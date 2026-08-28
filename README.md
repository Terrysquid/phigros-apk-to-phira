# Phigros APK to Phira

Extract files from Phigros APK/XAPK and create zips for Phira.

## 使用说明

依赖库：`UnityPy` & `yaml` (`pip install UnityPy PyYAML`)

运行 `main.py`

   1. **加载文件**
      - 选择文件/从TapTap下载文件（输入路径：`input/`）
      - 加载/检查并加载
      - 检查并加载会记录曲目ID、定数、谱面文件，并比对上一次记录，便于发现新曲/定数/谱面变化

   2. **搜索曲目（可以留空）**
      - 搜索曲目名称/ID
      - 筛选难度
         - `Other`包含`Legacy`等特殊难度
      - 筛选定数范围
      - 高级筛选（需要检查并加载）
         - 新曲
         - 新谱/改谱
   
   3. **选择曲目**
      - 在候选曲目列表中，
         - 单击选择
         - 双击获取曲目ID
         - 多选：`Ctrl`/`Shift`+单击或拖动
         - 全选：`Ctrl+A`或点击全选

   4. **导出谱面**
      - 输出路径：`output/xxx.zip`
      - 可以直接导入 Phira

## 导出内容

每个zip包含：
- 曲目 ID
- `chart.json`：谱面文件
- `music.wav`：音频文件
- `illustration.jpg`：曲绘文件
- `illustrationBlur.jpg`：曲绘文件（模糊）
- `illustrationLowRes.jpg`：曲绘文件（低画质）
- `info.yml`
   - 曲目名称
   - 谱面难度
   - 谱面定数
   - 谱师
   - 曲师
   - 画师
   - 预览时间

## 适用版本

- 版本号 113 (3.9.1) 及以上：导出全部内容
- 版本号 77 (2.5.1) 至 112：导出全部内容（使用旧版 typetree）
- 版本号 41 (1.6.4) 至 76：导出部分内容（曲目 ID、谱面文件、音频文件、曲绘文件）
- 版本号 41 以下：暂不支持

## 其它

- APK的路径会自动保存到`config.json`中
- `data/song_ids.json`、`data/difficulties.json`、`data/asset_hashes.json`会在检查并加载时自动生成，用于检测新曲/定数/谱面变化