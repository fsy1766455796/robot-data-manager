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

## 地图和 rosbag 管理

- 地图只识别 PGM，每个文件单独显示；大小仅为该 PGM 的字节数，不包含 YAML、PNG、点云或子目录。
- 路径分类使用 `maps`、`bags`、`rosbag` 等目录下的第一级子目录，例如 `maps/glim/a.pgm` 属于 `glim`。直接指定 maps/bags 为数据源也适用。根目录数据归入“未分類”。可用分类下拉框配合搜索和排序。
- 带 `metadata.yaml` 的 rosbag 按录制目录显示，大小只统计该目录中的 `.mcap`、`.db3`、`.bag` 文件；不计元数据、日志或嵌套的其他录制。没有元数据的录制文件单独显示。
- 每条记录都有删除按钮。地图删除该 PGM 及同目录引用它的 YAML；rosbag 删除该条记录的数据文件及元数据。不会递归删除目录，其他文件会保留。确认框列出具体文件，完全删除无法恢复。
- 自动发现和 `--root` 来源保持只读。要在 Linux 上启用删除，用实际本地数据路径启动：

```sh
bash start.sh --manage-root "$HOME/maps" --manage-root "$HOME/rosbag"
```

路径必须存在；只指定需要管理的目录。移动硬盘路径仍遵循原有只读限制。原有“一時保管・復元”功能继续保留。

测试：`python -m unittest -v`
