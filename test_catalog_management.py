import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app import create_app

class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for category in ['glim', 'slam_toolbo']:
            folder = self.root/'maps'/category
            folder.mkdir(parents=True)
            for name in ['first', 'second']:
                Image.new('L', (10, 20)).save(folder/(name+'.pgm'))
                (folder/(name+'.yaml')).write_text('image: '+name+'.pgm\nresolution: 0.05\n')
            Image.new('L', (30, 40)).save(folder/'ignore.png')
            (folder/'unrelated.bin').write_bytes(b'x'*10000)
        png = self.root/'maps'/'png-only'; png.mkdir()
        Image.new('L', (10, 10)).save(png/'ignore.png')
        bag = self.root/'bags'/'glim'/'recording'; bag.mkdir(parents=True)
        (bag/'metadata.yaml').write_text('rosbag2_bagfile_information:\n  relative_file_paths: [part0.mcap, part1.mcap]\n')
        (bag/'part0.mcap').write_bytes(b'x'*31)
        (bag/'part1.mcap').write_bytes(b'x'*43)
        (bag/'ignore.log').write_bytes(b'x'*1000)
        nested = bag/'nested'; nested.mkdir(); (nested/'other.bag').write_bytes(b'x'*7)
        self.client = create_app([{'id':'data','name':'Data','path':str(self.root),'writable':True}]).test_client()
        self.headers = {'X-Catalog-Token': self.catalog()['token']}
    def catalog(self): return self.client.get('/api/catalog').get_json()
    def post(self, url, data): return self.client.post(url, json=data, headers=self.headers)
    def test_pgm_only_individual_size_and_categories(self):
        maps = [x for x in self.catalog()['items'] if x['kind']=='map']
        self.assertEqual(len(maps), 4)
        self.assertEqual({x['category'] for x in maps}, {'glim', 'slam_toolbo'})
        for x in maps:
            self.assertEqual(x['bytes'], Path(x['path']).stat().st_size)
            self.assertEqual(len(x['images']), 1)
            self.assertEqual(x['resolution'], .05)
    def test_map_delete_whole_containing_folder(self):
        x = next(x for x in self.catalog()['items'] if x['kind']=='map')
        path = Path(x['path']); before = {p for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.post('/api/delete', {'id': x['id']}).status_code, 200)
        after = {p for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before-after, {p for p in before if path.parent in p.parents})
        self.assertFalse(path.parent.exists())
        self.assertEqual(self.post('/api/delete', {'id': x['id']}).status_code, 404)
    def test_bag_size_delete_excludes_nested_and_unrelated(self):
        x = next(x for x in self.catalog()['items'] if x['name']=='recording')
        self.assertEqual(x['category'], 'glim')
        self.assertEqual(x['bytes'], 74)
        self.assertEqual(self.post('/api/delete', {'id': x['id']}).status_code, 200)
        self.assertTrue((Path(x['path'])/'ignore.log').exists())
        self.assertTrue((Path(x['path'])/'nested'/'other.bag').exists())
    def test_delete_rejects_symlink_and_missing_token(self):
        x = next(x for x in self.catalog()['items'] if x['kind']=='map')
        self.assertEqual(self.client.post('/api/delete', json={'id':x['id']}).status_code, 403)
        path=Path(x['path']); path.unlink(); path.symlink_to(path.parent/'second.pgm' if path.stem=='first' else path.parent/'first.pgm')
        self.assertEqual(self.post('/api/delete', {'id':x['id']}).status_code,403)
        self.assertTrue(path.with_suffix('.yaml').exists())
    def test_delete_readonly(self):
        client=create_app([{'id':'data','name':'Data','path':str(self.root),'writable':False}]).test_client()
        data=client.get('/api/catalog').get_json(); x=data['items'][0]
        self.assertFalse(x['can_delete'])
        self.assertEqual(client.post('/api/delete',json={'id':x['id']},headers={'X-Catalog-Token':data['token']}).status_code,403)
    def test_source_root_map_can_delete(self):
        Image.new('L',(1,1)).save(self.root/'root.pgm')
        self.post('/api/refresh',{})
        x=next(x for x in self.catalog()['items'] if x['relative_path']=='root.pgm')
        self.assertEqual(x['category'],'未分類')
        self.assertFalse(x['can_delete'])
        self.assertEqual(self.post('/api/delete',{'id':x['id']}).status_code,403)
        self.assertTrue((self.root/'root.pgm').exists())
        self.assertTrue(self.root.is_dir())
    def test_standalone_bags_remain_independent(self):
        folder=self.root/'bags'/'slam_toolbo'; folder.mkdir()
        (folder/'one.bag').write_bytes(b'one')
        (folder/'two.bag').write_bytes(b'two-two')
        self.post('/api/refresh',{})
        x=next(x for x in self.catalog()['items'] if x['name']=='one.bag')
        self.assertEqual(x['category'],'slam_toolbo')
        self.assertEqual(x['bytes'],3)
        self.assertEqual(self.post('/api/delete',{'id':x['id']}).status_code,200)
        self.assertEqual((folder/'two.bag').read_bytes(),b'two-two')

    def test_large_map_header_supported_but_finite_limit_retained(self):
        large=self.root/'maps'/'glim'/'large.pgm'
        # Header inspection must not allocate the full 163 MP image.
        large.write_bytes(b'P5\n12777 12777\n255\n')
        oversized=self.root/'maps'/'glim'/'oversized.pgm'
        oversized.write_bytes(b'P5\n15000 15000\n255\n')
        self.post('/api/refresh',{})
        items=self.catalog()['items']
        accepted=next(x for x in items if x['relative_path'].endswith('/large.pgm'))
        self.assertEqual(accepted['pixels'],163251729)
        self.assertEqual(accepted['warnings'],[])
        rejected=next(x for x in items if x['relative_path'].endswith('/oversized.pgm'))
        self.assertTrue(rejected['warnings'])

    def test_grayscale_preview_and_original(self):
        from io import BytesIO
        x=next(x for x in self.catalog()['items'] if x['kind']=='map')
        for query in ['', '?full=1', '?original=1']:
            response=self.client.get('/api/image/'+x['images'][0]['id']+query)
            self.assertEqual(response.status_code,200)
            with Image.open(BytesIO(response.data)) as image:
                self.assertEqual(image.mode,'L')
                self.assertEqual(image.size,(10,20))
