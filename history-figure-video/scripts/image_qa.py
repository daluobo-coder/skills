#!/usr/bin/env python3
"""
图片质检(VQA) — 用视觉模型检查生成图

用法:
  python3 image_qa.py <图片路径> [<图片路径> ...] [-q "问题"]

依赖 .env 中 OPENCODE_ZEN_API_KEY / OPENCODE_ZEN_BASE_URL
默认问题针对历史人物视频的常见翻车点(文字/畸形/画风/明暗)。
退出码: 0=全部通过, 1=有 FAIL
"""
import os, sys, base64, json, argparse, uuid, requests

BASE = os.getenv("OPENCODE_ZEN_BASE_URL", "").rstrip("/")
KEY = os.getenv("OPENCODE_ZEN_API_KEY", "")
MODEL = os.getenv("VQA_MODEL", "deepseek-v4.1-flash")

DEFAULT_Q = """你是短视频美术质检。逐张检查这张历史题材配图，按下面4项给结论：
1) 文字：画面里有没有真汉字/水印/签名/伪文字？有则 FAIL
2) 人物/器物：有没有畸形手指、多头多手、扭曲人脸、结构崩坏？有则 FAIL
3) 画风：是否廉价塑料感/AI糊感/明显跑题（现代物品、西式场景）？严重则 FAIL
4) 明暗：过暗看不清 or 过曝惨白？严重则 FAIL
输出格式：第一行 PASS 或 FAIL，第二行一句话说明，第三行列出主要问题（没有写"无"）。不要废话。"""


def ask(path, question, max_tokens=700):
    ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
    }
    h = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
         "x-opencode-session": str(uuid.uuid4())}
    r = requests.post(f"{BASE}/chat/completions", headers=h, json=body, timeout=180)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    return (msg.get("content") or msg.get("reasoning_content") or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("-q", "--question", default=DEFAULT_Q)
    args = ap.parse_args()

    if not BASE or not KEY:
        print("❌ 缺少 OPENCODE_ZEN_BASE_URL / OPENCODE_ZEN_API_KEY")
        sys.exit(2)

    bad = 0
    for p in args.images:
        print(f"=== {os.path.basename(p)} ===")
        try:
            out = ask(p, args.question)
        except Exception as e:
            print(f"  ⚠️ 质检失败: {type(e).__name__} {e}")
            bad += 1
            continue
        print(out)
        if out.lstrip().upper().startswith("FAIL"):
            bad += 1
    print(f"\n质检结果: {len(args.images) - bad}/{len(args.images)} PASS")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
