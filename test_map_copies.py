import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import create_app

class MapCopyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.original=self.root/'maps'/'glim'/'20260919-135337'/'map.pgm'
        self.copy=self.root/'maps'/'glim'/'20260919-135337（コピー）'/'map.pgm'
        for p in [self.original,self.copy]:
            p.parent.mkdir(parents=True); p.write_bytes(b'P5\n1 1\n255\n\xff')
        self.client=create_app([{'id':'data','name':'Data','path':str(self.root),'writable':True}]).test_client()
        self.token={'X-Catalog-Token':self.catalog()['token']}
    def catalog(self): return self.client.get('/api/catalog').get_json()
    def refresh(self): self.client.post('/api/refresh',json={},headers=self.token)
    def test_copy_paths_share_group_but_keep_independent_links(self):
        items=self.catalog()['items']; self.assertEqual(len(items),2)
        self.assertEqual(len({x['display_group'] for x in items}),1)
        self.assertEqual({x['path'] for x in items},{str(self.original),str(self.copy)})
        with patch('app.open_in_file_manager') as opener:
            for x in items:
                self.assertEqual(self.client.post('/api/open-folder',json={'id':x['id']},headers=self.token).status_code,200)
                opener.assert_called_with(Path(x['path']))
    def test_deleting_copy_preserves_original_and_removes_group(self):
        x=next(x for x in self.catalog()['items'] if x['path']==str(self.copy))
        self.assertEqual(self.client.post('/api/delete',json={'id':x['id']},headers=self.token).status_code,200)
        self.assertTrue(self.original.exists()); self.assertFalse(self.copy.exists())
        remaining=self.catalog()['items']; self.assertEqual(len(remaining),1)
        self.assertNotIn('display_group',remaining[0])
    def test_same_name_different_content_stays_separate(self):
        self.copy.write_bytes(b'P5\n1 1\n255\n\x00'); self.refresh()
        self.assertTrue(all('display_group' not in x for x in self.catalog()['items']))
    def test_different_categories_stay_separate(self):
        target=self.root/'maps'/'slam_toolbo'/'20260919-135337（コピー）'/'map.pgm'
        target.parent.mkdir(parents=True); self.copy.rename(target); self.refresh()
        self.assertTrue(all('display_group' not in x for x in self.catalog()['items']))
    def test_filename_copies_and_numbered_suffix(self):
        for suffix in [' (copy)', '（コピー 2）']:
            (self.original.parent/('map'+suffix+'.pgm')).write_bytes(self.original.read_bytes())
        self.refresh(); self.assertEqual(len({x['display_group'] for x in self.catalog()['items']}),1)
