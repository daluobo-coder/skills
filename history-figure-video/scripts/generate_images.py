#!/usr/bin/env python3
"""
AI生图脚本 - 百度 ERNIE-Image-Turbo
读取script.json的bg_prompt，逐张生成AI图片，PIL渐变兜底。
输出: images/ai_{NN}.png

用法: python3 generate_images.py <episode_dir>
"""
import json, os, sys, time, requests, fcntl
from io import BytesIO
from PIL import Image, ImageDraw

# === 硬性防护：禁止DashScope文生图 ===
# TTS_API_KEY(原DASHSCOPE_API_KEY)仅用于TTS(qwen3-tts-flash)，严禁用于文生图
# .env中已无DASHSCOPE_API_KEY，subagent无法获取该key调用文生图API
# 如发现subagent自行编写DashScope文生图脚本，应立即拒绝

# === 串行锁：禁止并发调用文生图 ===
_LOCK_FILE = "/tmp/generate_images.lock"

def acquire_lock():
    """获取文件锁，确保同一时间只有一个生图进程在运行"""
    lock_fd = open(_LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(f"{os.getpid()}\n")
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        print("❌ 已有其他生图进程在运行，禁止并发调用！请等待当前进程完成。")
        sys.exit(1)

# === 配置 ===
BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
BAIDU_API_BASE = os.getenv("BAIDU_API_BASE", "https://aistudio.baidu.com/llm/lmapi/v3")
IMAGE_MODEL = os.getenv("TEXT_TO_IMAGE_MODEL", "ERNIE-Image-Turbo")
# ⚠️ 生图服务只允许百度ERNIE-Image-Turbo，禁止使用DashScope/wanx-v1/阿里百炼文生图
TARGET_SIZE = (768, 1376)  # 竖版9:16
MAX_RETRIES = 3
RETRY_WAIT = 10  # 秒


def generate_with_baidu(prompt, negative_prompt=""):
    """调用百度ERNIE-Image生成图片，返回PIL Image或None"""
    if not BAIDU_API_KEY:
        print("  ⚠️ BAIDU_API_KEY未配置，跳过生图")
        return None

    headers = {
        "Authorization": f"Bearer {BAIDU_API_KEY}",
        "Content-Type": "application/json",
        "X-Client-Platform": "aistudio",
    }
    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "response_format": "url",
        "size": "768x1376",  # 竖版
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt

    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(
                f"{BAIDU_API_BASE}/images/generations",
                headers=headers,
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()

            if "data" not in data or not data["data"]:
                print(f"  ⚠️ 返回空数据: {json.dumps(data, ensure_ascii=False)[:200]}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_WAIT * (attempt + 1))
                    continue
                return None

            img_url = data["data"][0]["url"]
            img_resp = requests.get(img_url, timeout=60)
            img = Image.open(BytesIO(img_resp.content))
            # 确保尺寸正确
            if img.size != TARGET_SIZE:
                img = img.resize(TARGET_SIZE, Image.LANCZOS)
            return img

        except Exception as e:
            print(f"  ⚠️ 生图失败(重试{attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_WAIT * (attempt + 1))
            else:
                print(f"  ❌ 生图最终失败，使用渐变兜底")
                return None


def generate_gradient():
    """PIL渐变兜底图（深色古风色调）"""
    width, height = TARGET_SIZE
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(26 + (212 - 26) * (y / height) * 0.3)
        g = int(14 + (168 - 14) * (y / height) * 0.2)
        b = int(10 + (71 - 10) * (y / height) * 0.15)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def process_episode(ep_dir):
    """处理单集：读取script.json，逐张生成AI图片"""
    script_path = os.path.join(ep_dir, "script.json")
    images_dir = os.path.join(ep_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    if not os.path.exists(script_path):
        print(f"❌ 找不到script.json: {script_path}")
        return False

    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)

    sections = script.get("sections", [])
    if not sections:
        print("❌ script.json无sections")
        return False

    print(f"=== AI生图: {os.path.basename(ep_dir)} ({len(sections)}张) ===")

    success_count = 0
    fail_count = 0

    for i, sec in enumerate(sections):
        out_path = os.path.join(images_dir, f"ai_{i:02d}.png")

        # 跳过已存在且大小正常的图片（>50KB视为有效AI生图）
        if os.path.exists(out_path) and os.path.getsize(out_path) > 50000:
            print(f"  [跳过] ai_{i:02d}.png 已存在 ({os.path.getsize(out_path)/1024:.0f}KB)")
            success_count += 1
            continue

        prompt = sec.get("bg_prompt", "")
        sec_type = sec.get("type", "story")
        print(f"  生成 ai_{i:02d} (type={sec_type}): {prompt[:60]}...")

        if not prompt:
            print(f"  ⚠️ 无bg_prompt，使用渐变兜底")
            img = generate_gradient()
            img.save(out_path)
            fail_count += 1
            continue

        # 调用百度API生图
        img = generate_with_baidu(prompt, negative_prompt="text, watermark, low quality, blurry")

        if img is None:
            # 渐变兜底
            img = generate_gradient()
            img.save(out_path)
            fail_count += 1
            print(f"  ⚠️ ai_{i:02d}.png 渐变兜底")
        else:
            img.save(out_path, "PNG")
            file_size = os.path.getsize(out_path)
            success_count += 1
            print(f"  ✅ ai_{i:02d}.png ({file_size/1024:.0f}KB)")

        # 限速：每张间隔1秒
        time.sleep(1)

    total = success_count + fail_count
    print(f"\n生图完成: {success_count}/{total} 成功, {fail_count} 渐变兜底")

    if fail_count > 0:
        print(f"⚠️ {fail_count}张图使用了渐变兜底，建议检查后重新生成")

    return fail_count == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 generate_images.py <episode_dir>")
        sys.exit(1)

    ep_dir = sys.argv[1]
    if not os.path.isdir(ep_dir):
        print(f"❌ 目录不存在: {ep_dir}")
        sys.exit(1)

    # 获取串行锁，禁止并发
    lock = acquire_lock()

    try:
        ok = process_episode(ep_dir)
    finally:
        # 释放锁
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        try:
            os.unlink(_LOCK_FILE)
        except:
            pass

    sys.exit(0 if ok else 1)
