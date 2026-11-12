#!/usr/bin/env python3
"""
AI生图脚本 — 三引擎
  默认 wan   (阿里百炼 万相2.5 文生图, 品质最好, 中文prompt友好, 约¥0.2/张)
  备选 flux  (Pollinations FLUX, 免费无key, 但503/限流频繁, 45s/张)
  备选 baidu (百度 Stable-Diffusion-XL, 最快, 易出假印章/糊细节)

读取 script.json 的 bg_prompt(英文), 逐张生成, 后处理为 768x1376 (9:16)

用法:
  python3 generate_images.py <episode_dir> [--engine flux|baidu] [--force] [--only N]

实测要点(2026-11):
- bg_prompt 必须英文; 百度接口吃中文直接 400
- 百度: ERNIE-Image-Turbo 已下线(404) → 用 Stable-Diffusion-XL; 尺寸只认 768x1024/1024x768/1024x1024
- 百度出图常带假签名/假印章 + 细节糊 → 默认走 flux
- flux 免费额度: 每 IP 45s 一张, 超出返回 402 FREE_LIMIT
"""
import json, os, sys, time, argparse, random, urllib.parse, requests, fcntl
from io import BytesIO
from email.utils import formatdate
from PIL import Image, ImageDraw

# === 硬性防护：禁止DashScope文生图 ===
# TTS_API_KEY 仅用于TTS(qwen3-tts-flash)，严禁用于文生图

_LOCK_FILE = "/tmp/generate_images.lock"
TARGET_SIZE = (768, 1376)      # 最终 9:16
FLUX_MIN_INTERVAL = 45         # pollinations 免费额度
BAIDU_MIN_INTERVAL = 8

DASHSCOPE_KEY = os.getenv("TTS_API_KEY", "")
WAN_MODEL = os.getenv("WAN_MODEL", "wan2.5-t2i-preview")
WAN_NEG = "文字,汉字,印章,落款,签名,水印,模糊,低清,畸形手指,多余肢体,现代物品,塑料感"

BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
BAIDU_API_BASE = os.getenv("BAIDU_API_BASE", "https://aistudio.baidu.com/llm/lmapi/v3")
DEAD_MODELS = {"ernie-image-turbo", "ernie-image"}
_env_model = os.getenv("TEXT_TO_IMAGE_MODEL", "Stable-Diffusion-XL")
BAIDU_MODEL = "Stable-Diffusion-XL" if _env_model.lower() in DEAD_MODELS else _env_model

DEFAULT_NEG = "text, watermark, signature, seal, chinese characters, blurry, low quality, deformed hands, extra fingers, modern clothing"


def acquire_lock():
    fd = open(_LOCK_FILE, 'w')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(f"{os.getpid()}\n"); fd.flush()
        return fd
    except (IOError, OSError):
        print("❌ 已有其他生图进程在运行，禁止并发调用！")
        sys.exit(1)


class Throttle:
    def __init__(self, interval):
        self.interval = interval
        self.last = 0.0

    def wait(self):
        gap = time.time() - self.last
        if gap < self.interval:
            time.sleep(self.interval - gap)
        self.last = time.time()


def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)


def fit_target(img):
    """中心裁切成 9:16 并缩放到 TARGET_SIZE"""
    w, h = img.size
    need = TARGET_SIZE[0] / TARGET_SIZE[1]
    if w / h > need:
        nw = int(h * need); x = (w - nw) // 2
        img = img.crop((x, 0, x + nw, h))
    else:
        nh = int(w / need); y = (h - nh) // 2
        img = img.crop((0, y, w, y + nh))
    return img.resize(TARGET_SIZE, Image.LANCZOS)



# ---------- wan (阿里百炼 万相2.5) ----------
def gen_wan(prompt, negative_prompt=WAN_NEG, retries=1):
    if not DASHSCOPE_KEY:
        print("  ⚠️ TTS_API_KEY 未配置，无法用 wan 引擎")
        return None
    H = {"Authorization": f"Bearer {DASHSCOPE_KEY}", "Content-Type": "application/json",
         "X-DashScope-Async": "enable"}
    body = {"model": WAN_MODEL,
            "input": {"prompt": prompt, "negative_prompt": negative_prompt},
            "parameters": {"size": "768*1344", "n": 1, "prompt_extend": True}}
    for attempt in range(retries):
        try:
            r = requests.post("https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                              headers=H, json=body, timeout=60)
            if r.status_code != 200:
                print(f"  ⚠️ wan 提交失败 {r.status_code}: {r.text[:140]}")
                time.sleep(8 * (attempt + 1)); continue
            tid = r.json()["output"]["task_id"]
            for _ in range(40):
                time.sleep(4)
                d = requests.get(f"https://dashscope.aliyuncs.com/api/v1/tasks/{tid}",
                                 headers={"Authorization": f"Bearer {DASHSCOPE_KEY}"}, timeout=30).json()
                st = d["output"].get("task_status")
                if st == "SUCCEEDED":
                    url = d["output"]["results"][0]["url"]
                    img = Image.open(BytesIO(requests.get(url, timeout=120).content))
                    return fit_target(img.convert("RGB"))
                if st in ("FAILED", "CANCELED"):
                    print(f"  ⚠️ wan 任务失败: {json.dumps(d, ensure_ascii=False)[:200]}")
                    break
        except Exception as e:
            print(f"  ⚠️ wan 异常 (第{attempt+1}/{retries}次): {type(e).__name__} {e}")
        time.sleep(8 * (attempt + 1))
    return None


# ---------- flux (pollinations) ----------
_flux_throttle = Throttle(FLUX_MIN_INTERVAL)


def gen_flux(prompt, seed=None, retries=8):
    seed = seed if seed is not None else random.randint(1, 10 ** 6)
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width={TARGET_SIZE[0]}&height={TARGET_SIZE[1]}&model=flux&nologo=true&seed={seed}")
    for attempt in range(retries):
        _flux_throttle.wait()
        try:
            r = requests.get(url, timeout=240)
            if r.status_code == 200 and len(r.content) > 20000:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                # pollinations 免费额度会在右下角打 "pollinations.ai" 水印 → 先裁掉底部7%
                w, h = img.size
                img = img.crop((0, 0, w, int(h * 0.93)))
                return fit_target(img)
            body = r.text[:140].replace("\n", " ")
            print(f"  ⚠️ flux {r.status_code} (第{attempt+1}/{retries}次): {body}")
            time.sleep(min(30 * (attempt + 1), 120))
        except Exception as e:
            print(f"  ⚠️ flux 异常 (第{attempt+1}/{retries}次): {type(e).__name__} {e}")
            time.sleep(15 * (attempt + 1))
    return None


# ---------- baidu (Stable-Diffusion-XL) ----------
_baidu_throttle = Throttle(BAIDU_MIN_INTERVAL)


def _baidu_headers():
    return {
        "Authorization": f"Bearer {BAIDU_API_KEY}",
        "Content-Type": "application/json",
        "date": formatdate(timeval=time.time(), localtime=False, usegmt=True),
        "X-Client-Platform": "aistudio",
    }


def gen_baidu(prompt, negative_prompt=DEFAULT_NEG, retries=4):
    if not BAIDU_API_KEY:
        print("  ⚠️ BAIDU_API_KEY 未配置")
        return None
    if has_cjk(prompt):
        print("  ⚠️ bg_prompt 含中文，百度接口会 400！请改英文")

    size = "768x1024"
    for attempt in range(retries):
        _baidu_throttle.wait()
        payload = {"model": BAIDU_MODEL, "prompt": prompt, "n": 1,
                   "size": size, "response_format": "url"}
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        try:
            r = requests.post(f"{BAIDU_API_BASE}/images/generations",
                              headers=_baidu_headers(), json=payload, timeout=240)
            if r.status_code == 200:
                img = Image.open(BytesIO(requests.get(r.json()["data"][0]["url"], timeout=120).content))
                return fit_target(img.convert("RGB"))
            body = r.text[:160].replace("\n", " ")
            if "size is invalid" in body and size != "1024x1024":
                print(f"  ↪ {size} 不被接受，改用 1024x1024")
                size = "1024x1024"
                continue
            print(f"  ⚠️ baidu {r.status_code} (第{attempt+1}/{retries}次): {body}")
            time.sleep(10 * (attempt + 1))
        except Exception as e:
            print(f"  ⚠️ baidu 异常 (第{attempt+1}/{retries}次): {type(e).__name__} {e}")
            time.sleep(10 * (attempt + 1))
    return None


def generate_gradient():
    img = Image.new('RGB', TARGET_SIZE)
    draw = ImageDraw.Draw(img)
    top, bottom = (58, 42, 32), (108, 84, 60)
    for y in range(TARGET_SIZE[1]):
        f = y / TARGET_SIZE[1]
        draw.line([(0, y), (TARGET_SIZE[0], y)],
                  fill=tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3)))
    return img


def process_episode(ep_dir, engine="flux", force=False, only=None):
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
    print(f"=== AI生图: {os.path.basename(ep_dir)} ({len(targets)}/{len(sections)}张, engine={engine}) ===")

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

        engine_fallback = False
        if engine == "wan":
            img = gen_wan(prompt)
            if img is None:
                print("  ↪ wan 失败，切 flux 兜底")
                img = gen_flux(prompt); engine_fallback = True
            if img is None:
                print("  ↪ flux 也失败，切百度兜底")
                img = gen_baidu(prompt)
        elif engine == "flux":
            img = gen_flux(prompt)
            if img is None and BAIDU_API_KEY:
                print("  ↪ flux 失败，切百度兜底")
                img = gen_baidu(prompt); engine_fallback = True
        else:
            img = gen_baidu(prompt)

        if img is None:
            img = generate_gradient(); fail += 1
            img.save(out_path, "PNG")
            print(f"  ⚠️ ai_{i:02d}.png 渐变兜底 ({os.path.getsize(out_path)/1024:.0f}KB)")
        else:
            ok += 1
            img.save(out_path, "PNG")
            tag = "(百度兜底)" if engine_fallback else ""
            print(f"  ✅ ai_{i:02d}.png{tag} ({os.path.getsize(out_path)/1024:.0f}KB 768x1376)")

    print(f"\n生图完成: {ok}/{ok+fail} 成功, {fail} 张渐变兜底")
    if fail:
        print("⚠️ 有图片使用渐变兜底，检查英文 prompt / 限流后重跑")
    return fail == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='AI生图(默认wan, 备选flux/baidu)')
    ap.add_argument('episode_dir')
    ap.add_argument('--engine', default='wan', choices=['wan', 'flux', 'baidu'])
    ap.add_argument('--force', action='store_true', help='忽略已有图片全部重生成')
    ap.add_argument('--only', type=int, default=None, help='只生成指定序号(0-based)')
    args = ap.parse_args()

    if not os.path.isdir(args.episode_dir):
        print(f"❌ 目录不存在: {args.episode_dir}")
        sys.exit(1)

    lock = acquire_lock()
    try:
        process_episode(args.episode_dir, engine=args.engine, force=args.force, only=args.only)
    finally:
        lock.close()
