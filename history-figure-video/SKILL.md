---
name: history-figure-video
description: 历史人物抖音短视频/中视频生成（段岳泽式史料分歧文风）。史料→JSON脚本→风控机检→AI生图→TTS配音→字幕→合成竖屏视频→发布。当用户提到"历史人物视频""人物传记视频""做个历史视频""历史短视频""历史人物故事视频""帮我讲讲XX的故事并做成视频""XX的视频怎么做"时使用此skill。即使用户只给出人物名并要求生成视频,也应触发。适用于抖音历史赛道序列篇/单集中视频制作。
---

# 历史人物短视频生成（段岳泽风·史料分歧版）

## 核心原则

1. **分步执行,每步汇报** — 每完成一步必须向用户汇报进度
2. **CPU精准管控** — 只在视频合成(步骤7)时切换CPU 100%+开睿频,完成后立即切回40%+关睿频
3. **图片逐张质检** — 步骤4b逐张审查,每张汇报结果
4. **文风铁律** — 大白话短句、零抒情、不站队;史料分歧是核心亮点;结尾不给结论(默认"留给后人判断")
5. **风控分级** — 违规词硬拦、定性词要归属、情绪词只提示;先机检(copy_guard)后评审
6. **无频道硬绑定** — 默认不带频道名;用户明确要求品牌化时,结尾金句后另起一句加"读史明事理"

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
- **edge-tts ≥7.3.1**(步骤6默认TTS,免费,需能访问微软语音接口)
- 百度AI Studio API Key(`BAIDU_API_KEY`,配置在 `$HOME/.openclaw/.env`)
- TTS API Key(`TTS_API_KEY`,配置在 `$HOME/.openclaw/.env`) — **仅用于TTS(qwen3-tts-flash)，严禁用于文生图**
- Noto Sans CJK SC 字体(系统已装)

## 流程概览(8步)

```
1 去重检查 → 2 素材获取 → 3 文案改写(段岳泽风)+风控机检 → 4 AI生图 → 4b 逐张图片质检 → 5 HTML截图 → 6 TTS+字幕 → 7 合成视频+收尾 → 8 抖音发布
```

| 步骤 | 耗时 | 执行方式 | CPU |
|------|------|----------|-----|
| 1 去重 | <5s | 同步 | 40% |
| 2 素材 | 10-30s | 同步 | 40% |
| 3 文案+机检 | 30-90s | 同步 | 40% |
| 4 生图 | 2-5min | 后台 | 40% |
| 4b 质检 | 1-3min | 逐张 | 40% |
| 5 截图 | 30-60s | 后台 | 40% |
| 6 TTS | 2-5min | 后台 | 40% |
| 7 合成+收尾 | 3-5min | 后台 | **100%→40%** |
| 8 发布 | 1-3min/集 | 串行 | 40% |

详细流程见 `references/workflow.md`(注意:其中 3a 旧文风条款已被 `references/copywriting-duanyueze.md` 覆盖)。

---

## 1 去重检查(同步,<5s)

复用 `stories.db`,source字段用"历史人物"。候选人物见 `references/figure-candidates.md`。

完成后:创建系列输出目录,写入 `series_info.json`,创建首集目录,写入 `progress.json`(current_step=1)。

## 2 素材获取(同步,10-30s)

优先web_fetch抓维基百科,备选百度百科,ctext.org抓古籍原文。**正史+野史+墓志铭同时抓取,分开标注来源**。

**按"分歧"组织素材**:每条关键事实标注属于哪一方(A史料/B史料),抓不到两方以上记载的题材,在步骤3换角度或换选题。

素材存储格式见 `references/workflow.md`。

## 3 文案改写+避多音字+史实排错+风控机检+质检(同步,30-90s)

**⚠️ 文风以 `references/copywriting-duanyueze.md` 为准,workflow.md 第3a节的易中天式移时、现代职场类比、结尾口号全部作废。**

六个子步骤,顺序固定:

### 3a 按段岳泽规范成稿

产出内容 JSON(`title/hook/main_body/ending/note`),再映射为 `script.json`。规范要点:

- 钩子二选一:反常识误区("很多人以为……但查阅史料并非如此")或疑问引入("不同史书给出了完全不一样的记载")
- 主体平铺史实,**必须写出"A史料记载……；B史料记载……"的分歧**,这是核心亮点
- 客观陈述,不评价人物好坏,不下绝对定论
- 结尾默认:"不同史料各有依据,至于真相如何,留给后人自行判断。"(用户明确要氛围感才用折中版)
- **全文旁白 280～420 字**,单句 ≤20 字,大白话,零抒情,禁现代类比
- 每节 `source` 必填,可指回抓到的原文

字段映射与示例见 `references/copywriting-duanyueze.md` 第 5、7 节。

### 3b 避多音字

**必须**用pypinyin逐字检查旁白文本,标记所有多音字。检查脚本见 `references/polyphone-replace.md`。所有多音字必须替换为无歧义表达。

### 3c 史实排错(必做)

文案写完后、机检前,**必须**逐项核查以下6类史实错误。发现任何一项即打回修改。

| 检查项 | 方法 | 常见错误 |
|--------|------|----------|
| **年代** | 关键事件年份×人物年龄交叉验证 | 出生年≠事件年-年龄、在位时间算错 |
| **人物关系** | 父子/祖孙/君臣/姻亲逐条核对 | 爷爷写成父亲、同辈写成上下级 |
| **官职/封号** | 查正史本纪/列传,注意时间线 | 封号在事件发生时还未授予 |
| **引文准确性** | 墓志铭/正史原文逐字比对 | 断章取义、张冠李戴、翻译偏差 |
| **时间跨度** | 起止年份相减,与文案表述对比 | "三十年"实际只有十四年 |
| **出处标注** | 每条标注是否与实际来源一致 | 野史标注为正史、墓志内容标注为旧唐书 |

**执行流程**:
1. 提取文案中所有**可验证事实**(人名、年份、年龄、官职、引文、出处)
2. 逐条用web_search交叉验证(至少2个独立来源)
3. 墓志铭原文必须与出土全文逐字比对
4. 发现错误→立即修正→重新验证修正后的事实
5. 输出《史实排错报告》,列出:✅已验证 / ❌已修正 / ⚠️存疑(附理由)
6. 报告存入 `script_fact_check.md`,随script.json一起保存

**⚠️ 存疑处理**:无法确认的事实,文案中必须加限定词("据说""传说归传说""有说法认为"),不得以肯定语气陈述。

### 3d 去AI味

6步流程(黑名单→否定转肯定→剥离心理锚点→对话排毒→形容词压缩→逐句自检)。详见 `references/deai-checklist.md`。

注意:本规范已禁用抒情与升华,3d 只负责清 AI 套话("值得注意的是""不得不说""让人不禁")和排比堆砌,不重复风控检查。

### 3e 风控机检(硬门槛,必须通过)

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/copy_guard.py <episode_dir>
```

分级规则:

| 级别 | 触发 | 结果 |
|------|------|------|
| 硬拦 | 现代类比/当下引申(职场、内卷、老板、KPI、放到今天、人生道理……)、敏感词 | FAIL,重写 |
| 归属 | 千古一帝/明君/暴君等定性词,前后12字无"后世/史家/《书名》/称/评价/认为" | FAIL,补出处 |
| 软提示 | 悲凉/可惜/伟大/不堪等情绪词 | 仅标记,交 3f 判断 |
| 结构 | 某节 source 为空、总字数不在 280～420 | FAIL |

退出码 0 才继续。需要明细加 `--report copy_guard_report.json`。

### 3f 文案质检

机检通过后再评审。七角色评审,最低分 ≥ 90 才通过。

| 角色 | 检查重点 |
|------|----------|
| 阅读者 | 开篇吸引力、节奏、画面感 |
| 编审 | 错别字、标点、措辞 |
| 故事家 | 因果、剧情推进、分歧是否讲清 |
| 史实复核员 | 3c报告有无遗漏、出处是否成立、定性词归属是否真实 |
| 文学顾问 | 层次、细节、活性(但不许添加抒情) |
| 毒舌读者 | AI味残留、水字数、套话结尾 |
| TTS审查员 | 多音字残留、绕口表达、TTS不友好标点 |

情绪词软提示由"文学顾问"与"毒舌读者"共同裁决:属叙事需要则保留,属强行煽情则删。

## 4 AI生图(后台,2-5min)

**⚠️ 绝对禁止自行编写生图脚本。生图只能通过以下命令执行，不得修改、不得替换、不得绕过：**

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/generate_images.py <episode_dir>
```

**⚠️ 如果你在步骤4中写了任何新的.py脚本或调用了任何非百度API，你就是在犯错。**

**⚠️ 文生图必须串行调用，禁止并发。每次只调一张图，等上一张完成后再调下一张。多集制作时也必须逐集串行，禁止同时为多集生图。**

**三引擎**:`wan`(阿里万相2.5,画质最好,~¥0.2/张,**当前欠费不可用**)、`flux`(默认,Pollinations FLUX 免费,有低分辨率+偶发503,水印脚本已裁)、`baidu`(百度 SD-XL,最快但假印章/糊细节多)。出图统一后处理为 768x1376 (9:16),失败时 PIL 渐变兜底。

```bash
# 默认 flux(约60s/张,一集6张约7-10分钟)
python3 ~/.openclaw/skills/history-figure-video/scripts/generate_images.py <episode_dir>
# 快速版/兜底
python3 ~/.openclaw/skills/history-figure-video/scripts/generate_images.py <episode_dir> --engine baidu
```

**⚠️ bg_prompt 必须写英文**(百度接口吃中文直接 400;flux 也建议英文)。格式:`traditional chinese painting, [scene], muted natural colors, soft diffused light, fine brushwork, vertical composition, no text, no characters`。负面词脚本已内置(`text, watermark, signature, seal...`)。
- 补图:`--force` 全部重跑,`--only N` 只重生第 N 张
- 禁止并发(脚本有文件锁)

**⚠️ TTS_API_KEY仅用于TTS(步骤6)，严禁用于文生图。DashScope的wanx-v1、image-synthesis、multimodal-generation等文生图API一律禁止调用。**

风格用"中国风历史画"或"工笔重彩",人物用剪影或侧脸。**⚠️ prompt禁用"古代""年代"等含"代"字的词**(AI会把"代"字渲染到画面上),用"古时""旧时"替代。所有prompt末尾加"无文字无汉字"。详细prompt示例见 `references/workflow.md`。

## 4b 逐张图片质检

**用脚本机检,不要只靠肉眼**:

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/image_qa.py <episode_dir>/images/ai_*.png
```

`image_qa.py` 用视觉模型逐张判 PASS/FAIL,检查:①真汉字/水印/假印章签名 ②畸形手指多头 ③廉价AI感/现代物品穿帮 ④过暗过曝。退出码 0=全过。

**审查标准**:构图合理、画面完整、无文字渲染(含假签名/假印章)、风格统一、人物结构正常。

### 审查流程

1. 跑 `image_qa.py`,按输出的 PASS/FAIL 逐张处理
2. **PASS** → 记录通过,继续下一张
3. **FAIL** → 执行重试流程

### 重试流程(每张图最多3轮)

a. 记录失败图片路径+失败原因+当前重试次数到 `progress.json.image_retries`
b. **回到步骤4**,重新执行 `generate_images.py <episode_dir>`(脚本幂等,重新生成全部图片)
c. **回到4b**,单独审查该张图片
d. 通过则继续;FAIL则重复a-c,满3次进入e
e. **3次均失败** → 加入 `progress.json.skipped_images` 列表,跳过该图,继续下一张

### 后续步骤对缺失图片的处理

- **步骤5 screenshot.py**:读取 `skipped_images`,对缺失图片用纯色背景+章节标题占位HTML
- **步骤7 compose_video.py**:对 `skipped_images` 中的图片用渐变/纯色兜底帧,最终汇报时列出"N张图片使用了兜底方案"
- **final 汇报**:读取 `progress.json.skipped_images`,告知用户哪些图片未能生成,建议手动补图后重新合成

全部完成后:更新 `progress.json`(current_step=4b),汇报用户进度。

## 5 HTML截图(后台,30-60s)

Playwright渲染768x1376截图。视觉风格(配色/字号/布局)见 `references/style-guide.md`。**⚠️ 钩子页纯背景图不叠加文字,故事页只显示章节标题,旁白文字禁止打在图片上**(只通过TTS配音+底部字幕传达)。

```bash
python3 ~/.openclaw/skills/history-figure-video/scripts/screenshot.py <episode_dir>
```

## 6 TTS+字幕(后台,2-5min)

默认 **edge-tts(免费)**,音色 `zh-CN-YunjianNeural`(沉稳男声),语速 `+8%`。句间停顿:句号0.5s/逗号0.2s/分号0.4s。字幕14px加粗,按标点分行显示。**停顿期间字幕保持显示(延伸到下一句开始),避免闪烁**。

- **⚠️ edge-tts 必须 ≥7.3.1**:旧版会被微软接口直接 403(已在本机升级到 7.3.1)
- 换音色:`--voice zh-CN-YunyangNeural` 等,`--list-voices` 查看全部
- 换语速:`--rate +12%` / `-5%`
- 备选付费引擎:`--engine qwen`(百炼 Vincent,需 TTS_API_KEY)

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

**话题规则**:必带 `#{人物名}` `#{朝代}` `#人文历史`,再按内容选带1-2个话题,详见 `references/style-guide.md`。

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
4. **文案必须过 copy_guard 机检(退出码0)**,再进入七角色评审;顺序不能反
5. **必避多音字**,TTS审查员角色必须通过
6. 背景图base64 data URI内嵌HTML
7. QQ Bot发送视频用 `<qqmedia>` 标签
8. 去重+更新数据库
9. `progress.json` 存在则从 `current_step` 继续
10. **⚠️ 抖音定时发布时区陷阱**:服务器UTC,传`--schedule`时用**UTC时间**(目标北京时间-8h),详见步骤8.3

## 参考文档

| 文件 | 内容 |
|------|------|
| `references/copywriting-duanyueze.md` | **文案规范(最高优先级)**:段岳泽式史料分歧文风、结构、风控分级、JSON映射、示例 |
| `references/workflow.md` | 8步详细流程(素材格式、生图prompt、合成细节);3a旧文风条款已作废 |
| `references/style-guide.md` | 抖音赛道风格规范(BGM、音效、标题、视觉风格、字幕、配音) |
| `references/data-format.md` | 数据路径、目录结构、series_info.json、progress.json格式 |
| `references/polyphone-replace.md` | 多音字替换策略+检查脚本 |
| `references/figure-candidates.md` | 历史人物候选列表 |
| `scripts/generate_images.py` | AI生图脚本(默认flux,备选baidu;英文prompt,768x1376,节流+重试) |
| `scripts/image_qa.py` | 图片质检(视觉模型机检文字/畸形/画风/明暗,退出码0=全过) |
| `scripts/tts_subtitle.py` | TTS+字幕生成脚本(轻量入口,默认edge-tts,可切qwen) |
| `scripts/tts_common.py` | TTS公共模块(edge-tts/qwen双引擎,音色指纹缓存) |
| `scripts/compose_video.py` | 视频合成脚本(读取步骤6音频+SRT,含音效叠加,步骤7一体化) |
| `scripts/screenshot.py` | HTML截图脚本(封面/故事/结尾页) |
| `scripts/copy_guard.py` | 文案风控机检(硬拦/归属/软提示/结构,退出码0才放行) |
| `references/deai-checklist.md` | 去AI味6步清单 |
