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


```sh
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
```

## 地図の削除範囲

地図の「削除」は、その PGM が入っているフォルダー全体を完全削除します。
同じフォルダー内の別の地図、YAML、点群、隠しファイル、サブフォルダーも対象です。
別の保存先にある原本・コピーは残ります。確認画面に対象フォルダーを表示します。
データソースのルート直下にある地図は、ルート全体の誤削除を防ぐため削除できません。
フォルダー内にシンボリックリンクがある場合も削除を拒否します。
rosbag の削除範囲は従来どおりです。
