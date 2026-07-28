#!/usr/bin/env python3
"""
HTML截图脚本
- Playwright渲染768x1376截图
- 根据style-guide.md规范生成封面/钩子/故事/结尾页HTML
- 背景图base64内嵌
- 遮罩透明度低(0.3-0.4),靠text-shadow保证文字可读,不压暗背景

用法:
  python3 screenshot.py <episode_dir>

episode_dir 示例: ~/workspace/data/ai_drama/2026/07/历史人物_上官婉儿_序列篇/E01_刀下留人
"""

import os, json, sys, base64, subprocess

E01_DIR = sys.argv[1]
FRAME_DIR = os.path.join(E01_DIR, "images")
HTML_DIR = os.path.join(E01_DIR, "html_frames")

os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

# 加载文案
script_path = os.path.join(E01_DIR, "script.json")
if not os.path.exists(script_path):
    print(f"❌ 找不到文案: {script_path}")
    sys.exit(1)

with open(script_path) as f:
    script = json.load(f)

sections = script["sections"]
figure_name = script.get("figure_name", "")
dynasty = script.get("dynasty", "")

# 兜底: script.json可能缺少figure_name/dynasty,从series_info.json读取
if not figure_name or not dynasty:
    series_info_path = os.path.join(os.path.dirname(E01_DIR), "series_info.json")
    if os.path.exists(series_info_path):
        with open(series_info_path) as f:
            series_info = json.load(f)
        if not figure_name:
            figure_name = series_info.get("figure_name", "")
        if not dynasty:
            dynasty = series_info.get("dynasty", "")
        print(f"  ⚠️ script.json缺少figure_name/dynasty,已从series_info.json补充: figure_name={figure_name}, dynasty={dynasty}")
    else:
        print(f"  ❌ script.json缺少figure_name/dynasty,且series_info.json不存在!封面页将显示不完整")

# 颜色规范(来自style-guide.md)
MAIN_BG = "#1a0e0a"
GOLD = "#d4a847"
DARK_RED = "#8b0000"
WHITE = "#ffffff"


def img_to_base64(path):
    """将图片转为base64 data URI"""
    if not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext.lstrip("."), "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"


def find_bg_image(idx):
    """查找段idx对应的AI生图"""
    for name in [f"ai_{idx:02d}.png", f"bg_{idx:02d}.png", f"image_{idx:02d}.png"]:
        p = os.path.join(FRAME_DIR, name)
        if os.path.exists(p):
            return p
    return None


def generate_cover_html(figure_name, dynasty, bg_path=None):
    """封面页: 垂直居中三行 — 系列名/人物名/朝代"""
    bg_style = ""
    if bg_path:
        bg_uri = img_to_base64(bg_path)
        bg_style = f"background-image: url('{bg_uri}'); background-size: cover; background-position: center;"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:768px; height:1376px; background:{MAIN_BG}; {bg_style} display:flex; flex-direction:column; justify-content:center; align-items:center; font-family:'Noto Sans CJK SC',sans-serif; }}
.overlay {{ position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.55); }}
.content {{ position:relative; z-index:1; text-align:center; }}
.series {{ color:{DARK_RED}; font-size:52px; font-weight:bold; text-shadow:2px 2px 6px rgba(0,0,0,0.9); margin-bottom:30px; }}
.name {{ color:{GOLD}; font-size:88px; font-weight:bold; text-shadow:2px 2px 8px rgba(0,0,0,0.9); margin-bottom:20px; }}
.dynasty {{ color:{WHITE}; font-size:36px; text-shadow:1px 1px 4px rgba(0,0,0,0.8); }}
</style></head><body>
<div class="overlay"></div>
<div class="content">
  <div class="series">历史人物</div>
  <div class="name">{figure_name}</div>
  <div class="dynasty">{dynasty}</div>
</div>
</body></html>"""


def generate_hook_html(bg_path=None):
    """钩子页: 纯背景图,不叠加任何文字。旁白通过TTS声音+底部字幕传达"""
    bg_style = ""
    if bg_path:
        bg_uri = img_to_base64(bg_path)
        bg_style = f"background-image: url('{bg_uri}'); background-size: cover; background-position: center;"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:768px; height:1376px; background:{MAIN_BG}; {bg_style} display:flex; justify-content:center; align-items:center; font-family:'Noto Sans CJK SC',sans-serif; }}
.overlay {{ position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.15); }}
</style></head><body>
<div class="overlay"></div>
</body></html>"""


def generate_story_html(title, bg_path=None):
    """故事页: 左上角章节标题 + 红色短横线,不叠加旁白文字"""
    bg_style = ""
    if bg_path:
        bg_uri = img_to_base64(bg_path)
        bg_style = f"background-image: url('{bg_uri}'); background-size: cover; background-position: center;"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:768px; height:1376px; background:{MAIN_BG}; {bg_style} display:flex; flex-direction:column; font-family:'Noto Sans CJK SC',sans-serif; }}
.overlay {{ position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.15); }}
.header {{ position:relative; z-index:1; padding:60px 50px 20px; }}
.title {{ color:{GOLD}; font-size:56px; font-weight:bold; text-shadow:2px 2px 6px rgba(0,0,0,0.9); }}
.divider {{ width:60px; height:4px; background:{DARK_RED}; margin-top:15px; }}
</style></head><body>
<div class="overlay"></div>
<div class="header">
  <div class="title">{title}</div>
  <div class="divider"></div>
</div>
</body></html>"""


def generate_ending_html(slogan="读史明事理，平章说", bg_path=None):
    """结尾页: 居中金句"""
    bg_style = ""
    if bg_path:
        bg_uri = img_to_base64(bg_path)
        bg_style = f"background-image: url('{bg_uri}'); background-size: cover; background-position: center;"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:768px; height:1376px; background:{MAIN_BG}; {bg_style} display:flex; justify-content:center; align-items:center; font-family:'Noto Sans CJK SC',sans-serif; }}
.overlay {{ position:absolute; top:0; left:0; width:100%; height:100%; background:transparent; }}
.slogan {{ position:relative; z-index:1; color:{GOLD}; font-size:52px; font-weight:bold; text-align:center; text-shadow:2px 2px 6px rgba(0,0,0,0.9); }}
</style></head><body>
<div class="overlay"></div>
<div class="slogan">{slogan}</div>
</body></html>"""


def render_screenshot(html_path, output_path):
    """用Playwright渲染截图"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 768, "height": 1376})
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.screenshot(path=output_path, full_page=False)
            browser.close()
        return True
    except ImportError:
        # Playwright不可用,尝试命令行
        r = subprocess.run([
            "npx", "playwright", "screenshot",
            "--viewport-size=768,1376",
            f"file://{os.path.abspath(html_path)}", output_path
        ], capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception as e:
        print(f"  截图失败: {e}")
        return False


# === 主流程 ===
print("=== HTML截图生成 ===")

for i, section in enumerate(sections):
    section_type = section.get("type", "story")
    title = section.get("title", "")
    bg_path = find_bg_image(i)

    html_path = os.path.join(HTML_DIR, f"frame_{i:02d}.html")
    output_path = os.path.join(FRAME_DIR, f"frame_{i:02d}.png")

    # 已存在则跳过
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"  段{i}: 已存在,跳过")
        continue

    # 生成HTML
    if section_type == "cover":
        html_content = generate_cover_html(figure_name, dynasty, bg_path)
    elif section_type == "hook":
        html_content = generate_hook_html(bg_path)
    elif section_type == "ending":
        html_content = generate_ending_html(bg_path=bg_path)
    else:
        html_content = generate_story_html(title, bg_path)

    with open(html_path, "w") as f:
        f.write(html_content)

    # 渲染截图
    ok = render_screenshot(html_path, output_path)
    if ok:
        print(f"  段{i} [{section_type}]: 截图完成")
    else:
        print(f"  段{i} [{section_type}]: 截图失败,需手动处理")

print(f"\n✅ HTML截图完成!")
