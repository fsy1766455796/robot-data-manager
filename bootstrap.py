"""Install isolated dependencies on first launch, then start the catalog."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

base=Path(__file__).resolve().parent
if sys.version_info < (3,9):
    raise SystemExit('Python 3.9 以降をインストールしてください。')
cache=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))
if sys.platform=='darwin': cache=Path.home()/'Library'/'Caches'
requirements=base/'requirements.txt'
fingerprint=hashlib.sha256(requirements.read_bytes()).hexdigest()
env=cache/'robot-data-manager'/('python-'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))
python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.exists():
    print('初回起動：実行環境を準備しています…',flush=True)
    try: venv.EnvBuilder(with_pip=True).create(env)
    except Exception as e:
        raise SystemExit('仮想環境を作成できません。Ubuntu では python3-venv を確認してください。\n'+str(e))
stamp=env/'.requirements-hash'
ready=subprocess.run([str(python),'-c','import flask, PIL, yaml'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
if not ready or not stamp.exists() or stamp.read_text()!=fingerprint:
    print('ライブラリをインストールしています（初回はインターネット接続が必要です）…',flush=True)
    result=subprocess.run([str(python),'-m','pip','install','--timeout','15','--retries','1','-r',str(requirements)])
    if result.returncode: raise SystemExit('取得できませんでした。ネットワークを確認して再起動してください。')
    stamp.write_text(fingerprint)
os.execv(str(python),[str(python),str(base/'app.py'),'--open-browser',*sys.argv[1:]])
