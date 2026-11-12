#!/usr/bin/env python3
"""
AI生图脚本 - 百度 AI Studio Stable-Diffusion-XL
读取 script.json 的 bg_prompt(英文), 逐张生成, 中心裁切为 9:16 竖版, PIL渐变兜底

用法:
  python3 generate_images.py <episode_dir> [--force] [--only N]

硬约束(2026-11 实测):
- 模型名必须是 Stable-Diffusion-XL; ERNIE-Image-Turbo 已下线(404)
- 合法尺寸只有 768x1024 / 1024x768 / 1024x1024, 其他 size 一律 400
- **中文 prompt 会直接 400 Service temporarily unavailable**, 必须写英文
- 请求间隔需 >=8s, 否则 403 访问过于频繁
- 输出统一中心裁切+缩放为 768x1376 (9:16)
"""
import json, os, sys, time, argparse, requests, fcntl
from io import BytesIO
from email.utils import formatdate
from PIL import Image, ImageDraw

# === 硬性防护：禁止DashScope文生图 ===
# TTS_API_KEY 仅用于TTS，严禁用于文生图

_LOCK_FILE = "/tmp/generate_images.lock"
MIN_INTERVAL = 8          # 两次请求最小间隔(秒), 低于此值会被限流
TARGET_SIZE = (768, 1376)  # 最终竖版 9:16
REQUEST_SIZE = "768x1024"  # 接口支持的竖版尺寸(3:4), 再裁成 9:16

BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
BAIDU_API_BASE = os.getenv("BAIDU_API_BASE", "https://aistudio.baidu.com/llm/lmapi/v3")
DEAD_MODELS = {"ernie-image-turbo", "ernie-image"}
_env_model = os.getenv("TEXT_TO_IMAGE_MODEL", "Stable-Diffusion-XL")
IMAGE_MODEL = "Stable-Diffusion-XL" if _env_model.lower() in DEAD_MODELS else _env_model
MAX_RETRIES = 4
_last_call = [0.0]


def acquire_lock():
    lock_fd = open(_LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(f"{os.getpid()}\n")
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        print("❌ 已有其他生图进程在运行，禁止并发调用！请等待当前进程完成。")
        sys.exit(1)


def _headers():
    return {
        "Authorization": f"Bearer {BAIDU_API_KEY}",
        "Content-Type": "application/json",
        "date": formatdate(timeval=time.time(), localtime=False, usegmt=True),
        "X-Client-Platform": "aistudio",
    }


def _throttle():
    gap = time.time() - _last_call[0]
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call[0] = time.time()


def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)


def crop_to_target(img):
    """中心裁切成 9:16 后缩放到 TARGET_SIZE"""
    w, h = img.size
    need = TARGET_SIZE[0] / TARGET_SIZE[1]          # 0.5581
    if w / h > need:                                 # 太宽 → 裁两侧
        nw = int(h * need)
        x = (w - nw) // 2
        img = img.crop((x, 0, x + nw, h))
    else:                                            # 太高 → 裁上下
        nh = int(w / need)
        y = (h - nh) // 2
        img = img.crop((0, y, w, y + nh))
    return img.resize(TARGET_SIZE, Image.LANCZOS)


def generate_with_baidu(prompt, negative_prompt=""):
    if not BAIDU_API_KEY:
        print("  ⚠️ BAIDU_API_KEY 未配置，跳过生图")
        return None

    if has_cjk(prompt):
        print("  ⚠️ bg_prompt 含中文，接口会返回 400！请改成英文提示词")

    size = REQUEST_SIZE
    for attempt in range(MAX_RETRIES):
        _throttle()
        payload = {
            "model": IMAGE_MODEL,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "url",
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        try:
            r = requests.post(f"{BAIDU_API_BASE}/images/generations",
                              headers=_headers(), json=payload, timeout=240)
            if r.status_code == 200:
                data = r.json()
                img = Image.open(BytesIO(requests.get(data["data"][0]["url"], timeout=120).content))
                return crop_to_target(img.convert("RGB"))

            body = r.text[:160].replace("\n", " ")
            if "size is invalid" in body and size != "1024x1024":
                print(f"  ↪ {size} 不被接受，改用 1024x1024")
                size = "1024x1024"
                continue
            wait = 10 * (attempt + 1)
            print(f"  ⚠️ 生图失败 {r.status_code} (第{attempt+1}/{MAX_RETRIES}次): {body} → {wait}s 后重试")
            time.sleep(wait)
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"  ⚠️ 生图异常 (第{attempt+1}/{MAX_RETRIES}次): {type(e).__name__} {e} → {wait}s 后重试")
            time.sleep(wait)

    print("  ❌ 生图最终失败，使用渐变兜底")
    return None


def generate_gradient():
    """PIL渐变兜底图（古朴暖褐调）"""
    width, height = TARGET_SIZE
    img = Image.new('RGB', TARGET_SIZE)
    draw = ImageDraw.Draw(img)
    top, bottom = (58, 42, 32), (108, 84, 60)
    for y in range(height):
        f = y / height
        draw.line([(0, y), (width, y)],
                  fill=tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3)))
    return img


def process_episode(ep_dir, force=False, only=None):
    script_path = os.path.join(ep_dir, "script.json")
    images_dir = os.path.join(ep_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    if not os.path.exists(script_path):
        print(f"❌ 找不到 script.json: {script_path}")
        return False

    with open(script_path, encoding='utf-8') as f:
        script = json.load(f)

    sections = script.get("sections", [])
    if not sections:
        print("❌ script.json 无 sections")
        return False

    targets = [(i, s) for i, s in enumerate(sections) if only is None or i == only]
    print(f"=== AI生图: {os.path.basename(ep_dir)} ({len(targets)}/{len(sections)}张, {IMAGE_MODEL}) ===")

    ok = fail = 0
    for i, sec in targets:
        out_path = os.path.join(images_dir, f"ai_{i:02d}.png")

        if not force and os.path.exists(out_path) and os.path.getsize(out_path) > 50000:
            print(f"  [跳过] ai_{i:02d}.png 已存在 ({os.path.getsize(out_path)/1024:.0f}KB)")
            ok += 1
            continue

        prompt = (sec.get("bg_prompt") or "").strip()
        print(f"  生成 ai_{i:02d} (type={sec.get('type','story')}): {prompt[:70]}...")

        if not prompt:
            print("  ⚠️ 无 bg_prompt，使用渐变兜底")
            generate_gradient().save(out_path)
            fail += 1
            continue

        img = generate_with_baidu(prompt, negative_prompt="text, watermark, chinese characters, low quality, blurry, deformed")
        if img is None:
            img = generate_gradient()
            fail += 1
            img.save(out_path, "PNG")
            print(f"  ⚠️ ai_{i:02d}.png 渐变兜底 ({os.path.getsize(out_path)/1024:.0f}KB)")
        else:
            ok += 1
            img.save(out_path, "PNG")
            print(f"  ✅ ai_{i:02d}.png ({os.path.getsize(out_path)/1024:.0f}KB {TARGET_SIZE[0]}x{TARGET_SIZE[1]})")

    total = ok + fail
    print(f"\n生图完成: {ok}/{total} 成功, {fail} 张渐变兜底")
    if fail:
        print("⚠️ 有图片使用渐变兜底，检查 bg_prompt 是否为英文/是否被限流后重跑")
    return fail == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='AI生图(百度 Stable-Diffusion-XL)')
    ap.add_argument('episode_dir')
    ap.add_argument('--force', action='store_true', help='忽略已有图片，全部重新生成')
    ap.add_argument('--only', type=int, default=None, help='只重新生成指定序号(0-based)')
    args = ap.parse_args()

    if not os.path.isdir(args.episode_dir):
        print(f"❌ 目录不存在: {args.episode_dir}")
        sys.exit(1)

    lock = acquire_lock()
    try:
        process_episode(args.episode_dir, force=args.force, only=args.only)
    finally:
        lock.close()
