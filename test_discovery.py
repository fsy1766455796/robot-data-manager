import tempfile
import unittest
from pathlib import Path
from discovery import discover, has_data
from app import create_app, main
from unittest.mock import patch

class DiscoveryTests(unittest.TestCase):
    def test_arbitrary_drive_name_and_manageable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); disk=root/'Different SSD'; data=disk/'maps'/'sample'; data.mkdir(parents=True)
            (data/'map.pgm').write_bytes(b'P5\n1 1\n255\n\xff')
            sources=discover(home=root/'home',mounts=[disk])
            self.assertEqual(len(sources),1); self.assertTrue(sources[0]['writable'])
            self.assertEqual(sources[0]['name'],'Different SSD')
            self.assertEqual(discover(home=root/'home',mounts=[disk]),sources)
    def test_no_links_or_trash_or_deep_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); disk=root/'drive'; disk.mkdir(); outside=root/'outside'; outside.mkdir()
            (outside/'data.mcap').touch(); (disk/'link').symlink_to(outside,target_is_directory=True)
            trash=disk/'.Trash'; trash.mkdir(); (trash/'data.mcap').touch()
            self.assertFalse(has_data(disk))
            (disk/'a').mkdir(); (disk/'a'/'metadata.yaml').touch()
            self.assertTrue(has_data(disk)); self.assertFalse(has_data(disk,max_depth=0))
    def test_startup_without_data_does_not_generate_demo(self):
        built=[]
        def build(*args, **kwargs):
            application=create_app(*args, **kwargs)
            built.append(application)
            return application
        with patch('sys.argv',['app.py','--no-auto']), patch('app.create_app',side_effect=build), patch('app.Flask.run'), patch('app.make_demo') as demo:
            main()
        demo.assert_not_called()
        result=built[0].test_client().get('/api/catalog').get_json()
        self.assertEqual(result['sources'],[])
        self.assertEqual(result['items'],[])

    def test_refresh_discovers_attach_and_detach(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); state=[]
            app=create_app([],discover_sources=lambda:list(state)); c=app.test_client()
            token=c.get('/api/catalog').get_json()['token']
            state.append({'id':'disk','name':'disk','path':str(root),'writable':False})
            c.post('/api/refresh',json={},headers={'X-Catalog-Token':token})
            self.assertEqual(len(c.get('/api/catalog').get_json()['sources']),1)
            state.clear(); c.post('/api/refresh',json={},headers={'X-Catalog-Token':token})
            self.assertEqual(c.get('/api/catalog').get_json()['sources'],[])

if __name__=='__main__': unittest.main()

class DefaultManagementTests(unittest.TestCase):
    def test_default_startup_and_new_drive_allow_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); home=root/'home'; local=home/'maps'/'glim'; local.mkdir(parents=True)
            (local/'map.pgm').write_bytes(b'P5\n1 1\n255\n\xff')
            mounts=[]; built=[]
            real_discover=discover
            def build(*args, **kwargs):
                application=create_app(*args, **kwargs); built.append(application); return application
            with patch('sys.argv',['app.py']), patch('app.discover',side_effect=lambda:real_discover(home=home,mounts=mounts)), patch('app.create_app',side_effect=build), patch('app.Flask.run'):
                main()
            c=built[0].test_client(); data=c.get('/api/catalog').get_json()
            headers={'X-Catalog-Token':data['token']}
            self.assertTrue(data['items'][0]['can_delete'])
            drive=root/'USB'; bag=drive/'bags'/'slam_toolbo'/'sample'; bag.mkdir(parents=True)
            (bag/'sample.mcap').write_bytes(b'recording')
            mounts.append(drive)
            with patch('app.discover',side_effect=lambda:real_discover(home=home,mounts=mounts)):
                self.assertEqual(c.post('/api/refresh',json={},headers=headers).status_code,200)
            recording=next(x for x in c.get('/api/catalog').get_json()['items'] if x['kind']=='bag')
            self.assertTrue(recording['can_delete'])
            with patch('app.discover',side_effect=lambda:real_discover(home=home,mounts=mounts)):
                self.assertEqual(c.post('/api/delete',json={'id':recording['id']},headers=headers).status_code,200)
            self.assertFalse((bag/'sample.mcap').exists())

    def test_discovery_respects_filesystem_write_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); maps=root/'maps'; maps.mkdir(); (maps/'map.pgm').touch()
            with patch('discovery.os.access',return_value=False):
                sources=discover(home=root,mounts=[])
            self.assertFalse(sources[0]['writable'])
