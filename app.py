"""Local ROS map/rosbag catalog. No ROS installation required."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from io import BytesIO
import argparse, hashlib, json, os, re, secrets, shutil, threading, uuid, warnings, sys, webbrowser
from discovery import discover
import yaml
from PIL import Image, ImageDraw
from flask import Flask, jsonify, request, send_file, abort

BASE = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
IMAGE_EXT = {'.png', '.pgm', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}
BAG_EXT = {'.mcap', '.db3', '.bag'}
SKIP = {'System Volume Information', '$RECYCLE.BIN'}

def excluded(name):
    return name.startswith(('.', '$', 'FOUND.')) or name in SKIP

def within(path, root):
    try:
        path.resolve().relative_to(root.resolve()); return True
    except ValueError:
        return False

def load_yaml(path):
    if path.stat().st_size > 8_000_000:
        raise ValueError('YAML exceeds 8 MB')
    with path.open(encoding='utf-8') as f:
        value = yaml.safe_load(f)
    if not isinstance(value, dict):
        raise ValueError('Expected YAML mapping')
    return value

def path_date(path):
    matches = re.findall(r'(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)', str(path))
    for parts in reversed(matches):
        try:
            return datetime(*map(int, parts)).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None

def files_under(root):
    for d, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [n for n in dirs if not excluded(n) and not (Path(d)/n).is_symlink()]
        for n in files:
            p = Path(d)/n
            if not excluded(n) and not p.is_symlink():
                yield p

def make_demo(root):
    """Only create synthetic data in the application's local demo directory."""
    if root.exists():
        return
    for name, size, res in [('campus_test_20260909', (160, 120), .05), ('route_demo_20261003', (1200, 900), .05)]:
        p = root/'maps'/name; p.mkdir(parents=True)
        im = Image.new('L', size, 205); draw = ImageDraw.Draw(im)
        w,h = size
        draw.rectangle((w*.12,h*.12,w*.88,h*.88), fill=250, outline=0, width=max(2,w//100))
        for x in (.32,.60):
            draw.rectangle((w*x,h*.25,w*(x+.12),h*.65), fill=0)
        im.save(p/'map.pgm')
        (p/'map.yaml').write_text(yaml.safe_dump({'image':'map.pgm','resolution':res,'origin':[0,0,0],'negate':0,'occupied_thresh':.65,'free_thresh':.196}))
    p = root/'bags'/'demo_20260919'; p.mkdir(parents=True)
    # Metadata-only sample: deliberately no fake MCAP binary.
    (p/'metadata.yaml').write_text(yaml.safe_dump({'rosbag2_bagfile_information':{
        'version':9, 'storage_identifier':'mcap','duration':{'nanoseconds':120_000_000_000},
        'starting_time':{'nanoseconds_since_epoch':1789783200_000_000_000},'message_count':3600,
        'relative_file_paths':['demo_0.mcap'], 'topics_with_message_count':[
            {'topic_metadata':{'name':'/scan','type':'sensor_msgs/msg/LaserScan'},'message_count':1200},
            {'topic_metadata':{'name':'/odom','type':'nav_msgs/msg/Odometry'},'message_count':2400}]}}))

def create_app(sources, discover_sources=None):
    app = Flask(__name__, static_folder='static')
    app.config['MAX_CONTENT_LENGTH'] = 32768
    token = secrets.token_urlsafe(32)
    lock = threading.RLock()
    items, paths, image_paths = {}, {}, {}
    source_map = {s['id']:s for s in sources}

    def scan():
        with lock:
            if discover_sources is not None:
                sources[:] = discover_sources()
                source_map.clear()
                source_map.update({s['id']:s for s in sources})
            items.clear(); paths.clear(); image_paths.clear()
            for source in sources:
                root = Path(source['path']); source['available'] = root.is_dir(); source['warnings'] = []
                if not source['available']: continue
                groups = []
                all_paths = []
                def onerror(e): source['warnings'].append(str(e))
                for d, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
                    p = Path(d)
                    for n in dirs + files:
                        if (p/n).is_symlink():
                            source['warnings'].append('Skipped symbolic link: '+str((p/n).relative_to(root)))
                    dirs[:] = [n for n in dirs if not excluded(n) and not (p/n).is_symlink()]
                    fs = [p/n for n in files if not excluded(n) and not (p/n).is_symlink()]
                    all_paths.extend(fs)
                    images = sorted([f for f in fs if f.suffix.lower() in IMAGE_EXT], key=lambda f:(f.name!='map.pgm',f.suffix!='.pgm',f.name))
                    bagfiles = [f for f in fs if f.suffix.lower() in BAG_EXT]
                    if (p/'metadata.yaml') in fs or bagfiles:
                        groups.append((p,'bag',fs,[]))
                    elif images or any(f.suffix in {'.pcd','.ply','.simplemap','.mm','.las'} for f in fs):
                        groups.append((p,'map',fs,images))
                for p,kind,fs,imgs in groups:
                    rel = str(p.relative_to(root))
                    ident = hashlib.sha256((source['id']+':'+rel).encode()).hexdigest()[:24]
                    entry = dict(id=ident,source=source['id'],name=p.name,path=str(p),relative_path=rel,
                                 kind=kind,date=path_date(rel),date_basis='folder',bytes=0,topics=[],images=[],warnings=[],
                                 pixels=None,width=None,height=None,resolution=None,duration=None,messages=None,format='',
                                 readonly=not source['writable'],can_trash=False)
                    try:
                        group_files = [f for f in all_paths if f==p or p in f.parents]
                        entry['bytes'] = sum(f.stat().st_size for f in group_files)
                        entry['file_count'] = len(group_files)
                        entry['files'] = [{'name':str(f.relative_to(p)),'bytes':f.stat().st_size} for f in group_files]
                        if kind == 'bag':
                            meta = p/'metadata.yaml'
                            if meta.is_file() and not meta.is_symlink():
                                data = load_yaml(meta)['rosbag2_bagfile_information']
                                entry['duration'] = int(data.get('duration',{}).get('nanoseconds',0))/1e9
                                entry['messages'] = data.get('message_count')
                                entry['format'] = data.get('storage_identifier','')
                                ns = data.get('starting_time',{}).get('nanoseconds_since_epoch')
                                if ns is not None:
                                    dt = datetime.fromtimestamp(int(ns)/1e9,JST)
                                    entry['recorded_at'] = dt.isoformat()
                                    if dt.year >= 2000:
                                        entry['date'] = dt.strftime('%Y-%m-%d'); entry['date_basis'] = 'metadata (JST)'
                                    else: entry['warnings'].append('Recording clock is invalid; date uses folder name.')
                                for t in data.get('topics_with_message_count',[]):
                                    m = t.get('topic_metadata',{})
                                    entry['topics'].append({'name':m.get('name','?'),'type':m.get('type','?'),'count':t.get('message_count',0)})
                                for name in data.get('relative_file_paths',[]):
                                    f=p/name
                                    if not within(f,p) or f.is_symlink() or not f.is_file():
                                        entry['warnings'].append('Missing or external data file: '+name)
                            else: entry['warnings'].append('No metadata.yaml; topic details unavailable. Binary data has not been parsed.')
                            if not any(f.suffix.lower() in BAG_EXT for f in group_files):
                                entry['warnings'].append('Metadata only; no recording data file found.')
                        else:
                            entry['format'] = '3D / screenshots' if any(f.suffix in {'.simplemap','.mm','.las','.pcd','.ply'} for f in fs) else '2D map'
                            for f in fs:
                                if f.suffix in {'.yaml','.yml'}:
                                    try:
                                        meta=load_yaml(f)
                                        if 'image' in meta:
                                            primary=(p/str(meta['image'])).resolve()
                                            if primary in [x.resolve() for x in imgs]:
                                                imgs.sort(key=lambda x:x.resolve()!=primary)
                                                entry['resolution']=meta.get('resolution')
                                                entry['format']='2D map + 3D data' if entry['format'].startswith('3D') else '2D map'
                                                break
                                    except Exception as e: entry['warnings'].append(f.name+': '+str(e))
                            for i,img in enumerate(imgs):
                                image_id=ident+'-'+str(i); image_paths[image_id]=(img,root)
                                try:
                                    with warnings.catch_warnings():
                                        warnings.simplefilter('error',Image.DecompressionBombWarning)
                                        with Image.open(img) as im: w,h=im.size
                                    entry['images'].append({'id':image_id,'name':img.name,'width':w,'height':h})
                                    if i==0: entry.update(width=w,height=h,pixels=w*h)
                                except Exception as e: entry['warnings'].append(img.name+': '+str(e))
                        # Root folders and folders nesting another dataset cannot be moved as one item.
                        entry['can_trash'] = bool(source['writable'] and p!=root and not any(q!=p and p in q.parents for q,_,_,_ in groups))
                    except Exception as e:
                        entry['warnings'].append(str(e))
                    items[ident]=entry; paths[ident]=(p,source)
            return list(items.values())

    def safe_mutation(source,path):
        root=Path(source['path'])
        if not source['writable'] or within(root,Path('/Volumes')) or within(path,Path('/Volumes')):
            abort(403,description='This source is read-only.')
        if path==root or not within(path,root) or path.is_symlink(): abort(403)
        for part in [path,*path.parents]:
            if part==root: break
            if part.is_symlink(): abort(403)
        if not root.is_dir(): abort(409,description='Source is unavailable.')

    @app.before_request
    def guard():
        if request.host.split(':')[0] not in {'127.0.0.1','localhost'}: abort(403)
        if request.method!='GET' and request.headers.get('X-Catalog-Token')!=token: abort(403)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
        return response

    @app.errorhandler(Exception)
    def error(e):
        return jsonify(error=getattr(e,'description',str(e))),getattr(e,'code',500) or 500

    @app.get('/')
    def index(): return app.send_static_file('index.html')

    @app.get('/api/catalog')
    def catalog():
        with lock:
            for source in sources:
                source['disk'] = None
                try:
                    root = Path(source['path'])
                    if root.is_dir():
                        usage = shutil.disk_usage(root)
                        source['disk'] = {'total': usage.total, 'used': usage.used, 'free': usage.free}
                except OSError:
                    pass
            return jsonify(items=list(items.values()),sources=sources,token=token)

    @app.post('/api/refresh')
    def refresh(): scan(); return jsonify(ok=True)

    @app.get('/viewer/<ident>')
    def viewer(ident):
        if ident not in image_paths: abort(404)
        return app.send_static_file('viewer.html')

    @app.get('/api/image/<ident>')
    def preview(ident):
        with lock: pair=image_paths.get(ident)
        if pair is None: abort(404)
        p,root=pair
        if not within(p,root) or p.is_symlink(): abort(403)
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(p) as im:
                im=im.convert('RGB')
                if request.args.get('original') != '1':
                    im.thumbnail((2200,2200) if request.args.get('full') else (600,450))
                out=BytesIO(); im.save(out,format='PNG'); out.seek(0)
        return send_file(out,mimetype='image/png')

    @app.post('/api/trash')
    def trash():
        with lock:
            ident=(request.get_json() or {}).get('id')
            if ident not in paths: abort(404)
            p,source=paths[ident]; safe_mutation(source,p)
            if not items[ident]['can_trash']: abort(403,description='Non-movable dataset.')
            # Refuse trees containing links, including links to external drives.
            for d,ds,fs in os.walk(p,followlinks=False):
                if any((Path(d)/n).is_symlink() for n in ds+fs): abort(403,description='Dataset contains symbolic links.')
            trashroot=Path(source['path'])/'.catalog-trash'
            if trashroot.is_symlink(): abort(403)
            tid=uuid.uuid4().hex; dest=trashroot/tid
            dest.mkdir(parents=True)
            meta={'id':tid,'source':source['id'],'original':str(p.relative_to(source['path'])),'time':datetime.now(JST).isoformat()}
            (dest/'record.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
            try: p.rename(dest/'data')
            except Exception:
                (dest/'record.json').unlink(); dest.rmdir(); raise
            scan(); return jsonify(ok=True)

    @app.get('/api/trash')
    def trash_list():
        result=[]
        for s in sources:
            if not s['writable']: continue
            tr=Path(s['path'])/'.catalog-trash'
            if tr.is_symlink(): continue
            for p in tr.glob('*/record.json'):
                if p.is_symlink() or p.parent.is_symlink(): continue
                try:
                    if (p.parent/'data').exists(): result.append(json.loads(p.read_text()))
                except Exception: pass
        return jsonify(items=result)

    @app.post('/api/restore')
    def restore():
        with lock:
            data=request.get_json() or {}; tid=data.get('id',''); source=source_map.get(data.get('source'))
            if source is None or not re.fullmatch('[0-9a-f]{32}',tid): abort(400)
            record=Path(source['path'])/'.catalog-trash'/tid
            safe_mutation(source,record)
            if not (record/'data').is_dir() or (record/'record.json').is_symlink(): abort(404)
            meta=json.loads((record/'record.json').read_text()); target=Path(source['path'])/meta['original']
            safe_mutation(source,target)
            if target.exists(): abort(409,description='Original path already exists; nothing was overwritten.')
            target.parent.mkdir(parents=True,exist_ok=True)
            (record/'data').rename(target)
            (record/'record.json').unlink(); record.rmdir(); scan(); return jsonify(ok=True)

    scan()
    return app

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',action='append',default=[],help='Additional read-only data directory')
    parser.add_argument('--manage-root',action='append',default=[],help='Explicit opt-in to reversible quarantine on a LOCAL directory; /Volumes is always denied')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-auto',action='store_true',help='Disable automatic discovery')
    parser.add_argument('--open-browser',action='store_true')
    args=parser.parse_args()
    explicit=[]
    for writable, roots in [(False,args.root),(True,args.manage_root)]:
        for root in roots:
            p=Path(root).expanduser().resolve()
            if not p.is_dir(): parser.error('Directory does not exist: '+str(p))
            if writable and (any(within(p,Path(b)) for b in ['/Volumes','/media','/run/media','/mnt']) or p in [Path('/'),Path.home()]):
                parser.error('Use a dedicated local folder for management. Removable drives stay read-only.')
            if any(within(p,Path(s['path'])) or within(Path(s['path']),p) for s in explicit):
                parser.error('Sources must not overlap.')
            explicit.append({'id':'source'+str(len(explicit)),'name':p.name,'path':str(p),'writable':writable})
    def get_sources():
        auto=[] if args.no_auto else discover()
        auto=[s for s in auto if not any(within(Path(s['path']),Path(e['path'])) or within(Path(e['path']),Path(s['path'])) for e in explicit)]
        return explicit+auto
    app=create_app([], discover_sources=get_sources)
    url=f'http://127.0.0.1:{args.port}'
    print(f'Open {url} — discovered drives are read-only',flush=True)
    if args.open_browser:
        threading.Timer(1.5, lambda:webbrowser.open(url)).start()
    app.run(host='127.0.0.1',port=args.port,debug=False,threaded=True)

if __name__=='__main__': main()
