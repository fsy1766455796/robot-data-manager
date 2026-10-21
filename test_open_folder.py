import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import create_app, open_in_file_manager


class OpenFolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.map = self.root/'map with space.pgm'
        self.map.write_bytes(b'P5\n1 1\n255\n\xff')
        self.bag = self.root/'bags'/'recording'
        self.bag.mkdir(parents=True)
        (self.bag/'metadata.yaml').write_text('rosbag2_bagfile_information: {}')
        self.client = create_app([{'id':'ro','name':'Data','path':str(self.root),'writable':False}]).test_client()
        self.catalog = self.client.get('/api/catalog').get_json()
        self.headers = {'X-Catalog-Token':self.catalog['token']}

    def test_reveal_map_and_bag_even_when_readonly(self):
        with patch('app.open_in_file_manager') as opener:
            for item in self.catalog['items']:
                response=self.client.post('/api/open-folder',json={'id':item['id']},headers=self.headers)
                self.assertEqual(response.status_code,200)
                opener.assert_called_with(Path(item['path']))

    def test_token_unknown_and_missing_file(self):
        item=next(x for x in self.catalog['items'] if x['kind']=='map')
        with patch('app.open_in_file_manager') as opener:
            self.assertEqual(self.client.post('/api/open-folder',json={'id':item['id']}).status_code,403)
            self.assertEqual(self.client.post('/api/open-folder',json={'id':'unknown'},headers=self.headers).status_code,404)
            self.map.unlink()
            self.assertEqual(self.client.post('/api/open-folder',json={'id':item['id']},headers=self.headers).status_code,404)
            opener.assert_not_called()

    def test_symlink_substitution_denied(self):
        item=next(x for x in self.catalog['items'] if x['kind']=='map')
        self.map.unlink(); self.map.symlink_to(self.bag/'metadata.yaml')
        with patch('app.open_in_file_manager') as opener:
            self.assertEqual(self.client.post('/api/open-folder',json={'id':item['id']},headers=self.headers).status_code,403)
            opener.assert_not_called()

    def test_linux_reveals_file_with_encoded_uri(self):
        with patch('app.sys.platform','linux'), patch('app.subprocess.run') as run:
            open_in_file_manager(self.map)
            command=run.call_args.args[0]
            self.assertIn('org.freedesktop.FileManager1.ShowItems',command)
            self.assertIn('array:string:'+self.map.as_uri(),command)
            self.assertNotIn('shell',run.call_args.kwargs)

    def test_linux_falls_back_to_parent_folder(self):
        with patch('app.sys.platform','linux'), patch('app.subprocess.run',side_effect=[subprocess.CalledProcessError(1,'dbus-send'),None]) as run:
            open_in_file_manager(self.map)
            self.assertEqual(run.call_args.args[0],['xdg-open',str(self.root)])

    def test_linux_directory_opens_directory(self):
        with patch('app.sys.platform','linux'), patch('app.subprocess.run') as run:
            open_in_file_manager(self.bag)
            self.assertEqual(run.call_args.args[0],['xdg-open',str(self.bag)])

    def test_missing_desktop_returns_error(self):
        with patch('app.sys.platform','linux'), patch('app.subprocess.run',side_effect=FileNotFoundError):
            with self.assertRaises(RuntimeError):
                open_in_file_manager(self.bag)
