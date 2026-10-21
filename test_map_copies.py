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
    def test_copy_name_groups_even_when_contents_differ(self):
        self.copy.write_bytes(b'P5\n1 1\n255\n\x00'); self.refresh()
        self.assertEqual(len({x['display_group'] for x in self.catalog()['items']}),1)
    def test_different_categories_stay_separate(self):
        target=self.root/'maps'/'slam_toolbo'/'20260919-135337（コピー）'/'map.pgm'
        target.parent.mkdir(parents=True); self.copy.rename(target); self.refresh()
        self.assertTrue(all('display_group' not in x for x in self.catalog()['items']))
    def test_filename_copies_and_numbered_suffix(self):
        for suffix in [' (copy)', '（コピー 2）']:
            (self.original.parent/('map'+suffix+'.pgm')).write_bytes(self.original.read_bytes())
        self.refresh(); self.assertEqual(len({x['display_group'] for x in self.catalog()['items']}),1)

    def test_same_directory_copy_filename_with_different_size(self):
        self.copy.unlink()
        copy=self.original.parent/'map（コピー）.pgm'
        copy.write_bytes(b'P5\n# Different export header\n1 1\n255\n\x00')
        self.refresh()
        items=self.catalog()['items']
        self.assertEqual(len(items),2)
        self.assertEqual(len({x['display_group'] for x in items}),1)
        self.assertEqual({x['bytes'] for x in items},{self.original.stat().st_size,copy.stat().st_size})
    def test_timestamp_directory_groups_versioned_pgm_names(self):
        folder=self.root/'maps'/'glim'/'20250919_192900'; folder.mkdir()
        for name in ['map.pgm','map.20260919201553pgm','map.20260919201554.pgm','other.pgm']:
            (folder/name).write_bytes(b'P5\n1 1\n255\n\x00')
        (folder/'map.png').write_bytes(b'ignore')
        self.refresh()
        versions=[x for x in self.catalog()['items'] if '20250919_192900' in x['path']]
        self.assertEqual(len(versions),4)
        self.assertEqual(len({x['display_group'] for x in versions}),1)
        for x in versions:
            self.assertEqual(x['bytes'],Path(x['path']).stat().st_size)
            self.assertEqual(len(x['images']),1)
            self.assertEqual(self.client.get('/api/image/'+x['images'][0]['id']).status_code,200)
        original_group=next(x['display_group'] for x in self.catalog()['items'] if '20260919-135337' in x['path'])
        self.assertNotEqual(versions[0]['display_group'],original_group)
        version=next(x for x in versions if x['path'].endswith('map.20260919201553pgm'))
        self.assertEqual(self.client.post('/api/delete',json={'id':version['id']},headers=self.token).status_code,200)
        self.assertTrue((folder/'map.pgm').exists())

    def test_discovery_finds_timestamp_extension(self):
        from discovery import has_data
        folder=self.root/'version-only';folder.mkdir()
        (folder/'map.20260919201553pgm').write_bytes(b'P5\n1 1\n255\n\xff')
        self.assertTrue(has_data(folder))

    def test_direct_timestamp_source_groups_versions(self):
        folder=self.root/'20250919_192900';folder.mkdir()
        for name in ['map.pgm','map.20260919201553pgm']:
            (folder/name).write_bytes(b'P5\n1 1\n255\n\xff')
        client=create_app([{'id':'time','name':'Time','path':str(folder),'writable':True}]).test_client()
        items=client.get('/api/catalog').get_json()['items']
        self.assertEqual(len({x['display_group'] for x in items}),1)
