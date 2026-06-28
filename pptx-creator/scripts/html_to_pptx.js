#!/usr/bin/env node
/**
 * html_to_pptx.js — Convert HTML slide files to a PPTX presentation.
 *
 * Usage:
 *   node html_to_pptx.js slides.html output.pptx
 *   node html_to_pptx.js slide1.html slide2.html slide3.html output.pptx
 *
 * The HTML is parsed with cheerio. Each <div class="slide"> becomes one slide.
 * Theme colors/fonts are read from CSS custom properties on the .slide element.
 *
 * Dependencies: pptxgenjs, cheerio
 *   npm install -g pptxgenjs cheerio
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const cheerio = require("cheerio");

// ── Helpers ──────────────────────────────────────────────────────────────

function parseColor(val) {
  if (!val) return null;
  // Handle hex
  const hex = val.replace("#", "").trim();
  if (/^[0-9A-Fa-f]{3,8}$/.test(hex)) return hex;
  // Handle rgb()
  const rgb = val.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (rgb) {
    return [rgb[1], rgb[2], rgb[3]].map(n => parseInt(n).toString(16).padStart(2, "0")).join("");
  }
  return null;
}

function parseInches(val) {
  if (!val) return null;
  // px → inches (96dpi)
  const px = val.match(/([\d.]+)px/);
  if (px) return parseFloat(px[1]) / 96;
  // em → inches (assume 16px base)
  const em = val.match(/([\d.]+)em/);
  if (em) return (parseFloat(em[1]) * 16) / 96;
  // bare number → inches
  const bare = val.match(/^([\d.]+)$/);
  if (bare) return parseFloat(bare[1]);
  // pt → inches
  const pt = val.match(/([\d.]+)pt/);
  if (pt) return parseFloat(pt[1]) / 72;
  return null;
}

function parseFontSize(val) {
  if (!val) return null;
  const pt = val.match(/([\d.]+)pt/);
  if (pt) return parseFloat(pt[1]);
  const px = val.match(/([\d.]+)px/);
  if (px) return parseFloat(px[1]) * 0.75;
  const em = val.match(/([\d.]+)em/);
  if (em) return parseFloat(em[1]) * 12;
  return null;
}

function getCSSVar($, el, name) {
  const style = $(el).attr("style") || "";
  const match = style.match(new RegExp(`--${name}\\s*:\\s*([^;]+)`));
  return match ? match[1].trim() : null;
}

// ── Slide type handlers ──────────────────────────────────────────────────

const SLIDE_HANDLERS = {
  "slide-title": renderTitleSlide,
  "slide-section": renderSectionSlide,
  "slide-key-point": renderKeyPointSlide,
  "slide-two-column": renderTwoColumnSlide,
  "slide-three-column": renderThreeColumnSlide,
  "slide-big-number": renderBigNumberSlide,
  "slide-timeline": renderTimelineSlide,
  "slide-closing": renderClosingSlide,
};

function getSlideType($, slide) {
  const classes = (slide.attr("class") || "").split(/\s+/);
  for (const cls of classes) {
    if (SLIDE_HANDLERS[cls]) return cls;
  }
  return null;
}

function getThemeColors($, slide) {
  return {
    darkBg: getCSSVar($, slide, "dark-bg") || "1E2761",
    lightBg: getCSSVar($, slide, "light-bg") || "F5F7FA",
    accent: getCSSVar($, slide, "accent") || "028090",
    darkText: getCSSVar($, slide, "dark-text") || "2C3E50",
    bodyText: getCSSVar($, slide, "body-text") || "333333",
    headerFont: getCSSVar($, slide, "header-font") || "Arial",
    bodyFont: getCSSVar($, slide, "body-font") || "Calibri",
  };
}

// ── Individual slide renderers ───────────────────────────────────────────

function renderTitleSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.darkBg };

  const title = slide.find(".title").text().trim();
  const subtitle = slide.find(".subtitle").text().trim();
  const meta = slide.find(".meta").text().trim();

  if (title) s.addText(title, {
    x: 1, y: 2, w: 11.33, h: 2,
    fontSize: 44, fontFace: theme.headerFont, color: "FFFFFF",
    bold: true, align: "left", valign: "bottom"
  });
  if (subtitle) s.addText(subtitle, {
    x: 1, y: 4, w: 11.33, h: 1,
    fontSize: 20, fontFace: theme.bodyFont, color: "CADCFC",
    align: "left", valign: "top"
  });
  if (meta) s.addText(meta, {
    x: 1, y: 6, w: 11.33, h: 0.5,
    fontSize: 12, fontFace: theme.bodyFont, color: "999999", align: "left"
  });
  return s;
}

function renderSectionSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.darkBg };

  const num = slide.find(".section-number").text().trim();
  const title = slide.find(".section-title").text().trim();
  const desc = slide.find(".section-desc").text().trim();

  if (num) s.addText(num, {
    x: 1, y: 2, w: 2, h: 1,
    fontSize: 60, fontFace: theme.headerFont, color: theme.accent, bold: true
  });
  if (title) s.addText(title, {
    x: 1, y: 3, w: 11.33, h: 1.5,
    fontSize: 36, fontFace: theme.headerFont, color: "FFFFFF", bold: true
  });
  if (desc) s.addText(desc, {
    x: 1, y: 4.5, w: 11.33, h: 1,
    fontSize: 16, fontFace: theme.bodyFont, color: "CADCFC"
  });
  return s;
}

function renderKeyPointSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.lightBg };

  // Accent bar
  s.addShape(pptx.ShapeType.rect, {
    x: 0.5, y: 0.5, w: 0.15, h: 3, fill: { color: theme.accent }
  });

  const headline = slide.find(".headline").text().trim();
  const body = slide.find(".body-text").text().trim();

  if (headline) s.addText(headline, {
    x: 1, y: 0.8, w: 10, h: 1.5,
    fontSize: 36, fontFace: theme.headerFont, color: theme.darkText, bold: true
  });
  if (body) s.addText(body, {
    x: 1, y: 2.5, w: 10, h: 2.5,
    fontSize: 16, fontFace: theme.bodyFont, color: theme.bodyText,
    lineSpacingMultiple: 1.5
  });

  // Visual accent circle
  s.addShape(pptx.ShapeType.ellipse, {
    x: 10.5, y: 4, w: 2, h: 2, fill: { color: theme.accent }
  });
  return s;
}

function renderTwoColumnSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.lightBg };

  const heading = slide.find("h2").first().text().trim();
  const bullets = slide.find(".col-text li").map((_, li) => $(li).text().trim()).get();
  const imgSrc = slide.find(".col-visual img").attr("src");

  if (heading) s.addText(heading, {
    x: 0.5, y: 0.3, w: 6, h: 1,
    fontSize: 28, fontFace: theme.headerFont, color: theme.darkText, bold: true
  });
  if (bullets.length) s.addText(
    bullets.map(b => ({ text: b, options: { bullet: true, fontSize: 14 } })),
    { x: 0.5, y: 1.5, w: 5.5, h: 4.5, color: theme.bodyText, lineSpacingMultiple: 1.8 }
  );
  if (imgSrc) {
    const imgPath = path.resolve(path.dirname(inputFiles[0] || "."), imgSrc);
    if (fs.existsSync(imgPath)) {
      s.addImage({ path: imgPath, x: 7, y: 1.2, w: 5.8, h: 5, sizing: { type: "cover", w: 5.8, h: 5 } });
    }
  }
  return s;
}

function renderThreeColumnSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.lightBg };

  const heading = slide.find("h2").first().text().trim();
  const cards = slide.find(".card").map((_, card) => {
    const title = $(card).find("h3").text().trim();
    const body = $(card).find("p").text().trim();
    return { title, body };
  }).get();

  if (heading) s.addText(heading, {
    x: 0.5, y: 0.3, w: 12, h: 1,
    fontSize: 28, fontFace: theme.headerFont, color: theme.darkText, bold: true
  });

  const cardW = 3.5, gap = 0.5, startX = 0.75;
  cards.forEach((item, i) => {
    const cx = startX + i * (cardW + gap);
    s.addShape(pptx.ShapeType.roundRect, {
      x: cx, y: 1.8, w: cardW, h: 4.5,
      fill: { color: theme.lightBg }, rectRadius: 0.15,
      line: { color: theme.accent, width: 1 }
    });
    s.addShape(pptx.ShapeType.ellipse, {
      x: cx + 1.25, y: 2.2, w: 1, h: 1, fill: { color: theme.accent }
    });
    if (item.title) s.addText(item.title, {
      x: cx + 0.3, y: 3.5, w: cardW - 0.6, h: 0.8,
      fontSize: 18, fontFace: theme.headerFont, color: theme.darkText, bold: true, align: "center"
    });
    if (item.body) s.addText(item.body, {
      x: cx + 0.3, y: 4.3, w: cardW - 0.6, h: 1.5,
      fontSize: 12, fontFace: theme.bodyFont, color: theme.bodyText, align: "center"
    });
  });
  return s;
}

function renderBigNumberSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.lightBg };

  const label = slide.find(".label").text().trim();
  const number = slide.find(".number").text().trim();
  const explanation = slide.find(".explanation").text().trim();

  if (label) s.addText(label, {
    x: 1, y: 1, w: 11, h: 0.8,
    fontSize: 16, fontFace: theme.bodyFont, color: theme.bodyText, align: "left"
  });
  if (number) s.addText(number, {
    x: 1, y: 1.8, w: 11, h: 2.5,
    fontSize: 72, fontFace: theme.headerFont, color: theme.accent, bold: true, align: "left"
  });
  if (explanation) s.addText(explanation, {
    x: 1, y: 4.5, w: 11, h: 1.5,
    fontSize: 16, fontFace: theme.bodyFont, color: theme.bodyText, lineSpacingMultiple: 1.5
  });
  return s;
}

function renderTimelineSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.lightBg };

  const heading = slide.find("h2").first().text().trim();
  const steps = slide.find(".step").map((_, step) => {
    const title = $(step).find("h3").text().trim();
    const desc = $(step).find("p").text().trim();
    return { title, desc };
  }).get();

  if (heading) s.addText(heading, {
    x: 0.5, y: 0.3, w: 12, h: 1,
    fontSize: 28, fontFace: theme.headerFont, color: theme.darkText, bold: true
  });

  if (steps.length) {
    const stepW = 11.33 / steps.length;
    const lineY = 3.5;
    s.addShape(pptx.ShapeType.line, {
      x: 1, y: lineY, w: 11.33, h: 0,
      line: { color: theme.accent, width: 2 }
    });
    steps.forEach((item, i) => {
      const cx = 1 + i * stepW;
      s.addShape(pptx.ShapeType.ellipse, {
        x: cx + stepW / 2 - 0.25, y: lineY - 0.25, w: 0.5, h: 0.5,
        fill: { color: theme.accent }
      });
      if (item.title) s.addText(item.title, {
        x: cx, y: lineY + 0.6, w: stepW, h: 0.6,
        fontSize: 14, fontFace: theme.headerFont, color: theme.darkText, bold: true, align: "center"
      });
      if (item.desc) s.addText(item.desc, {
        x: cx, y: lineY + 1.2, w: stepW, h: 1.5,
        fontSize: 11, fontFace: theme.bodyFont, color: theme.bodyText, align: "center"
      });
    });
  }
  return s;
}

function renderClosingSlide(pptx, $, slide, theme) {
  const s = pptx.addSlide();
  s.background = { color: theme.darkBg };

  const closingText = slide.find("h1").text().trim();
  const subtext = slide.find(".subtext").text().trim();
  const contact = slide.find(".contact").text().trim();

  if (closingText) s.addText(closingText, {
    x: 1, y: 2, w: 11.33, h: 2,
    fontSize: 44, fontFace: theme.headerFont, color: "FFFFFF",
    bold: true, align: "center", valign: "middle"
  });
  if (subtext) s.addText(subtext, {
    x: 1, y: 4, w: 11.33, h: 1,
    fontSize: 18, fontFace: theme.bodyFont, color: "CADCFC", align: "center"
  });
  if (contact) s.addText(contact, {
    x: 1, y: 5.5, w: 11.33, h: 1,
    fontSize: 12, fontFace: theme.bodyFont, color: "999999", align: "center"
  });
  return s;
}

// ── Main ─────────────────────────────────────────────────────────────────

let inputFiles = [];
let outputFile = "output.pptx";

function parseArgs() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node html_to_pptx.js <slide1.html> [slide2.html ...] <output.pptx>");
    process.exit(1);
  }
  outputFile = args[args.length - 1];
  inputFiles = args.slice(0, -1);
}

function main() {
  parseArgs();

  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";

  for (const file of inputFiles) {
    const html = fs.readFileSync(file, "utf-8");
    const $ = cheerio.load(html);
    const slides = $(".slide");

    if (slides.length === 0) {
      // Treat the whole file as one slide
      const wrapper = $("<div>").append($.root().children());
      wrapper.addClass("slide");
      const type = getSlideType($, wrapper) || "slide-key-point";
      const theme = getThemeColors($, wrapper);
      const handler = SLIDE_HANDLERS[type];
      if (handler) handler(pptx, $, wrapper, theme);
      continue;
    }

    slides.each((_, el) => {
      const slide = $(el);
      const type = getSlideType($, slide);
      const theme = getThemeColors($, slide);
      if (!type) {
        console.warn(`Skipping slide with unknown type: ${(slide.attr("class"))}`);
        return;
      }
      const handler = SLIDE_HANDLERS[type];
      if (handler) handler(pptx, $, slide, theme);
    });
  }

  pptx.writeFile({ fileName: outputFile }).then(() => {
    console.log(`Created: ${outputFile}`);
  }).catch(err => {
    console.error("Error writing PPTX:", err);
    process.exit(1);
  });
}

main();
