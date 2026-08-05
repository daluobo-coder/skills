# 数据格式与路径

## 数据路径

| 类型 | 路径 |
|------|------|
| 数据根目录 | `$HOME/workspace/data/ai_drama/` |
| 系列输出目录 | `$HOME/workspace/data/ai_drama/{yyyy}/{mm}/历史人物_{人物名}_序列篇/` |
| 每集输出目录 | 系列目录下 `E{NN}_{集标题}/` |
| 素材原文 | 系列目录下 `素材/史料/{人物名}.txt` |
| 系列信息 | 系列目录下 `series_info.json` |
| 创作数据库 | `$HOME/workspace/data/ai_drama/stories.db`(复用,source字段区分) |
| 进度文件 | 每集目录下 `progress.json` |
| BGM | `$HOME/workspace/data/ai_drama/bgm/gaoshan_liushui_guzheng.mp3` |

## 目录结构示例

```
历史人物_上官婉儿_序列篇/
├── E01_刀下留人/
│   ├── script.json          ← 文案脚本
│   ├── script_source.md     ← 史料出处标注
│   ├── script_fact_check.md ← 史实排错报告
│   ├── audio/               ← TTS音频
│   ├── images/              ← AI生图(ai_{NN}.png)
│   ├── html_frames/         ← HTML截图源文件
│   ├── images_scaled/       ← 缩放后图片(768x1376)
│   ├── sub/                 ← 字幕srt
│   ├── seg_*.mp4            ← 分段视频
│   ├── final.mp4            ← 成片
│   ├── publish.txt          ← 抖音发布信息(标题+简介+话题,compose_video.py自动生成)
│   └── progress.json        ← 本集进度
├── E02_额上梅花/
├── 素材/
│   └── 史料/上官婉儿.txt
└── series_info.json         ← 系列总信息
```

## series_info.json 格式

```json
{
  "figure_name": "上官婉儿",
  "dynasty": "唐",
  "total_episodes": 5,
  "bgm_path": "$HOME/workspace/data/ai_drama/bgm/gaoshan_liushui_guzheng.mp3",
  "channel_name": "",
  "opening_hook_template": "{本集核心反转/焦点}",
  "ending_slogan": "读史明事理",
  "episodes": [
    {"ep": 1, "title": "刀下留人", "hook": "她爷爷被武则天杀了,她却成了武则天最信任的人"},
    {"ep": 2, "title": "额上梅花", "hook": "她脸上的梅花,不是画的,是刀刻的"}
  ],
  "created_at": "2026-07-21T20:35:00+08:00"
}
```

> 日期按北京时间(UTC+8)。

## progress.json 格式

每集独立进度文件,放在对应集目录下:

```json
{
  "figure_name": "上官婉儿",
  "dynasty": "唐",
  "episode": 1,
  "episode_title": "刀下留人",
  "current_step": 3,
  "steps_completed": [1, 2, 3],
  "output_dir": "$HOME/workspace/data/ai_drama/2026/07/历史人物_上官婉儿_序列篇/E01_刀下留人/",
  "started_at": "2026-07-21T20:35:00+08:00",
  "last_updated": "2026-07-21T20:40:00+08:00",
  "last_error": null
}
```

## 环境变量

密钥在 `$HOME/.openclaw/.env`,`load_dotenv("$HOME/.openclaw/.env")` 加载。

- `BAIDU_API_KEY` — 百度AI Studio(生图)
- `TTS_API_KEY` — 阿里DashScope TTS(qwen3-tts-flash)，严禁用于文生图
