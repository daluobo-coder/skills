# PptxGenJS 速查手册

用 JavaScript 创建 .pptx 文件。安装：`npm install -g pptxgenjs`

## 基本设置

```javascript
const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();

// 设置演示文稿属性
pptx.layout = "LAYOUT_WIDE";  // 13.33" x 7.5"（16:9，推荐）
pptx.author = "作者名";
pptx.title = "演示文稿标题";

// 添加幻灯片
const slide = pptx.addSlide();

// 保存
await pptx.writeFile({ fileName: "output.pptx" });
```

## 布局常量

| 常量 | 尺寸 | 比例 |
|------|------|------|
| `LAYOUT_WIDE` | 13.33" × 7.5" | 16:9 |
| `LAYOUT_4x3` | 10" × 7.5" | 4:3 |

**始终使用 LAYOUT_WIDE**，除非用户明确要求 4:3。

## 单位

所有位置和尺寸默认使用**英寸**。

```javascript
slide.addText("你好", { x: 1, y: 2, w: 4, h: 1 });  // 英寸
```

## 幻灯片背景

```javascript
// 纯色
slide.background = { color: "1E2761" };

// 渐变
slide.background = { fill: { type: "gradient", stops: [
  { position: 0, color: "1E2761" },
  { position: 100, color: "065A82" }
]}};
```

## 文本

```javascript
// 简单文本
slide.addText("标题", {
  x: 0.5, y: 0.5, w: 12, h: 1.5,
  fontSize: 36, fontFace: "Arial",
  color: "FFFFFF", bold: true,
  align: "left", valign: "middle"
});

// 多格式文本（文本片段）
slide.addText([
  { text: "关键指标：", options: { fontSize: 16, color: "666666" } },
  { text: "42%", options: { fontSize: 36, color: "F96167", bold: true } }
], { x: 1, y: 2, w: 5, h: 2 });

// 项目符号列表
slide.addText([
  { text: "第一点", options: { bullet: true, fontSize: 14 } },
  { text: "第二点", options: { bullet: true, fontSize: 14 } },
  { text: "第三点", options: { bullet: true, fontSize: 14 } }
], { x: 1, y: 2, w: 8, h: 4, color: "333333" });

// 编号列表
slide.addText([
  { text: "步骤一", options: { bullet: { type: "number" }, fontSize: 14 } },
  { text: "步骤二", options: { bullet: { type: "number" }, fontSize: 14 } }
], { x: 1, y: 2, w: 8, h: 3, color: "333333" });
```

## 形状

```javascript
// 矩形
slide.addShape(pptx.ShapeType.rect, {
  x: 0, y: 0, w: 0.3, h: 7.5,
  fill: { color: "F96167" }
});

// 圆角矩形
slide.addShape(pptx.ShapeType.roundRect, {
  x: 1, y: 2, w: 5, h: 3,
  fill: { color: "E8F4F8" },
  rectRadius: 0.15
});

// 圆形（用椭圆，宽高相等）
slide.addShape(pptx.ShapeType.ellipse, {
  x: 5, y: 1, w: 2, h: 2,
  fill: { color: "028090" }
});

// 线条
slide.addShape(pptx.ShapeType.line, {
  x: 1, y: 3, w: 11, h: 0,
  line: { color: "CCCCCC", width: 1 }
});
```

## 图片

```javascript
// 从文件
slide.addImage({ path: "image.png", x: 1, y: 1, w: 4, h: 3 });

// 从 URL
slide.addImage({ path: "https://example.com/img.png", x: 1, y: 1, w: 4, h: 3 });

// 从 base64
slide.addImage({ data: "image/png;base64,iVBOR...", x: 1, y: 1, w: 4, h: 3 });

// 尺寸适配
slide.addImage({
  path: "image.png", x: 1, y: 1, w: 4, h: 3,
  sizing: { type: "cover", w: 4, h: 3 }  // "cover" 或 "contain"
});
```

## 表格

```javascript
const rows = [
  [{ text: "表头1", options: { bold: true, color: "FFFFFF", fill: { color: "1E2761" } } },
   { text: "表头2", options: { bold: true, color: "FFFFFF", fill: { color: "1E2761" } } }],
  [{ text: "单元格1" }, { text: "单元格2" }],
  [{ text: "单元格3" }, { text: "单元格4" }]
];

slide.addTable(rows, {
  x: 1, y: 2, w: 11,
  border: { type: "solid", pt: 0.5, color: "CCCCCC" },
  colW: [5.5, 5.5],
  rowH: [0.5, 0.4, 0.4],
  fontSize: 12,
  color: "333333"
});
```

## 图表

```javascript
// 柱状图
slide.addChart(pptx.ChartType.bar, [
  { name: "系列1", labels: ["Q1", "Q2", "Q3", "Q4"], values: [12, 25, 18, 30] }
], {
  x: 1, y: 1.5, w: 8, h: 5,
  showValue: true,
  chartColors: ["028090"],
  catAxisLabelFontSize: 10,
  valAxisLabelFontSize: 10
});

// 饼图
slide.addChart(pptx.ChartType.pie, [
  { name: "占比", labels: ["A", "B", "C"], values: [40, 35, 25] }
], {
  x: 3, y: 1.5, w: 6, h: 5,
  showPercent: true,
  chartColors: ["1E2761", "028090", "97BC62"]
});
```

## 页码与页脚

```javascript
// 页码（单页）
slide.addText([
  { text: "3", options: { fontSize: 10, color: "999999" } }
], { x: 12.5, y: 7, w: 0.5, h: 0.3, align: "right" });

// 页脚条
slide.addShape(pptx.ShapeType.rect, {
  x: 0, y: 7.1, w: 13.33, h: 0.4,
  fill: { color: "1E2761" }
});
slide.addText("公司机密", {
  x: 0.5, y: 7.1, w: 5, h: 0.4,
  fontSize: 9, color: "FFFFFF", valign: "middle"
});
```

## 母版幻灯片（可复用布局）

```javascript
// 定义母版
pptx.defineSlideMaster({
  title: "内容页_浅色",
  background: { color: "F5F7FA" },
  objects: [
    // 侧边强调条
    { rect: { x: 0, y: 0, w: 0.3, h: 7.5, fill: { color: "028090" } } },
    // 页脚
    { rect: { x: 0, y: 7.1, w: 13.33, h: 0.4, fill: { color: "1E2761" } } },
    { text: { text: "公司名", options: { x: 0.5, y: 7.1, w: 5, h: 0.4, fontSize: 9, color: "FFFFFF" } } }
  ]
});

// 使用母版
const slide = pptx.addSlide({ masterName: "内容页_浅色" });
```

## 常见坑

| 坑 | 解决方案 |
|----|----------|
| 颜色带 `#` 前缀 | PptxGenJS 用**不带** `#` 的十六进制：`"1E2761"` 而非 `"#1E2761"` |
| 文字溢出 | 在文本框上设置 `shrinkText: true` 或 `autoFit: true` |
| 布局尺寸错误 | 始终先设置 `pptx.layout = "LAYOUT_WIDE"` |
| 图片找不到 | 使用绝对路径或相对于当前工作目录的路径 |
| 表格列不对齐 | 显式设置 `colW` 数组，总和必须等于 `w` |
| 字体不渲染 | 使用标准字体（Arial、Calibri、Georgia 等） |
| 幻灯片太拥挤 | 最小边距 0.5"，每页最多 5-6 个要点 |
| 标题下的装饰线 | 不要加——那是 AI 生成的标志 |
