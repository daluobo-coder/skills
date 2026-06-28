# 设计规范

从实战中提炼的视觉设计规则。生成PPT时参照此文件确保专业度。

---

## 一、色彩体系

### 1.1 语义色（跨主题通用）

| 语义 | 深色文字 | 浅色背景 | 用途 |
|------|----------|----------|------|
| 风险/危险 | `C0392B` | `FDE8E8` | 负面指标、警告、高风险 |
| 关注/提醒 | `E67E22` | `FFF3E0` | 中性提醒、需关注项 |
| 健康/正面 | `2E7D32` | `C8E6C9` | 正面指标、健康状态 |
| 强调/主色 | 主题accent | 主题浅色 | 标题、关键数据、CTA |
| 中性信息 | `333333` | — | 正文、说明 |

**关键规则：**
- 绿色文字用 `2E7D32`（深绿），**不要用 `27AE60`**（太浅，投影不可读）
- 绿色背景用 `C8E6C9`（中浅绿），**不要用 `E8F8E8`**（太浅，与白底几乎无区分）
- 红色文字用 `C0392B`（稳重红），**不要用 `E74C3C`**（太亮，刺眼）
- 数据表格中的颜色编码必须与语义色一致，不要混用

### 1.2 主题色扩展规范

每个主题定义了5个基础色，实际生成时需要扩展为完整色板：

```
主题色 → 扩展色板
├── darkBg      → 页脚深色: darken 20% (如 065A82 → 0A3D5C)
├── midBg       → 数据图色: 原值 / lighten 30% (如 1C7293 → 5BA3BD)
├── deepBg      → 深强调: 原值 / 次要标题色
├── lightBg     → 内容页底: 原值
├── accent      → CTA/高亮: 原值
├── —           → 正文色: 1A1A2E (近黑，不用纯黑)
├── —           → 副文字: 666666 (中灰)
├── —           → 弱文字: 888888 (投影可辨)
├── —           → 卡片底: FFFFFF
├── —           → 表格斑马纹: F0F7FA (浅蓝灰)
└── —           → 分隔线: D0DDE5 (浅蓝灰)
```

### 1.3 深色背景上的文字色阶

| 元素 | 色值 | 对比度(vs #065A82) |
|------|------|-------------------|
| 主标题 | `FFFFFF` | >15:1 ✅ |
| 副标题 | `E0F0F8` | ~10:1 ✅ |
| 说明文字 | `C0D8E8` | ~6:1 ✅ |
| 弱化文字 | `8ABCD0` | ~4:1 ⚠️ 仅大字 |
| ❌ 避免 | `8FAFC0` | <3:1 ❌ |

---

## 二、版式规范

### 2.1 页面结构

```
┌────────────────────────────────────────┐
│ 0.25" accent bar (可选)                │
│ 0.7"   标题区                          │
│ ─────────────────────────────────────  │
│ 主内容区                               │
│                                        │
│                                        │
│ 0.45"  页脚条 (深色)                    │
└────────────────────────────────────────┘
```

- **左侧强调条**：0.25英寸宽，accent色，内容页使用
- **页脚条**：0.4英寸高，darkBg darken 20%，左侧报告名+右侧页码
- **标题区**：y=0.3, h=0.8, fontSize=24, 粗体
- **内容区**：y=1.2 至 y=6.7

### 2.2 卡片规范

| 属性 | 值 | 说明 |
|------|-----|------|
| 圆角 | 0.12" | roundRect, 不要0.05（太方）或0.3（太圆） |
| 阴影 | blur:6, offset:2, opacity:0.1 | 轻阴影，不要过重 |
| 背景 | #FFFFFF | 白色卡片，不用浅灰 |
| 顶部色条 | 0.08" 高 | 比整块色头更精致 |
| 左侧色条 | 0.08" 宽 | 语义色，标识分类 |
| 间距 | 0.15" (紧凑) / 0.3" (标准) | 紧凑用于网格，标准用于独立卡片 |
| 内边距 | 0.2-0.3" | 文字不要贴边 |

### 2.3 卡片高度计算

**核心原则：卡片高度匹配内容量，不要留大量底白。**

| 内容量 | 推荐高度 | 示例 |
|--------|----------|------|
| 标题+1行数据 | 1.0-1.2" | 关键发现卡片 |
| 标题+2行数据 | 1.6-1.8" | 指标卡片 |
| 标题+3条要点 | 2.0-2.3" | 子卡片 |
| 色块头+4条要点 | 4.0-4.5" | 策略卡片 |
| 色块头+2指标+2行动 | 5.0-5.3" | 风险分层卡片 |

**反模式：** 4条要点+5.3英寸高度 = 底部30%空白 ❌

### 2.4 信息层级

每页最多3层信息，每层用字号+字重+颜色三重区分：

```
L1 标题层：24pt+ | bold | darkText / accent
L2 数据层：14-22pt | bold | 语义色(红/绿/橙)
L3 说明层：10-12pt | regular | subText
```

**绝不允许：** 同一层级的两个元素用相同字号+字重但不同颜色（视觉混乱）

---

## 三、组件库

### 3.1 指标卡片（核心数据展示）

```javascript
// 大号数字 + 小标签 + 说明
s.addShape(pptx.ShapeType.roundRect, {
  x, y, w, h: 1.0,
  fill: { color: cardBg }, rectRadius: 0.1,
  shadow: { type: "outer", blur: 4, offset: 1, color: "000000", opacity: 0.08 }
});
s.addShape(pptx.ShapeType.rect, { x, y, w: 0.08, h: 1.0, fill: { color: accent } }); // 侧色条
s.addText(label,  { x: x+0.2, y: y+0.08, w, h: 0.3, fontSize: 12, color: subText, bold: true });
s.addText(value,  { x: x+0.2, y: y+0.35, w, h: 0.35, fontSize: 18, color: accent, bold: true });
s.addText(desc,   { x: x+0.2, y: y+0.7, w, h: 0.25, fontSize: 10, color: subText });
```

### 3.2 风险卡片（三级状态）

```javascript
// 三色体系：红/橙/绿
const riskColors = {
  high:   { text: "C0392B", bg: "FDE8E8", dot: "C0392B" },
  medium: { text: "E67E22", bg: "FFF3E0", dot: "E67E22" },
  low:    { text: "2E7D32", bg: "C8E6C9", dot: "2E7D32" }
};
// 卡片底色用风险bg，文字用风险text
// 大号数字右对齐 valign:bottom 保证跨卡片对齐
```

### 3.3 时间轴

```javascript
// 水平时间轴
const lineY = 2.5;
s.addShape(pptx.ShapeType.line, {
  x: startX, y: lineY, w: totalW, h: 0,
  line: { color: accent, width: 3 }  // 3pt粗线
});
// 箭头终点
s.addShape(pptx.ShapeType.triangle, {
  x: endX, y: lineY - 0.2, w: 0.4, h: 0.4,
  fill: { color: accent }, rotate: 90
});
// 节点圆
s.addShape(pptx.ShapeType.ellipse, {
  x: nodeX, y: lineY - 0.25, w: 0.5, h: 0.5,
  fill: { color: accent }
});
// 季度标签在轴上方，数值在轴下方
```

### 3.4 策略卡片（顶部色块+要点列表）

```javascript
// 色块头（含图标+标题）
s.addShape(pptx.ShapeType.roundRect, {
  x, y, w, h: 1.2,
  fill: { color: accent }, rectRadius: 0.12
});
// 白底覆盖（消除色块底圆角）
s.addShape(pptx.ShapeType.rect, { x, y: y+1.0, w, h: 0.3, fill: { color: accent } });
s.addShape(pptx.ShapeType.roundRect, { x, y: y+1.1, w, h: 0.3, fill: { color: cardBg } });

// 图标（大号）
s.addText(icon, { x, y: y+0.1, w, h: 0.55, fontSize: 28, align: "center" });
// 标题（白色）
s.addText(title, { x: x+0.15, y: y+0.6, w: w-0.3, h: 0.5, fontSize: 15, color: "FFFFFF", bold: true, align: "center" });
```

### 3.5 表格

```javascript
// 表头：深色底+白字
// 数据行：斑马纹（白+F0F7FA交替）
// 语义色在单元格级别设置，不要在行级别
// 风险图标列：🔴 ⚠️ ✅ 配合对应颜色
const headerOpts = { bold: true, color: "FFFFFF", fill: { color: deepBg }, fontSize: 12, align: "center" };
const cellOpts = (row, color) => ({
  fontSize: 11, color, fill: { color: row % 2 === 0 ? "FFFFFF" : "F0F7FA" },
  bold: color === "C0392B", align: "center"
});
```

---

## 四、排版细节

### 4.1 字号体系

| 元素 | 字号 | 字重 | 字体 |
|------|------|------|------|
| 封面主标题 | 44-48pt | bold | headerFont |
| 封面副标题 | 28pt | bold | headerFont |
| 章节分隔编号 | 64pt | bold | headerFont |
| 章节分隔标题 | 36pt | bold | headerFont |
| 页面标题 | 24-28pt | bold | headerFont |
| 卡片标题 | 16-18pt | bold | headerFont |
| 大号数据 | 20-30pt | bold | headerFont |
| 正文 | 12-14pt | regular | bodyFont |
| 要点/条目 | 11-12pt | regular | bodyFont |
| 注释/标签 | 9-10pt | regular | bodyFont |

### 4.2 对齐规则

- **标题左对齐**（非居中）
- **正文左对齐**
- **数据右对齐**（数值列、百分比）
- **编号/图标居中**
- **同一行卡片内大号数字用 valign:bottom** 确保底部对齐

### 4.3 间距规则

| 元素 | 间距 |
|------|------|
| 标题与内容 | 0.5" |
| 卡片之间 | 0.15-0.3" |
| 卡片内条目 | 0.6-0.7" (紧凑) / 0.85" (宽松) |
| 时间轴标签与数值 | 0.3" (轴上方→轴→轴下方) |
| 分析要点之间 | 0.32-0.35" |
| 页脚与内容 | 0.4" |

### 4.4 装饰元素

| 元素 | 规格 | 用途 |
|------|------|------|
| 封面装饰圆 | 3-5" 直径 | 右上/右下，accent色 |
| 章节分隔虚线 | 3-4.5" 长，1.5pt | 右侧4条，长短交替 |
| 虚线端圆点 | 0.16" 直径 | accent色 |
| 左侧强调条 | 0.25"×7.1" | 内容页 |
| 分隔线 | 3-4" 宽，0.05" 高 | accent色，标题与副标题之间 |
| 页脚条 | 13.33"×0.4" | darkBg darken 20% |

---

## 五、图表配色

### 5.1 柱状图/条形图

```javascript
chartColors: [midBg]  // 单色系，简洁
// 或多色对比
chartColors: [deepBg, accent, midBg, "A0C8D8"]
```

### 5.2 饼图

```javascript
// 标签含百分比，减少对照图例
labels: ["轿车 40%", "SUV 34%", "载货 15%", "其他 11%"]
chartColors: [deepBg, accent, midBg, "A0C8D8"]
```

### 5.3 折线图

```javascript
chartColors: [accent]
lineDataSymbol: "circle"
lineDataSymbolSize: 8
dataLabelPosition: "t"
// Y轴不从0开始时要标注
```

---

## 六、禁忌清单

| ❌ 禁止 | ✅ 正确做法 |
|---------|-----------|
| 连续文本混排 | 独立元素/子卡片 |
| 行级表格颜色 | 单元格级颜色 |
| 纯文字页面 | 至少1个视觉元素 |
| 相同布局连续使用 | 布局轮换 |
| 正文居中 | 正文左对齐 |
| 默认蓝色配色 | 主题色系 |
| 低对比度文字 | 遵循色阶表 |
| 卡片高度不匹配内容 | 按内容量计算高度 |
| 装饰圆与背景同色 | 用accent色或更亮色 |
| 大号数字顶部对齐 | valign:bottom 底部对齐 |
| 时间轴无方向感 | 加粗线+箭头 |
| "持续"作为时间标签 | "长期"更统一 |
