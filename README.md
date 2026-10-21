# Mac・Linux の実行方法

```sh
git clone https://github.com/fsy1766455796/robot-data-manager.git
cd robot-data-manager
bash start.sh \
  --manage-root "$HOME/ros2_ws/maps" \
  --manage-root "$HOME/ros2_ws/rosbag"
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
