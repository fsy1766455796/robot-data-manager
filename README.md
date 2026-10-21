# Mac・Linux の実行方法

```sh
git clone https://github.com/fsy1766455796/robot-data-manager.git
cd robot-data-manager
bash start.sh
```

自動検出されないフォルダーは、パスを指定して起動してください。

```sh
bash start.sh --root "/地図やrosbagのフォルダーのパス"
```

# Windows の実行方法

`E:/` は SSD のドライブ文字、または確認したいローカルフォルダーのパスに置き換えてください。

```powershell
git clone https://github.com/fsy1766455796/robot-data-manager.git
cd robot-data-manager
py bootstrap.py --root "E:/"
```

ブラウザーで http://127.0.0.1:8765 を開いてください。

## 自动发现与删除

直接运行 `bash start.sh`，自动发现的地图、rosbag 和挂载硬盘在文件系统允许写入时均支持删除，无需手动指定各自的路径。插入新硬盘后点击“再スキャン”。

删除前会列出具体文件供确认；完全删除无法恢复。只读挂载或没有写入权限时无法删除。`--root` 仍可用于明确以只读方式打开指定目录。
