import tempfile
import unittest
from pathlib import Path
from app import create_app

class MapCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.maps = self.root/'maps'/'glim'; self.maps.mkdir(parents=True)
        self.orphan = self.maps/'20250919_192900'; self.orphan.mkdir()
        (self.orphan/'cloud.pcd').write_bytes(b'x'*23)
        (self.orphan/'nested').mkdir(); (self.orphan/'nested'/'.cache').write_bytes(b'xx')
        self.good = self.maps/'20250920_192900'; self.good.mkdir()
        (self.good/'map.20260919201553pgm').write_bytes(b'P5\n1 1\n255\n\xff')
        self.client = create_app([dict(id='data',name='Data',path=str(self.root),writable=True)]).test_client()
        self.headers = {'X-Catalog-Token':self.client.get('/api/catalog').get_json()['token']}
    def preview(self):
        return self.client.post('/api/cleanup/preview',json={'source':'data'},headers=self.headers)
    def execute(self, plan):
        return self.client.post('/api/cleanup',json={'plan':plan},headers=self.headers)
    def test_preview_then_remove_whole_orphan_only(self):
        response = self.preview(); self.assertEqual(response.status_code,200)
        data = response.get_json(); self.assertEqual(len(data['items']),1)
        self.assertEqual(data['items'][0]['bytes'],25)
        self.assertTrue(self.orphan.exists())
        result = self.execute(data['plan']); self.assertEqual(result.status_code,200)
        self.assertEqual(result.get_json()['removed'],1)
        self.assertFalse(self.orphan.exists()); self.assertTrue(self.good.exists()); self.assertTrue(self.maps.exists())
        self.assertEqual(self.execute(data['plan']).status_code,409)
    def test_new_pgm_after_preview_blocks_cleanup(self):
        plan=self.preview().get_json()['plan']
        (self.orphan/'new.PGM').write_bytes(b'pgm')
        self.assertEqual(self.execute(plan).status_code,409)
        self.assertTrue((self.orphan/'cloud.pcd').exists())
    def test_changed_residue_after_preview_blocks_cleanup(self):
        plan=self.preview().get_json()['plan']
        (self.orphan/'cloud.pcd').write_bytes(b'changed')
        self.assertEqual(self.execute(plan).status_code,409)
        self.assertTrue(self.orphan.exists())
    def test_protects_bags_links_hidden_pgm_and_unrelated_folders(self):
        for index, name in enumerate(['metadata.yaml','record.mcap','.map.pgm','record.db3','record.bag']):
            folder=self.maps/f'2025092{index+1}_192900'; folder.mkdir(); (folder/name).write_text('keep')
        linked=self.maps/'20250927_192900'; linked.mkdir(); (linked/'link').symlink_to(self.good)
        unrelated=self.root/'other'/'20250928_192900'; unrelated.mkdir(parents=True)
        (self.maps/'ordinary-folder').mkdir()
        data=self.preview().get_json()
        self.assertEqual([x['path'] for x in data['items']], [str(self.orphan.relative_to(self.root))])
    def test_root_and_readonly_and_token_protection(self):
        self.assertEqual(self.client.post('/api/cleanup/preview',json={'source':'data'}).status_code,403)
        client=create_app([dict(id='ro',name='Read only',path=str(self.orphan),writable=False)]).test_client()
        token=client.get('/api/catalog').get_json()['token']
        self.assertEqual(client.post('/api/cleanup/preview',json={'source':'ro'},headers={'X-Catalog-Token':token}).status_code,403)
    def test_revalidates_all_before_removing_any(self):
        second=self.maps/'20250918_192900'; second.mkdir()
        plan=self.preview().get_json()['plan']
        (self.orphan/'link').symlink_to(self.good)
        self.assertEqual(self.execute(plan).status_code,409)
        self.assertTrue(second.exists()); self.assertTrue(self.orphan.exists())
    def test_remaining_packages_are_discovered_without_any_pgm(self):
        from discovery import has_data, discover
        (self.good/'map.20260919201553pgm').unlink()
        self.assertTrue(has_data(self.root/'maps'))
        found=discover(home=self.root, mounts=[])
        self.assertEqual([x['path'] for x in found],[str((self.root/'maps').resolve())])
    def test_pgm_inside_subfolder_protects_entire_package(self):
        (self.orphan/'nested'/'keep.pgm').write_text('pgm')
        self.assertEqual(self.preview().get_json()['items'],[])
    def test_direct_maps_source_keeps_source_and_category_directories(self):
        client=create_app([dict(id='maps',name='Maps',path=str(self.root/'maps'),writable=True)]).test_client()
        token=client.get('/api/catalog').get_json()['token']; headers={'X-Catalog-Token':token}
        plan=client.post('/api/cleanup/preview',json={'source':'maps'},headers=headers).get_json()
        self.assertEqual(len(plan['items']),1)
        self.assertEqual(client.post('/api/cleanup',json={'plan':plan['plan']},headers=headers).status_code,200)
        self.assertTrue(self.maps.is_dir())
    def test_preview_expiry_and_directory_replacement(self):
        from unittest.mock import patch
        plan=self.preview().get_json()['plan']
        with patch('app.time.monotonic',return_value=10**15):
            self.assertEqual(self.execute(plan).status_code,409)
        self.assertTrue(self.orphan.exists())
