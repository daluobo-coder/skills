# pptx-creator

AI 驱动的专业 PPT 生成技能。根据主题或大纲，自动创建视觉独特、设计专业的幻灯片。

## ✨ 特性

- **三条生成路线**：HTML 路线、PptxGenJS 直接生成路线、模板填充路线，根据场景智能选择
- **10 套内置主题**：覆盖商务、技术、创意、教育等场景
- **8 种布局模式**：标题页、双栏、图文、数据卡片、时间轴等，避免连续页面重复
- **强制质检**：自动转 PDF 逐页视觉检查，发现问题自动修复
- **自进化机制**：用户反馈→提炼可执行规则→写入经验库，越用越好
- **进度反馈**：每个耗时步骤主动告知用户进度

## 📦 目录结构

```
pptx-creator/
├── SKILL.md                          # 主流程 + 设计规范
├── scripts/
│   ├── html_to_pptx.js               # HTML → PPTX 转换脚本
│   └── fill_template.py              # 模板填充脚本
├── references/
│   ├── design-spec.md                # 设计规范（色彩/版式/组件库/图表配色）
│   ├── layout-patterns.md            # 8 种布局模式（含 HTML 模板 + PptxGenJS 代码）
│   ├── lessons-learned.md            # 实战踩坑经验（生成前必读）
│   ├── pptx-quick-ref.md             # PptxGenJS API 速查
│   ├── improvement-loop.md           # 持续改进机制
│   └── usage-log.md                  # 使用记录
└── assets/
    └── themes/                       # 10 套主题定义
        ├── midnight-executive.md
        ├── ocean-gradient.md
        ├── charcoal-minimal.md
        ├── cherry-bold.md
        ├── coral-energy.md
        ├── teal-trust.md
        ├── forest-moss.md
        ├── sage-calm.md
        ├── berry-cream.md
        └── warm-terracotta.md
```

## 🎨 内置主题

| 主题 | 适用场景 |
|------|----------|
| **午夜商务** | 董事会演示、季度报告、高管摘要、投资人路演、战略提案 |
| **海洋渐变** | 金融分析、研究演示、学术会议、医疗健康、政府报告 |
| **炭灰极简** | 技术演讲、架构评审、设计评审、极简品牌演示、开发者大会 |
| **樱桃冲击** | 销售推介、竞品分析、危机沟通、紧急报告、主题演讲 |
| **珊瑚活力** | 创业路演、营销演示、产品发布、增长报告、创意提案 |
| **青绿信赖** | SaaS 产品演示、科技创业、数据看板、金融科技、B2B 演示 |
| **森林苔藓** | 可持续发展报告、环保演示、农业、健康、有机品牌、教育 |
| **鼠尾草宁静** | 医疗健康、心理咨询、教育、公益组织、正念、人力资源演示 |
| **浆果奶油** | 时尚、美妆、奢侈品牌、杂志风格演示、艺术画廊、活动策划 |
| **暖陶土** | 室内设计、餐饮、酒店、文化演示、手作品牌、叙事展示 |

## 🔧 依赖

- **PptxGenJS**：`npm install -g pptxgenjs` — 从零创建 .pptx
- **markitdown**：`pip install "markitdown[pptx]"` — 从 .pptx 提取文本
- **LibreOffice** (`soffice`) — 质检时转 PDF
- **Poppler** (`pdftoppm`) — 质检时 PDF 转图片

## 🚀 使用方式

在 OpenClaw 中安装此 skill 后，直接说：

- "做个PPT"
- "生成演示文稿"
- "制作幻灯片"
- "我需要一套幻灯片"

AI 会自动触发此 skill，引导你选择主题、确认大纲，然后生成 PPT。

## 🔄 自进化机制

这是 pptx-creator 最独特的设计——它会从每次使用中学习：

1. **用户反馈 → 提炼规则**：不是简单记录"用户不喜欢"，而是转化为可执行的设计规则（如"绿色文字用 #2E7D32"）
2. **经验积累**：技术陷阱、布局经验、对比度规则自动写入经验库
3. **反馈升级**：同类反馈出现 3 次以上，从具体案例升级为通用设计规范
4. **定期整理**：每 5 次使用后自动健康检查，去重、升级、清理过时规则

## 📄 许可

MIT
