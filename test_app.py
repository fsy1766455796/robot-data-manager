import hashlib
import tempfile
import unittest
from pathlib import Path
import yaml
from PIL import Image
from app import create_app, make_demo

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.ro=self.root/'readonly'; make_demo(self.ro)
        self.rw=self.root/'managed'; make_demo(self.rw)
        self.app=create_app([
            {'id':'ro','name':'Read only','path':str(self.ro),'writable':False},
            {'id':'rw','name':'Managed','path':str(self.rw),'writable':True}])
        self.client=self.app.test_client()
        self.catalog=self.client.get('/api/catalog').get_json()
        self.headers={'X-Catalog-Token':self.catalog['token']}
    def tearDown(self): self.tmp.cleanup()
    def item(self,src,name):
        return next(x for x in self.client.get('/api/catalog').get_json()['items'] if x['source']==src and name in x['name'])
    def post(self,url,data): return self.client.post(url,json=data,headers=self.headers)
    def digest(self,root):
        return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    def test_readonly_and_csrf(self):
        before=self.digest(self.ro)
        x=self.item('ro','campus')
        self.assertEqual(self.post('/api/trash',{'id':x['id']}).status_code,403)
        self.assertEqual(self.client.post('/api/refresh',json={}).status_code,403)
        self.assertEqual(self.digest(self.ro),before)
        self.assertEqual(self.client.get('/api/catalog',headers={'Host':'attacker.invalid'}).status_code,403)
    def test_catalog_and_preview(self):
        x=self.item('ro','campus'); self.assertEqual(x['pixels'],19200)
        self.assertEqual(x['resolution'],.05)
        r=self.client.get('/api/image/'+x['images'][0]['id']); self.assertEqual(r.status_code,200)
        self.assertTrue(r.data.startswith(b'\x89PNG'))
        b=self.item('ro','demo_20260919'); self.assertEqual(len(b['topics']),2)
        self.assertEqual(b['duration'],120); self.assertTrue(b['warnings'])
    def test_roundtrip_preserves_all_bytes(self):
        before=self.digest(self.rw); x=self.item('rw','campus')
        self.assertEqual(self.post('/api/trash',{'id':x['id']}).status_code,200)
        self.assertFalse(Path(x['path']).exists())
        records=self.client.get('/api/trash').get_json()['items']; self.assertEqual(len(records),1)
        self.assertEqual(self.post('/api/restore',records[0]).status_code,200)
        self.assertEqual(before,self.digest(self.rw))
    def test_symlink_escape(self):
        x=self.item('rw','campus'); (Path(x['path']).parent/'outside').symlink_to(self.ro,target_is_directory=True)
        self.assertEqual(self.post('/api/trash',{'id':x['id']}).status_code,403)
        (self.rw/'linked').symlink_to(self.ro,target_is_directory=True)
        self.post('/api/refresh',{})
        c=self.client.get('/api/catalog').get_json()
        self.assertTrue(next(s for s in c['sources'] if s['id']=='rw')['warnings'])
    def test_restore_conflict_no_overwrite(self):
        x=self.item('rw','campus'); self.post('/api/trash',{'id':x['id']})
        Path(x['path']).parent.mkdir(); (Path(x['path']).parent/'keep.txt').write_text('keep')
        rec=self.client.get('/api/trash').get_json()['items'][0]
        self.assertEqual(self.post('/api/restore',rec).status_code,409)
        self.assertEqual((Path(x['path']).parent/'keep.txt').read_text(),'keep')
    def test_missing_source_and_malformed_yaml(self):
        p=self.rw/'bags'/'bad'; p.mkdir(); (p/'metadata.yaml').write_text('bad: [')
        self.post('/api/refresh',{}); self.assertTrue(self.item('rw','bad')['warnings'])
        missing=create_app([{'id':'missing','name':'missing','path':str(self.root/'missing'),'writable':False}])
        self.assertFalse(missing.test_client().get('/api/catalog').get_json()['sources'][0]['available'])
    def test_ssd_path_cannot_be_enabled(self):
        app=create_app([{'id':'ssd','name':'SSD','path':'/Volumes/catalog-test-volume-not-mounted','writable':True}])
        # Test the mutation policy independently of whether a drive is attached.
        with app.test_request_context('/'):
            safe=next(c.cell_contents for c in app.view_functions['trash'].__closure__ if callable(c.cell_contents) and getattr(c.cell_contents,'__name__','')=='safe_mutation')
            with self.assertRaises(Exception) as cm:
                safe({'path':'/Volumes/catalog-test-volume-not-mounted','writable':True},Path('/Volumes/catalog-test-volume-not-mounted/anything'))
            self.assertEqual(cm.exception.code,403)

if __name__=='__main__': unittest.main(verbosity=2)
