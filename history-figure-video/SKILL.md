---
name: history-figure-video
description: 历史人物抖音短视频生成。史料→旁白→AI生图→百炼TTS配音→字幕→合成竖屏视频。当用户提到"历史人物视频""人物传记视频""做个历史视频""历史短视频""历史人物故事视频""帮我讲讲XX的故事并做成视频""XX的视频怎么做"时使用此skill。即使用户只给出人物名并要求生成视频,也应触发。适用于抖音历史赛道"平章说"频道的序列篇短视频制作。
---

# 历史人物短视频生成

## 核心原则

1. **分步执行,每步汇报** — 每完成一步必须向用户汇报进度
2. **CPU精准管控** — 只在视频合成(步骤7)时切换CPU 100%+开睿频,完成后立即切回40%+关睿频
3. **图片逐张质检** — 步骤4b逐张审查,每张汇报结果

## 执行方式

用 `sessions_spawn` 启动独立subagent执行全流程,`context="isolated"`。

**序列篇模式**:先完成全系列规划(步骤1-3),确认后逐集制作(步骤4-8循环)。

```
sessions_spawn(
  task="按照 ~/.openclaw/skills/history-figure-video/SKILL.md 流程,生成历史人物序列篇视频。人物名:{用户指定的名字}。先读SKILL.md,然后按步骤执行。序列篇模式:先完成全系列规划,确认后逐集制作。",
  context="isolated",
  mode="run",
  taskName="history-figure-video"
)
```

## 前置依赖

- Python 3.12+、ffmpeg+ffprobe、playwright、Pillow、python-dotenv、pypinyin、requests
- 百度AI Studio API Key(`BAIDU_API_KEY`,配置在 `$HOME/.openclaw/.env`)
- TTS API Key(`TTS_API_KEY`,配置在 `$HOME/.openclaw/.env`) — **仅用于TTS(qwen3-tts-flash)，严禁用于文生图**
- Noto Sans CJK SC 字体(系统已装)

## 流程概览(8步)

```
1 去重检查 → 2 素材获取 → 3 文案改写+避多音字+去AI味+质检 → 4 AI生图 → 4b 逐张图片质检 → 5 HTML截图 → 6 TTS+字幕 → 7 合成视频+收尾 → 8 抖音发布
```

| 步骤 | 耗时 | 执行方式 | CPU |
|------|------|----------|-----|
| 1 去重 | <5s | 同步 | 40% |
| 2 素材 | 10-30s | 同步 | 40% |
| 3 文案 | 30-60s | 同步 | 40% |
| 4 生图 | 2-5min | 后台 | 40% |
| 4b 质检 | 1-3min | 逐张 | 40% |
| 5 截图 | 30-60s | 后台 | 40% |
| 6 TTS | 2-5min | 后台 | 40% |
| 7 合成+收尾 | 3-5min | 后台 | **100%→40%** |
| 8 发布 | 1-3min/集 | 串行 | 40% |

详细流程见 `references/workflow.md`。

---

## 1 去重检查(同步,<5s)

复用 `stories.db`,source字段用"历史人物"。候选人物见 `references/figure-candidates.md`。

完成后:创建系列输出目录,写入 `series_info.json`,创建首集目录,写入 `progress.json`(current_step=1)。

## 2 素材获取(同步,10-30s)

优先web_fetch抓维基百科,备选百度百科,ctext.org抓古籍原文。**正史+野史+墓志铭同时抓取,分开标注来源**。

素材存储格式见 `references/workflow.md`。

## 3 文案改写+避多音字+去AI味+质检(同步,30-60s)

这是最关键的步骤,包含5个子步骤:

- **3a 文案改写** — 易中天式说史风格,正史为主野史为辅标注出处。改写模板和详细原则见 `references/workflow.md`
- **3b 避多音字** — pypinyin逐字检查,替换策略见 `references/polyphone-replace.md`
- **3c 史实排错** — 6类核查(年代/人物关系/官职/引文/时间跨度/出处),详细流程见 `references/workflow.md`
- **3d 去AI味** — 6步流程,见 `references/deai-checklist.md`
- **3e 文案质检** — 七角色评审,最低分≥90才通过

## 4 AI生图(后台,2-5min)

**⚠️ 绝对禁止自行编写生图脚本。生图只能通过以下命令执行，不得修改、不得替换、不得绕过：**

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/generate_images.py <episode_dir>
```

**⚠️ 如果你在步骤4中写了任何新的.py脚本或调用了任何非百度API，你就是在犯错。**

**⚠️ 文生图必须串行调用，禁止并发。每次只调一张图，等上一张完成后再调下一张。多集制作时也必须逐集串行，禁止同时为多集生图。**

脚本读取script.json的bg_prompt，调用百度AI Studio API(ERNIE-Image-Turbo)生成图片，失败时PIL渐变兜底。输出到 `images/ai_{NN}.png`。脚本内部已强制串行（逐张生成，每张间隔1秒）。

**⚠️ TTS_API_KEY仅用于TTS(步骤6)，严禁用于文生图。DashScope的wanx-v1、image-synthesis、multimodal-generation等文生图API一律禁止调用。**

风格用"中国风历史画"或"工笔重彩",人物用剪影或侧脸。**⚠️ prompt禁用"古代""年代"等含"代"字的词**(AI会把"代"字渲染到画面上),用"古时""旧时"替代。所有prompt末尾加"无文字无汉字"。详细prompt示例见 `references/workflow.md`。

## 4b 逐张图片质检

逐张审查,每张汇报。FAIL处理同folk-story-video。

## 5 HTML截图(后台,30-60s)

Playwright渲染768x1376截图。视觉风格(配色/字号/布局)见 `references/style-guide.md`。**⚠️ 钩子页纯背景图不叠加文字,故事页只显示章节标题,旁白文字禁止打在图片上**(只通过TTS配音+底部字幕传达)。

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/screenshot.py <episode_dir>
```

## 6 TTS+字幕(后台,2-5min)

百炼 qwen3-tts-flash,音色Vincent。句间停顿:句号0.5s/逗号0.2s/分号0.4s。字幕14px加粗,按标点分行显示。**停顿期间字幕保持显示(延伸到下一句开始),避免闪烁**。

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/tts_subtitle.py <episode_dir>
```

## 7 合成视频+收尾(后台,3-5min)

**⚠️ 步骤7开始前切换CPU至100%+开睿频**

```bash
echo 100 | sudo tee /sys/devices/system/cpu/intel_pstate/max_perf_pct
echo 0 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo  # 0=启用睿频
```

compose_video.py 读取步骤6已生成的音频和SRT,完成:预缩放帧图→合成节视频(含音效叠加)→拼接→字幕烧录→BGM混合→复制到media目录→更新progress.json。

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/compose_video.py <episode_dir>
```

**⚠️ 完成后立即切回CPU 40%+关睿频**

```bash
echo 40 | sudo tee /sys/devices/system/cpu/intel_pstate/max_perf_pct
echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo  # 1=禁用睿频
```

完成后:更新数据库(source="历史人物"),更新series_info.json,用 `<qqmedia>` 标签发送视频,汇报用户。

**⚠️ publish.txt 由 compose_video.py 自动生成,无需手动创建。** 脚本从script.json提取figure_name/ep/title/opening_hook/dynasty自动写入,格式为三行(标题/简介/话题)。如需修改,在脚本执行后编辑即可。

---

## 8 抖音发布(串行,每集1-3min)

### 8.1 发布前准备

**cookie有效检查:**

```bash
cd $HOME/workspace/social-auto-upload && xvfb-run python sau_cli.py douyin check --account douyin_uploader
```

输出 `valid` 才可继续。cookie失效则重新扫码登录:

```bash
cd $HOME/workspace/social-auto-upload && xvfb-run python sau_cli.py douyin login --account douyin_uploader --headless
```

登录会生成二维码图片,路径类似 `cookies/douyin_douyin_uploader_login_qrcode_*.png`。需发给用户扫码(用message工具发送图片)。

### 8.2 单集发布命令

```bash
cd $HOME/workspace/social-auto-upload && xvfb-run python sau_cli.py douyin upload-video \
  --account douyin_uploader \
  --file <视频文件路径> \
  --title "<标题>" \
  --desc "<简介>" \
  --tags 标签1,标签2,标签3,标签4 \
  --schedule "YYYY-MM-DD HH:MM" \
  --declaration "内容由AI生成" \
  --headless
```

参数说明:
- `--file`: 最终视频路径,位于 `$HOME/workspace/data/ai_drama/{yyyy}/{mm}/历史人物_{人物名}_序列篇/E{NN}_{集标题}/final.mp4`
- `--title`: publish.txt第一行
- `--desc`: publish.txt第二行
- `--tags`: publish.txt第三行的话题,逗号分隔(去掉#号)
- `--declaration`: 固定为 `"内容由AI生成"`

**话题规则**:必带 `#平章说` `#{人物名}` `#{朝代}` `#人文历史`,再按内容选带1-2个话题,详见 `references/style-guide.md`。

### 8.3 ⚠️ 时间陷阱：时区转换

**这是最容易出错的地方,必须注意:**

**服务器运行在UTC时区**,而抖音创作者平台期望北京时间(UTC+8)。

`sau` CLI的 `--schedule` 接收的是naive datetime字符串(无时区信息),直接填入抖音的输入框。抖音平台将该时间视为UTC,自动转换为北京时间显示。

**错误示例** (你写了北京时间,但它被当成UTC):
```
--schedule "2026-07-28 20:15"
# 抖音上显示为: 2026-07-29 04:15 (北京时间)
# 原因: 20:15 UTC = 次日04:15 北京时间
```

**正确做法** (传UTC时间,让抖音自行转换):
```
--schedule "2026-07-28 12:15"
# 抖音上显示为: 2026-07-28 20:15 (北京时间) ✓
# 原因: 12:15 UTC = 20:15 北京时间
```

**换算公式**: `--schedule`传的时间 = 目标北京时间 - 8小时

### 8.4 序列篇批量发布计划

对于4-5集序列篇,建议每晚20:15(北京时间)更新:

| 集数 | UTC传参 | 抖音显示(北京时间) |
|------|---------|-------------------|
| E01 | `--schedule "YYYY-07-28 12:15"` | 7月28日 20:15 |
| E02 | `--schedule "YYYY-07-29 12:15"` | 7月29日 20:15 |
| E03 | `--schedule "YYYY-07-30 12:15"` | 7月30日 20:15 |
| E04 | `--schedule "YYYY-07-31 12:15"` | 7月31日 20:15 |

**务必将日期替换为实际年份的当天日期。**

### 8.5 使用xvfb-run

服务器无图形界面,所有`playwright`相关命令必须用 `xvfb-run` 包裹:

```bash
xvfb-run python sau_cli.py douyin login ...
xvfb-run python sau_cli.py douyin check ...
xvfb-run python sau_cli.py douyin upload-video ...
```

---

## CPU管理

| 时机 | 操作 |
|------|------|
| 步骤7开始前 | CPU 100% + 开睿频 |
| 步骤7完成后 | CPU 40% + 关睿频 |

## 输出

- 系列输出目录:`$HOME/workspace/data/ai_drama/{yyyy}/{mm}/历史人物_{人物名}_序列篇/`
- 每集最终视频:`E{NN}_{集标题}/final.mp4`
- 每集发布信息:`E{NN}_{集标题}/publish.txt`(标题+简介+话题,由compose_video.py自动生成)
- QQ Bot发送:复制到 `~/.openclaw/media/qqbot/`,用 `<qqmedia>` 标签

## 注意事项

1. **sessions_spawn 独立subagent执行**
2. **失败写 `last_error` 到 `progress.json`**,最多重试3次
3. **CPU在视频合成时100%+睿频**,合成完成后立即切回40%+关睿频
4. **文案必须避多音字**,TTS审查员角色必须通过
5. 背景图base64 data URI内嵌HTML
6. 完成后切回CPU 40%+关睿频
7. QQ Bot发送视频用 `<qqmedia>` 标签
8. 去重+更新数据库
9. `progress.json` 存在则从 `current_step` 继续
10. **⚠️ 抖音定时发布时区陷阱**:服务器UTC,传`--schedule`时用**UTC时间**(目标北京时间-8h),详见步骤8.3

## 参考文档

| 文件 | 内容 |
|------|------|
| `references/workflow.md` | 8步详细流程(素材格式、文案模板、史实排错、质检角色、生图prompt) |
| `references/style-guide.md` | 抖音赛道风格规范(钩子、BGM、音效、标题、视觉风格、字幕、配音) |
| `references/data-format.md` | 数据路径、目录结构、series_info.json、progress.json格式 |
| `references/polyphone-replace.md` | 多音字替换策略+检查脚本 |
| `references/figure-candidates.md` | 历史人物候选列表 |
| `scripts/generate_images.py` | AI生图脚本(百度ERNIE-Image-Turbo,读取script.json的bg_prompt) |
| `scripts/tts_subtitle.py` | 百炼TTS+字幕生成脚本(轻量版,仅TTS+SRT) |
| `scripts/tts_common.py` | TTS公共模块(被tts_subtitle.py和compose_video.py共用) |
| `scripts/compose_video.py` | 视频合成脚本(读取步骤6音频+SRT,含音效叠加,步骤7一体化) |
| `scripts/screenshot.py` | HTML截图脚本(封面/故事/结尾页) |
| `references/deai-checklist.md` | 去AI味6步清单 |
