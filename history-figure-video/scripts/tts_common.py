#!/usr/bin/env python3
"""
TTS公共模块
- 默认引擎 edge-tts (Microsoft Edge 在线语音, 免费), 音色 zh-CN-YunjianNeural
- 备选引擎 qwen (百炼 qwen3-tts-flash, 音色 Vincent, 需 TTS_API_KEY)
- 按标点拆分单句, 逐句合成
- 句间停顿(句号0.5s, 逗号0.2s, 分号0.4s)
- 从实际音频时长反推字幕时间轴
- TTS失败自动重试(最多3次)

被 tts_subtitle.py 和 compose_video.py 共同引用
"""

import os, re, json, time, subprocess, sys, glob, asyncio
import requests

TTS_MODEL = "qwen3-tts-flash"
EDGE_DEFAULT_VOICE = "zh-CN-YunjianNeural"
EDGE_VOICES = {
    "zh-CN-YunjianNeural": "男声·沉稳叙事(默认,适合历史解说)",
    "zh-CN-YunyangNeural": "男声·新闻播报",
    "zh-CN-YunxiNeural": "男声·年轻清亮",
    "zh-CN-YunxiaNeural": "男声·少年",
    "zh-CN-XiaoxiaoNeural": "女声·温和",
    "zh-CN-XiaoyiNeural": "女声·活泼",
}
VOICE_FINGERPRINT = "voice_fingerprint.json"  # 记录缓存所属音色, 换音色时自动失效

# === 工具函数 ===

def split_by_punctuation(text):
    """按标点拆分为单句"""
    sentences = re.split(r'(?<=[。！？；，!?;,])', text)
    result = []
    for s in sentences:
        s = s.strip()
        if s:
            result.append(s)
    return result


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


def pause_after(text, pause_period=0.5, pause_comma=0.2, pause_semicolon=0.4):
    """根据句末标点决定停顿时长"""
    if text.endswith(('。', '！', '？', '!', '?')):
        return pause_period
    elif text.endswith(('；', ';')):
        return pause_semicolon
    elif text.endswith(('，', ',')):
        return pause_comma
    return 0.1


def gen_silence(duration, path):
    """生成指定时长的静音wav"""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration), "-c:a", "pcm_s16le", path
    ], capture_output=True)


def check_voice_cache(audio_dir, voice, engine="qwen"):
    """
    音色指纹检查: 确保缓存音频属于当前音色

    - audio_dir/voice_fingerprint.json 记录上次生成音频的音色+模型
    - 与当前 voice 一致 → 返回 True, 正常复用缓存
    - 不一致/缺失 → 清理旧 seg/silence/merged/concat 缓存, 写入新指纹, 返回 False
    """
    fp_path = os.path.join(audio_dir, VOICE_FINGERPRINT)
    current = {"engine": engine, "voice": voice, "model": TTS_MODEL if engine == "qwen" else "edge-tts"}

    cached = None
    if os.path.exists(fp_path):
        try:
            with open(fp_path) as f:
                cached = json.load(f)
        except Exception:
            cached = None

    if cached == current:
        return True  # 音色一致, 缓存可复用

    # 音色不一致或指纹缺失: 清理旧缓存, 避免旧音色文件被误用
    removed = 0
    for pattern in ["seg_*_s*.wav", "silence_*.wav", "seg_*_merged.wav", "concat_*.txt"]:
        for p in glob.glob(os.path.join(audio_dir, pattern)):
            try:
                os.remove(p)
                removed += 1
            except OSError:
                pass

    with open(fp_path, "w") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)

    old_voice = cached.get("voice") if cached else "无"
    print(f"  🔄 音色/引擎指纹变更 ({old_voice} → {voice}), 清理 {removed} 个旧音频缓存")
    return False


def qwen_tts(text, output_path, voice="Vincent", api_key=None, max_retries=3):
    """百炼TTS生成音频,失败自动重试"""
    # 去掉末尾标点再发送TTS,避免TTS遇标点提前收尾导致吞字
    tts_text = text.rstrip('。！？，；,.!?;')
    if not tts_text:
        tts_text = text
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers={
                    "Authorization": f"bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen3-tts-flash",
                    "input": {
                        "text": tts_text,
                        "voice": voice,
                        "language_type": "Chinese"
                    }
                },
                timeout=60
            )
            result = response.json()
            audio_url = None

            if "output" in result:
                audio_info = result["output"].get("audio", {})
                audio_url = audio_info.get("url")

            if audio_url:
                r = requests.get(audio_url, timeout=30)
                if r.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(r.content)
                    return True

            print(f"  TTS失败(尝试{attempt+1}/{max_retries}): {json.dumps(result, ensure_ascii=False)[:200]}")
        except Exception as e:
            print(f"  TTS异常(尝试{attempt+1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            time.sleep(1)

    return False


def edge_tts_synth(text, output_path, voice=EDGE_DEFAULT_VOICE, rate="+0%", max_retries=3):
    """Edge-TTS 在线合成(免费), 失败自动重试; 输出统一转 24k 单声道 wav"""
    try:
        import edge_tts
    except ImportError:
        print("  ❌ 未安装 edge-tts, 请执行: pip install edge-tts")
        return False

    mp3_path = output_path + ".mp3"
    for attempt in range(max_retries):
        try:
            async def _run():
                comm = edge_tts.Communicate(text, voice, rate=rate)
                await comm.save(mp3_path)
            asyncio.run(_run())

            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                r = subprocess.run([
                    "ffmpeg", "-y", "-i", mp3_path,
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", output_path
                ], capture_output=True, text=True)
                try:
                    os.remove(mp3_path)
                except OSError:
                    pass
                if os.path.exists(output_path) and os.path.getsize(output_path) > 4000:
                    return True
                print(f"  EdgeTTS转码失败(尝试{attempt+1}/{max_retries}): {(r.stderr or '')[-160:]}")
            else:
                print(f"  EdgeTTS无输出(尝试{attempt+1}/{max_retries})")
        except Exception as e:
            print(f"  EdgeTTS异常(尝试{attempt+1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            time.sleep(1.2)

    return False


def format_srt_time(seconds):
    """标准SRT时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def run_tts_pipeline(script, audio_dir, sub_dir, voice=None, api_key=None,
                     pause_period=0.5, pause_comma=0.2, pause_semicolon=0.4,
                     engine="edge", rate="+0%"):
    """
    完整TTS流水线: 逐句合成 → 带停顿拼接 → 生成SRT

    参数:
        script: script.json 内容(dict, 含 sections)
        audio_dir: 音频输出目录
        sub_dir: 字幕输出目录
        voice: 音色(edge: zh-CN-*; qwen: Vincent 等)
        api_key: DashScope API Key(仅 qwen 引擎需要)
        engine: edge | qwen
        rate: edge 引擎语速, 如 "+8%"/"-5%"。历史解说建议 +5%~+10%
        pause_period/comma/semicolon: 句间停顿时长

    返回:
        all_segments: [{section_idx, sentence_idx, text, audio_path, duration}, ...]
        timeline_segments: [{section, text, start, end}, ...]
        merged_srt: SRT文件路径
    """
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(sub_dir, exist_ok=True)

    if engine not in ("edge", "qwen"):
        raise ValueError(f"未知 TTS 引擎: {engine}")
    if not voice:
        voice = EDGE_DEFAULT_VOICE if engine == "edge" else "Vincent"

    # 音色/引擎指纹检查: 变更时自动清理旧缓存, 一致则复用缓存
    check_voice_cache(audio_dir, voice, engine)
    print(f"TTS引擎: {engine} / 音色: {voice}" + (f" / 语速: {rate}" if engine == "edge" else ""))

    sections = script["sections"]

    # Step 1: 逐句TTS合成
    print("=== TTS逐句合成 ===")
    all_segments = []

    for si, section in enumerate(sections):
        narration = section["narration"]
        sentences = split_by_punctuation(narration)
        print(f"\n段{si} [{section['title']}]: {len(sentences)}句")

        for ssi, sent in enumerate(sentences):
            audio_name = f"seg_{si:02d}_s{ssi:02d}.wav"
            audio_path = os.path.join(audio_dir, audio_name)

            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
                dur = get_duration(audio_path)
                all_segments.append({
                    "section_idx": si, "sentence_idx": ssi,
                    "text": sent, "audio_path": audio_path, "duration": dur
                })
                continue

            print(f"  TTS {audio_name}: {sent[:30]}...")
            if engine == "edge":
                ok = edge_tts_synth(sent, audio_path, voice=voice, rate=rate)
            else:
                ok = qwen_tts(sent, audio_path, voice=voice, api_key=api_key)
            if ok:
                dur = get_duration(audio_path)
                print(f"    OK: {dur:.2f}s")
                all_segments.append({
                    "section_idx": si, "sentence_idx": ssi,
                    "text": sent, "audio_path": audio_path, "duration": dur
                })
            else:
                print(f"    FAILED after retries!")
            time.sleep(0.3)

    # Step 2: 带停顿拼接 + 记录时间轴
    print("\n=== 生成带停顿音频 + 记录时间轴 ===")
    timeline_segments = []

    for si in range(len(sections)):
        section_segs = [s for s in all_segments if s["section_idx"] == si]
        if not section_segs:
            # 无旁白段(如封面): 生成3秒静音,确保seg_offsets计算正确
            silence_path = os.path.join(audio_dir, f"seg_{si:02d}_merged.wav")
            if not os.path.exists(silence_path):
                gen_silence(3.0, silence_path)
                print(f"  段{si}: 无旁白, 已生成3秒静音")
            else:
                print(f"  段{si}: 无旁白, 静音已存在")
            continue

        concat_list = os.path.join(audio_dir, f"concat_{si:02d}.txt")
        current_time = 0.0

        with open(concat_list, "w") as f:
            for seg in section_segs:
                timeline_segments.append({
                    "section": si,
                    "text": seg["text"],
                    "start": current_time,
                    "end": current_time + seg["duration"]
                })

                f.write(f"file '{os.path.abspath(seg['audio_path'])}'\n")
                current_time += seg["duration"]

                pause = pause_after(seg["text"], pause_period, pause_comma, pause_semicolon)
                if pause > 0:
                    silence_path = os.path.join(audio_dir, f"silence_{si:02d}_{seg['sentence_idx']:02d}_{pause:.1f}.wav")
                    if not os.path.exists(silence_path):
                        gen_silence(pause, silence_path)
                    f.write(f"file '{os.path.abspath(silence_path)}'\n")
                    current_time += pause

        merged_path = os.path.join(audio_dir, f"seg_{si:02d}_merged.wav")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", merged_path
        ], capture_output=True)

        actual_dur = get_duration(merged_path)
        print(f"  段{si}: {len(section_segs)}句, {actual_dur:.2f}s (含停顿)")

    # Step 3: 生成全局SRT
    # 每句字幕持续显示到下一句开始(停顿期间保持显示),避免字幕闪烁
    print("\n=== 生成SRT ===")
    seg_offsets = []
    offset = 0.0
    for si in range(len(sections)):
        seg_offsets.append(offset)
        merged_path = os.path.join(audio_dir, f"seg_{si:02d}_merged.wav")
        offset += get_duration(merged_path)

    srt_entries = []
    for seg in timeline_segments:
        si = seg["section"]
        srt_entries.append({
            "text": seg["text"],
            "start": seg["start"] + seg_offsets[si],
            "end": seg["end"] + seg_offsets[si]
        })

    # 填充停顿间隙: 每句end延伸到下一句start, 每段最后一句延伸到段末
    # 用 timeline_segments 的 section_idx 分组
    for si in range(len(sections)):
        # 该段在srt_entries中的索引范围
        seg_indices = [j for j, seg in enumerate(timeline_segments) if seg["section"] == si]

        # 段内: 每句end延伸到下一句start
        for k in range(len(seg_indices) - 1):
            i = seg_indices[k]
            next_i = seg_indices[k+1]
            if srt_entries[i]["end"] < srt_entries[next_i]["start"]:
                srt_entries[i]["end"] = srt_entries[next_i]["start"]

        # 段内最后一句: 延伸到该段音频末尾
        if seg_indices:
            last = seg_indices[-1]
            merged_path = os.path.join(audio_dir, f"seg_{si:02d}_merged.wav")
            seg_end = seg_offsets[si] + get_duration(merged_path)
            if srt_entries[last]["end"] < seg_end:
                srt_entries[last]["end"] = seg_end

    merged_srt = os.path.join(sub_dir, "merged.srt")
    with open(merged_srt, "w") as f:
        for idx, entry in enumerate(srt_entries):
            f.write(f"{idx+1}\n{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}\n{entry['text']}\n\n")

    print(f"  merged.srt: {len(srt_entries)}条")
    print(f"\n✅ TTS+字幕生成完成!")

    return all_segments, timeline_segments, merged_srt
