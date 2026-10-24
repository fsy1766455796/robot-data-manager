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

## PGM 削除後の残存フォルダーの一括整理

地図画面の「PGM のない地図を整理」を押すと、選択中のデータソース内の
`maps` / `map` 配下にある日時フォルダー（例：`20250919_192900`、コピー名も対応）を走査します。
サブフォルダーや隠しファイルも含めて PGM がなく、rosbag データやシンボリックリンクもないものだけを一覧表示します。
対象フォルダーと解放予定容量を確認し、「一覧のフォルダーを一括削除」で完全削除します。
点群など残っている全データも対象です。検索・分類フィルターによらず、選択中のデータソース全体が対象です。
データソースのルート、通常の分類フォルダー、日時形式以外のフォルダーは整理しません。
確認後に内容が変化した場合や15分以上経過した場合は、再走査が必要です。
