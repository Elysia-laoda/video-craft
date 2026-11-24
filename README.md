# video-craft-kit · 做视频 / 读视频的交接包

入口是 `SKILL.md`（DSH 技能名 `video-craft`，已 junction 到 `~/.dsh/skills/video-craft`）。

## 目录

| 路径 | 内容 |
|---|---|
| SKILL.md | 技能入口：选路、七条铁律、七步流程、验收六数 |
| references/01-做视频.md | 音乐 → 剧本 → 节拍表 → 场景 → 渲染 |
| references/02-读视频.md | 抽帧 / OCR 歌词轴 / 测 BPM / 拉评论 / 查许可 |
| references/03-场景与工程.md | Remotion 骨架、组件表、安全带、编译坑 |
| references/04-外部模型.md | 中转站模型选择、Claude CLI、生图 |
| references/05-验收.md | 六个数字与报告模板 |
| references/06-实例索引.md | 五个工程里能抄的零件 |
| references/07-坑表.md | 42 条实测坑（含长片/manifest 一节） |
| references/08-音效与素材.md | 素材获取与许可 |
| references/09-曲目参数.md | 已复核曲目参数 |
| references/10-长片与多镜头.md | manifest、镜头分配、空镜排查、定镜与运镜 |
| references/11-声音设计与混音.md | 逐镜音效、合成配方、限幅 |
| references/12-交付与打包.md | 转码、源码包、脱敏、校验 |
| references/08-音效与素材.md | Pixabay / Commons 取音效、特征挑选、许可证分级 |
| references/09-曲目参数.md | 已复核曲目的 BPM/首拍（含默认 BGM 与测法证据） |
| templates/ | 剧本模板、节拍表模板、五份验收脚本 |

## 30 秒上手

```powershell
python templates/验收脚本/analyze_music.py 音乐.wav        # 拿 BPM/首拍
# 写剧本 → 写节拍表 → 搭 Remotion → 画场景
python templates/验收脚本/verify_film.py 成片.mp4          # 验收
```

## 维护

- 新踩的坑写进 `references/07-坑表.md`（一行一条，带症状与解法）。
- 新工程做完，把「可抄的零件」补进 `references/06-实例索引.md`。
- 模型/端点变了改 `references/04-外部模型.md` 一张表即可。
