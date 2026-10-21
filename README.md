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



PROJECT_DIR="$(pwd)"
DESKTOP_DIR="$(xdg-user-dir DESKTOP)"

cat > "$DESKTOP_DIR/Robot Data Manager.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Robot Data Manager
Comment=ROS Map & Rosbag Manager
Exec=/bin/bash start.sh
Path=$PROJECT_DIR
Icon=utilities-terminal
Terminal=true
Categories=Development;
EOF

chmod +x "$DESKTOP_DIR/Robot Data Manager.desktop"
