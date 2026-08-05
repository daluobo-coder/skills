#!/usr/bin/env python3
"""
历史人物视频合成脚本 v5
- 不再内嵌TTS,读取步骤6(tts_subtitle.py)已生成的音频和SRT
- 预缩放帧图 + -framerate 1 -loop 1 编码优化
- 音效叠加(开场锣/悬念鼓/反转提示等)
- 拼接→字幕烧录→BGM→收尾(步骤7+8一体化)

用法:
  python3 compose_video.py <episode_dir> [--voice Vincent] [--font-size 14] [--bgm /path/to/bgm.mp3]

episode_dir 示例: ~/workspace/data/ai_drama/2026/07/历史人物_上官婉儿_序列篇/E01_刀下留人
"""

import os, re, json, time, subprocess, shutil, sys, argparse

E01_DIR = None  # set by args

# === 参数 ===
parser = argparse.ArgumentParser(description='历史人物视频合成')
parser.add_argument('episode_dir', help='集目录路径')
parser.add_argument('--voice', default='Vincent', help='百炼TTS音色 (默认: Vincent)')
parser.add_argument('--font-size', type=int, default=14, help='字幕字号 (默认: 14)')
parser.add_argument('--bgm', default='~/workspace/data/ai_drama/bgm/gaoshan_liushui_guzheng.mp3', help='BGM路径')
parser.add_argument('--fps', type=int, default=5, help='视频帧率 (默认: 5)')
parser.add_argument('--crf', type=int, default=30, help='视频CRF (默认: 30)')
parser.add_argument('--sfx-dir', default='~/workspace/data/ai_drama/sfx', help='音效素材目录')
args = parser.parse_args()

E01_DIR = args.episode_dir
FONT_SIZE = args.font_size
BGM_PATH = os.path.expanduser(args.bgm)
FPS = args.fps
CRF = args.crf
SFX_DIR = os.path.expanduser(args.sfx_dir)

AUDIO_DIR = os.path.join(E01_DIR, "audio")
SUB_DIR = os.path.join(E01_DIR, "sub")
FRAME_DIR = os.path.join(E01_DIR, "images")
FRAME_SCALED_DIR = os.path.join(E01_DIR, "images_scaled")
MEDIA_DIR = os.path.expanduser("~/.openclaw/media/qqbot")

os.makedirs(FRAME_SCALED_DIR, exist_ok=True)

# 加载文案
script_path = os.path.join(E01_DIR, "script.json")
if not os.path.exists(script_path):
    print(f"❌ 找不到文案: {script_path}")
    sys.exit(1)

with open(script_path) as f:
    script = json.load(f)

sections = script["sections"]

# 检查步骤6输出是否存在
merged_srt = os.path.join(SUB_DIR, "merged.srt")
if not os.path.exists(merged_srt):
    print(f"❌ 找不到字幕文件(请先运行步骤6 tts_subtitle.py): {merged_srt}")
    sys.exit(1)

# 检查每段音频是否存在
missing_audio = []
for i in range(len(sections)):
    audio_path = os.path.join(AUDIO_DIR, f"seg_{i:02d}_merged.wav")
    if not os.path.exists(audio_path):
        missing_audio.append(f"seg_{i:02d}_merged.wav")
if missing_audio:
    print(f"❌ 缺少音频文件(请先运行步骤6 tts_subtitle.py): {', '.join(missing_audio)}")
    sys.exit(1)


# === 工具函数 ===

def get_duration(path):
    """获取音频/视频时长"""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 0


def scale_frame(input_path, output_path, width=768, height=1376):
    """缩放帧图到目标尺寸"""
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
        output_path
    ], capture_output=True)


def find_frame(idx):
    """查找段idx对应的帧图"""
    for name in [f"frame_{idx:02d}.png", f"screenshot_{idx:02d}.png", f"bg_{idx:02d}.png"]:
        p = os.path.join(FRAME_DIR, name)
        if os.path.exists(p):
            return p
    return None


def get_sfx_for_section_type(section_type):
    """根据小节类型返回音效文件名"""
    sfx_map = {
        "cover": "gong.wav",              # 开场锣
        "hook": "suspense_drum.wav",       # 悬念鼓
        "reversal": "reverse_swoosh.wav",  # 反转提示
        "ending": "gu_zheng.wav",          # 古筝抒情
        "tragedy": "scare_stinger.wav",    # 惨烈遭遇
        "transition": "transition_whoosh.wav",  # 转场
        "chapter": "chapter_transition.wav",    # 章节转场
        "desolate": "wind.wav",            # 荒凉氛围
    }
    return sfx_map.get(section_type, None)


# === Step 1: 预缩放帧图 ===
print("=== Step 1: 预缩放帧图 ===")
for i in range(len(sections)):
    src = find_frame(i)
    if not src:
        print(f"  段{i}: 无帧图, 跳过")
        continue
    dst = os.path.join(FRAME_SCALED_DIR, f"frame_{i:02d}.png")
    if not os.path.exists(dst):
        scale_frame(src, dst)
        print(f"  段{i}: 缩放完成")
    else:
        print(f"  段{i}: 已存在")


# === Step 2: 合成节视频(含音效叠加) ===
print("\n=== Step 2: 合成节视频 ===")
seg_videos = []
for i in range(len(sections)):
    frame = os.path.join(FRAME_SCALED_DIR, f"frame_{i:02d}.png")
    audio = os.path.join(AUDIO_DIR, f"seg_{i:02d}_merged.wav")
    out = os.path.join(E01_DIR, f"seg_{i:02d}_raw.mp4")

    if not os.path.exists(frame) or not os.path.exists(audio):
        print(f"  seg_{i}: 缺文件, 跳过")
        continue

    dur = get_duration(audio)
    print(f"  合成 seg_{i} ({dur:.1f}s)...")

    # 检查是否需要叠加音效
    section_type = sections[i].get("type", "")
    sfx_file = get_sfx_for_section_type(section_type)
    sfx_path = os.path.join(SFX_DIR, sfx_file) if sfx_file else None

    if sfx_path and os.path.exists(sfx_path):
        # 叠加音效: 音效比旁白低6dB, 延迟0.3秒
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", "1", "-loop", "1", "-i", frame,
            "-i", audio,
            "-i", sfx_path,
            "-filter_complex",
            f"[1:a]aresample=24000[main];[2:a]aresample=24000,volume=0.5,adelay=300|300[sfx];[main][sfx]amix=inputs=2:duration=first:dropout_transition=2,atrim=0:{dur}[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-crf", str(CRF),
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-vsync", "cfr",
            "-t", str(dur), out
        ], capture_output=True, timeout=300)
    else:
        # 无音效,直接合成
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", "1", "-loop", "1", "-i", frame,
            "-i", audio,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-crf", str(CRF),
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-vsync", "cfr",
            "-t", str(dur), out
        ], capture_output=True, timeout=300)

    actual = get_duration(out)
    print(f"  seg_{i}: {actual:.2f}s")
    seg_videos.append(out)


# === Step 3: 拼接 ===
print("\n=== Step 3: 拼接 ===")
concat_path = os.path.join(E01_DIR, "concat.txt")
with open(concat_path, "w") as f:
    for sv in sorted(seg_videos):
        f.write(f"file '{sv}'\n")

concat_raw = os.path.join(E01_DIR, "final_raw.mp4")
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_path,"-c:v","libx264","-preset","ultrafast","-crf",str(CRF),"-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-r",str(FPS),concat_raw], capture_output=True, timeout=600)
total_dur = get_duration(concat_raw)
print(f"  拼接: {total_dur:.2f}s")


# === Step 4: 烧录字幕 ===
print("\n=== Step 4: 烧录字幕 ===")
final_sub = os.path.join(E01_DIR, "final_sub.mp4")
subprocess.run([
    "ffmpeg", "-y", "-i", concat_raw,
    "-vf", f"subtitles='{merged_srt}':force_style='FontName=Noto Sans CJK SC,FontSize={FONT_SIZE},PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=1,Shadow=1,Shadow=1,Bold=1,Alignment=2,MarginV=60'",
    "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
    "-crf", str(CRF),
    "-c:a", "copy", "-r", str(FPS), final_sub
], capture_output=True, timeout=600)
print(f"  字幕版: {get_duration(final_sub):.2f}s")


# === Step 5: BGM ===
print("\n=== Step 5: BGM ===")
final_path = os.path.join(E01_DIR, "final.mp4")
if os.path.exists(BGM_PATH):
    r = subprocess.run([
        "ffmpeg", "-y", "-i", final_sub,
        "-stream_loop", "-1", "-i", BGM_PATH,
        "-filter_complex", f"[1:a]volume=0.25,atrim=0:{total_dur}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", final_path
    ], capture_output=True)
    if r.returncode != 0:
        print(f"  BGM混合失败,使用无BGM版本")
        shutil.copy2(final_sub, final_path)
else:
    shutil.copy2(final_sub, final_path)

final_dur = get_duration(final_path)
final_size = os.path.getsize(final_path)
print(f"  final.mp4: {final_dur:.2f}s, {final_size/1024/1024:.1f}MB")

# === Step 6: 收尾 ===
print("\n=== Step 6: 收尾 ===")

# 复制到media目录
figure_name = script.get("figure_name", "unknown")
ep = script.get("ep", 1)
media_name = f"历史人物_{figure_name}_E{ep:02d}.mp4"
media_path = os.path.join(MEDIA_DIR, media_name)
os.makedirs(MEDIA_DIR, exist_ok=True)
shutil.copy2(final_path, media_path)
print(f"  已复制到: {media_path}")

# 生成 publish.txt
publish_path = os.path.join(E01_DIR, "publish.txt")
if not os.path.exists(publish_path):
    # 中文数字映射
    cn_nums = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
    cn_ep = cn_nums.get(ep, str(ep))
    title_text = script.get("title", "")
    publish_title = f"{figure_name}({cn_ep})：{title_text}"

    # 简介从opening_hook和ending_hook提取
    opening_hook = script.get("opening_hook", "")
    ending_hook = script.get("ending_hook", "")
    # 用opening_hook作为简介基础（兼容旧数据,去掉频道名前缀）
    desc = opening_hook
    if desc.startswith("平章说,") or desc.startswith("平章说，"):
        desc = desc.split("，", 1)[-1] if "，" in desc else desc.split(",", 1)[-1]
    if not desc.strip():
        desc = title_text

    # 话题标签
    dynasty = script.get("dynasty", "")
    tags = [figure_name]
    if dynasty:
        tags.append(dynasty)
    # 从sections内容推断额外标签
    section_texts = " ".join(s.get("narration", "") for s in script.get("sections", []))
    extra_tag_map = {
        "历史真相": ["真相", "正史", "野史"],
        "封神演义": ["封神", "演义"],
        "考古": ["考古", "出土", "发掘"],
        "甲骨文": ["甲骨", "卜辞"],
        "女将军": ["女将", "出征", "挂帅"],
        "姓氏起源": ["赐姓", "姓氏", "始祖"],
        "正史vs野史": ["正史", "野史"],
        "竹书纪年": ["竹书纪年"],
        "牧野之战": ["牧野", "倒戈"],
        "殷墟": ["殷墟"],
        "军事史": ["伏击", "围歼", "征伐"],
        "人文社科": ["人文", "社科"],
        "知识创作": ["知识"],
    }
    for tag, keywords in extra_tag_map.items():
        if any(kw in section_texts for kw in keywords) and tag not in tags:
            tags.append(tag)
            if len(tags) >= 5:
                break
    # 确保至少有知识赛道标签
    if "人文社科" not in tags and len(tags) < 5:
        tags.append("人文社科")

    tags_line = " ".join(f"#{t}" for t in tags)

    with open(publish_path, "w", encoding="utf-8") as f:
        f.write(f"{publish_title}\n{desc}\n{tags_line}\n")
    print(f"  已生成: {publish_path}")
    print(f"    标题: {publish_title}")
    print(f"    简介: {desc}")
    print(f"    话题: {tags_line}")
else:
    print(f"  publish.txt 已存在,跳过: {publish_path}")

# 更新progress
progress_path = os.path.join(E01_DIR, "progress.json")
progress = {}
if os.path.exists(progress_path):
    with open(progress_path) as f:
        progress = json.load(f)
progress.update({
    "current_step": 8,
    "steps_completed": [1,2,3,4,"4b",5,6,7,8],
    "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.gmtime(time.time()+8*3600)),
    "last_error": None,
    "status": "done"
})
with open(progress_path, "w") as f:
    json.dump(progress, f, ensure_ascii=False, indent=2)

print(f"\n✅ 合成完成!")
