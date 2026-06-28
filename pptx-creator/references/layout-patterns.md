# 布局模式

8 种幻灯片布局模式。每种包含 HTML 模板和 PptxGenJS 对应代码。

所有布局基于 **LAYOUT_WIDE**（13.33" × 7.5"），最小边距 0.5"。

---

## L1：标题页

全幅深色背景，大标题，副标题，可选日期/作者。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│         主标题                       │
│         副标题文字                    │
│                                     │
│         作者 · 日期                   │
│                                     │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.darkBg };
slide.addText(title, {
  x: 1, y: 2, w: 11.33, h: 2,
  fontSize: 44, fontFace: theme.headerFont, color: "FFFFFF",
  bold: true, align: "left", valign: "bottom"
});
slide.addText(subtitle, {
  x: 1, y: 4, w: 11.33, h: 1,
  fontSize: 20, fontFace: theme.bodyFont, color: "CADCFC",
  align: "left", valign: "top"
});
slide.addText(`${author} · ${date}`, {
  x: 1, y: 6, w: 11.33, h: 0.5,
  fontSize: 12, fontFace: theme.bodyFont, color: "999999",
  align: "left"
});
```

### HTML

```html
<div class="slide slide-title">
  <h1 class="title">{{标题}}</h1>
  <p class="subtitle">{{副标题}}</p>
  <p class="meta">{{作者}} · {{日期}}</p>
</div>
```

---

## L2：章节分隔页

深色或强调色背景上的粗体章节标题。标记主题转换。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│    02                               │
│    章节标题                          │
│    本部分简要描述                     │
│                                     │
│                                     │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.darkBg };
slide.addText(sectionNumber, {
  x: 1, y: 2, w: 2, h: 1,
  fontSize: 60, fontFace: theme.headerFont, color: theme.accent,
  bold: true
});
slide.addText(sectionTitle, {
  x: 1, y: 3, w: 11.33, h: 1.5,
  fontSize: 36, fontFace: theme.headerFont, color: "FFFFFF",
  bold: true
});
slide.addText(sectionDesc, {
  x: 1, y: 4.5, w: 11.33, h: 1,
  fontSize: 16, fontFace: theme.bodyFont, color: "CADCFC"
});
```

### HTML

```html
<div class="slide slide-section">
  <span class="section-number">{{编号}}</span>
  <h2 class="section-title">{{章节标题}}</h2>
  <p class="section-desc">{{章节描述}}</p>
</div>
```

---

## L3：核心观点

大标题，支撑段落，可选图标或视觉强调。

### 视觉结构

```
┌─────────────────────────────────────┐
│ ▌                                  │
│ ▌  核心观点标题                      │
│ ▌                                  │
│ ▌  支撑说明文字，详细阐述             │
│ ▌  核心观点的内容。                   │
│ ▌                                  │
│ ▌                     [图标/圆形]    │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.lightBg };
slide.addShape(pptx.ShapeType.rect, {
  x: 0.5, y: 0.5, w: 0.15, h: 3, fill: { color: theme.accent }
});
slide.addText(headline, {
  x: 1, y: 0.8, w: 10, h: 1.5,
  fontSize: 36, fontFace: theme.headerFont, color: theme.darkText,
  bold: true
});
slide.addText(body, {
  x: 1, y: 2.5, w: 10, h: 2.5,
  fontSize: 16, fontFace: theme.bodyFont, color: theme.bodyText,
  lineSpacingMultiple: 1.5
});
slide.addShape(pptx.ShapeType.ellipse, {
  x: 10.5, y: 4, w: 2, h: 2, fill: { color: theme.accent }
});
```

### HTML

```html
<div class="slide slide-key-point">
  <div class="accent-bar"></div>
  <h2 class="headline">{{标题}}</h2>
  <p class="body-text">{{正文}}</p>
  <div class="visual-accent"></div>
</div>
```

---

## L4：双栏

左侧：文字内容。右侧：图片、图表或视觉元素。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│  标题                                │
│                                     │
│  • 第一点              ┌──────────┐  │
│  • 第二点              │          │  │
│  • 第三点              │  图片/   │  │
│                        │  图表    │  │
│                        │          │  │
│                        └──────────┘  │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.lightBg };
slide.addText(heading, {
  x: 0.5, y: 0.3, w: 6, h: 1,
  fontSize: 28, fontFace: theme.headerFont, color: theme.darkText,
  bold: true
});
slide.addText(bullets.map(b => ({ text: b, options: { bullet: true, fontSize: 14 } })), {
  x: 0.5, y: 1.5, w: 5.5, h: 4.5,
  color: theme.bodyText, lineSpacingMultiple: 1.8
});
// 右侧：图片或图表
slide.addImage({ path: imagePath, x: 7, y: 1.2, w: 5.8, h: 5, sizing: { type: "cover", w: 5.8, h: 5 } });
```

### HTML

```html
<div class="slide slide-two-column">
  <div class="col col-text">
    <h2>{{标题}}</h2>
    <ul>{{要点列表}}</ul>
  </div>
  <div class="col col-visual">
    <img src="{{图片}}" alt="" />
  </div>
</div>
```

---

## L5：三栏

三个等宽卡片或内容块。适合对比、特性展示或并列要点。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│  标题                                │
│                                     │
│  ┌─────┐  ┌─────┐  ┌─────┐        │
│  │  A  │  │  B  │  │  C  │        │
│  │     │  │     │  │     │        │
│  │文字 │  │文字 │  │文字 │        │
│  └─────┘  └─────┘  └─────┘        │
│                                     │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.lightBg };
slide.addText(heading, {
  x: 0.5, y: 0.3, w: 12, h: 1,
  fontSize: 28, fontFace: theme.headerFont, color: theme.darkText, bold: true
});
const cardW = 3.5, gap = 0.5, startX = 0.75;
items.forEach((item, i) => {
  const cx = startX + i * (cardW + gap);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: cx, y: 1.8, w: cardW, h: 4.5,
    fill: { color: theme.cardBg }, rectRadius: 0.15
  });
  slide.addShape(pptx.ShapeType.ellipse, {
    x: cx + 1.25, y: 2.2, w: 1, h: 1, fill: { color: theme.accent }
  });
  slide.addText(item.title, {
    x: cx + 0.3, y: 3.5, w: cardW - 0.6, h: 0.8,
    fontSize: 18, fontFace: theme.headerFont, color: theme.darkText, bold: true, align: "center"
  });
  slide.addText(item.body, {
    x: cx + 0.3, y: 4.3, w: cardW - 0.6, h: 1.5,
    fontSize: 12, fontFace: theme.bodyFont, color: theme.bodyText, align: "center"
  });
});
```

### HTML

```html
<div class="slide slide-three-column">
  <h2>{{标题}}</h2>
  <div class="cards">
    <div class="card"><div class="icon"></div><h3>A</h3><p>...</p></div>
    <div class="card"><div class="icon"></div><h3>B</h3><p>...</p></div>
    <div class="card"><div class="icon"></div><h3>C</h3><p>...</p></div>
  </div>
</div>
```

---

## L6：大数字

一个突出的指标/数据，配支撑说明。冲击力导向。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│  指标标签                            │
│                                     │
│  42%                                │
│                                     │
│  简短说明这个数字的含义               │
│  以及它为什么重要。                    │
│                                     │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.lightBg };
slide.addText(label, {
  x: 1, y: 1, w: 11, h: 0.8,
  fontSize: 16, fontFace: theme.bodyFont, color: theme.bodyText,
  align: "left"
});
slide.addText(number, {
  x: 1, y: 1.8, w: 11, h: 2.5,
  fontSize: 72, fontFace: theme.headerFont, color: theme.accent,
  bold: true, align: "left"
});
slide.addText(explanation, {
  x: 1, y: 4.5, w: 11, h: 1.5,
  fontSize: 16, fontFace: theme.bodyFont, color: theme.bodyText,
  lineSpacingMultiple: 1.5
});
```

### HTML

```html
<div class="slide slide-big-number">
  <p class="label">{{标签}}</p>
  <p class="number">{{数字}}</p>
  <p class="explanation">{{说明}}</p>
</div>
```

---

## L7：时间线/流程

水平步骤序列。展示进展或时间顺序。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│  标题                                │
│                                     │
│  ●────────●────────●────────●       │
│  步骤1    步骤2    步骤3    步骤4    │
│  描述     描述     描述     描述    │
│                                     │
│                                     │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.lightBg };
slide.addText(heading, {
  x: 0.5, y: 0.3, w: 12, h: 1,
  fontSize: 28, fontFace: theme.headerFont, color: theme.darkText, bold: true
});
const steps = items.length;
const stepW = 11.33 / steps;
const lineY = 3.5;
// 连接线
slide.addShape(pptx.ShapeType.line, {
  x: 1, y: lineY, w: 11.33, h: 0,
  line: { color: theme.accent, width: 2 }
});
items.forEach((item, i) => {
  const cx = 1 + i * stepW;
  // 圆形节点
  slide.addShape(pptx.ShapeType.ellipse, {
    x: cx + stepW/2 - 0.25, y: lineY - 0.25, w: 0.5, h: 0.5,
    fill: { color: theme.accent }
  });
  // 步骤标题
  slide.addText(item.title, {
    x: cx, y: lineY + 0.6, w: stepW, h: 0.6,
    fontSize: 14, fontFace: theme.headerFont, color: theme.darkText, bold: true, align: "center"
  });
  // 步骤描述
  slide.addText(item.desc, {
    x: cx, y: lineY + 1.2, w: stepW, h: 1.5,
    fontSize: 11, fontFace: theme.bodyFont, color: theme.bodyText, align: "center"
  });
});
```

### HTML

```html
<div class="slide slide-timeline">
  <h2>{{标题}}</h2>
  <div class="timeline-line"></div>
  <div class="steps">
    <div class="step"><div class="node"></div><h3>步骤1</h3><p>描述</p></div>
    <div class="step"><div class="node"></div><h3>步骤2</h3><p>描述</p></div>
    <div class="step"><div class="node"></div><h3>步骤3</h3><p>描述</p></div>
    <div class="step"><div class="node"></div><h3>步骤4</h3><p>描述</p></div>
  </div>
</div>
```

---

## L8：结尾页

深色背景呼应标题页。行动号召、联系方式或致谢。

### 视觉结构

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│         谢谢                         │
│         欢迎提问与讨论                │
│                                     │
│         email@example.com           │
│         @handle                     │
│                                     │
└─────────────────────────────────────┘
```

### PptxGenJS

```javascript
const slide = pptx.addSlide();
slide.background = { color: theme.darkBg };
slide.addText(closingText, {
  x: 1, y: 2, w: 11.33, h: 2,
  fontSize: 44, fontFace: theme.headerFont, color: "FFFFFF",
  bold: true, align: "center", valign: "middle"
});
slide.addText(subtext, {
  x: 1, y: 4, w: 11.33, h: 1,
  fontSize: 18, fontFace: theme.bodyFont, color: "CADCFC",
  align: "center"
});
slide.addText(contactInfo, {
  x: 1, y: 5.5, w: 11.33, h: 1,
  fontSize: 12, fontFace: theme.bodyFont, color: "999999",
  align: "center"
});
```

### HTML

```html
<div class="slide slide-closing">
  <h1>{{结尾文字}}</h1>
  <p class="subtext">{{副文字}}</p>
  <p class="contact">{{联系方式}}</p>
</div>
```

---

## 布局选择指南

| 内容类型 | 推荐布局 |
|---------|---------|
| 演示开场 | L1：标题页 |
| 主题转换 | L2：章节分隔页 |
| 核心论点/论题 | L3：核心观点 |
| 配图特性展示 | L4：双栏 |
| 对比/特性展示 | L5：三栏 |
| 关键指标/数据 | L6：大数字 |
| 流程/路线图 | L7：时间线 |
| 演示收尾 | L8：结尾页 |

**规则：**
- 绝不在连续页面使用相同布局
- 每个演示必须以 L1 开头、L8 结尾
- 在主要章节之间使用 L2 过渡
- L6 在有具体数字要突出时效果最好
