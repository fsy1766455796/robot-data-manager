import tempfile
import unittest
from pathlib import Path
from app import create_app

class MapFolderDeleteTests(unittest.TestCase):
    def test_deletes_whole_folder_and_preserves_neighbor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root/'maps'/'glim'/'20260919-135337'
            folder.mkdir(parents=True)
            for name in ['map.pgm', 'copy.pgm']:
                (folder/name).write_bytes(b'P5\n1 1\n255\n\xff')
            (folder/'cloud').mkdir()
            (folder/'cloud'/'data.pcd').write_text('point cloud')
            (folder/'map.yaml').write_text('image: map.pgm\n')
            (folder/'.hidden').write_text('also removed')
            neighbor = folder.parent/'neighbor'; neighbor.mkdir()
            (neighbor/'keep.txt').write_text('keep')
            client = create_app([dict(id='data', name='Data', path=str(root), writable=True)]).test_client()
            catalog = client.get('/api/catalog').get_json()
            item = catalog['items'][0]
            result = client.post('/api/delete', json={'id': item['id']}, headers={'X-Catalog-Token': catalog['token']})
            self.assertEqual(result.status_code, 200)
            self.assertFalse(folder.exists())
            self.assertTrue((neighbor/'keep.txt').exists())
            self.assertEqual(client.get('/api/catalog').get_json()['items'], [])

    def test_rejects_link_anywhere_in_folder_before_deleting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root/'map-data'; folder.mkdir()
            image = folder/'map.pgm'; image.write_bytes(b'P5\n1 1\n255\n\xff')
            outside = root/'keep.txt'; outside.write_text('keep')
            client = create_app([dict(id='data', name='Data', path=str(root), writable=True)]).test_client()
            catalog = client.get('/api/catalog').get_json()
            (folder/'.link').symlink_to(outside)
            result = client.post('/api/delete', json={'id':catalog['items'][0]['id']}, headers={'X-Catalog-Token':catalog['token']})
            self.assertEqual(result.status_code, 403)
            self.assertTrue(image.exists())
            self.assertEqual(outside.read_text(), 'keep')
