#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
copy_guard.py — history-figure-video 文案风控机检

分级规则（2026-11 起）：
  硬拦(HARD)   : 当下/职场类比、敏感词        -> 直接 FAIL
  归属(ATTR)   : 明君/暴君/千古一帝等定性词   -> 必须附近有出处或"称/认为/后世"等归属词,否则 FAIL
  提示(SOFT)   : 情绪化形容词                 -> 只标记,不拦截,交人工/评审判断
  结构(STRUCT) : 每节 source 非空、总字数区间  -> 不满足 FAIL

用法:
  python3 scripts/copy_guard.py <episode_dir> [--min-chars 280] [--max-chars 420] [--report out.json]

退出码: 0=通过(可能有 SOFT 提示) 1=硬拦/结构/归属不通过
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 硬拦：现代职场/当下社会类比（规范 2.1：禁止现代职场类比、禁止引申当下）
HARD_MODERN = [
    r"职场", r"内卷", r"KPI", r"绩效", r"社畜", r"打工人", r"996", r"老板",
    r"融资", r"甲方", r"乙方",
    r"如今社会", r"现代社会", r"放到今天", r"今天我们", r"当代人", r"现代人",
    r"人生道理", r"人生启示", r"情商", r"逆袭",
]

# 硬拦：敏感词（可按需追加；文件 data/sensitive.txt 每行一个词同样生效）
HARD_SENSITIVE_DEFAULT = [
    "民族分裂", "分裂国家", "疆独", "藏独", "台独",
]

# 软提示：情绪化形容词（不拦，只标记）
SOFT_EMOTION = [
    "悲凉", "悲壮", "可惜", "可叹", "不堪", "伟大", "伟岸", "凄凉", "凄惨",
    "令人扼腕", "令人唏嘘", "让人心痛", "千古遗憾", "何其", "何等",
    "残忍", "冷血", "阴暗", "丑陋", "英明神武", "雄才大略", "气吞山河",
]

# 归属检查：定性评价词（必须说明"谁说的"）
VERDICT_WORDS = [
    "千古一帝", "千古明君", "明君", "圣君", "雄主", "明主", "贤君",
    "暴君", "昏君", "庸主", "独夫", "仁君",
]
ATTRIBUTION_MARKERS = re.compile(r"后世|史家|史书|记载|评价|认为|被誉为|被称为|号为|(?<![堪号自简])称")
ATTRIBUTION_SOURCE = re.compile(r"《[^》]{1,20}》")

# 归属词窗口（前后各 N 字内出现归属标记或书名号即视为有出处）
ATTR_WINDOW = 12

CJK_PUNCT = re.compile(r"[\s，。！？；：、“”‘’（）《》—…·,.!?;:\"'()\[\]-]")


def load_sensitive(ep_dir: Path):
    words = list(HARD_SENSITIVE_DEFAULT)
    p = ep_dir / "sensitive.txt"
    if p.exists():
        words += [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    return words


def sections_of(data):
    secs = data.get("sections") or []
    if not secs and data.get("main_body"):
        # 兼容段岳泽纯文本 JSON：main_body 按行/段切分
        lines = [l.strip() for l in str(data["main_body"]).splitlines() if l.strip()]
        secs = [{"title": f"段落{i+1}", "narration": l, "source": ""} for i, l in enumerate(lines)]
    return secs


def check_text(text, where, sensitive):
    hard, soft, attr = [], [], []
    for pat in HARD_MODERN:
        for m in re.finditer(pat, text):
            hard.append({"where": where, "rule": "现代类比/当下引申", "hit": m.group(0), "context": clip(text, m.start(), m.end())})
    for w in sensitive:
        for m in re.finditer(re.escape(w), text):
            hard.append({"where": where, "rule": "敏感词", "hit": w, "context": clip(text, m.start(), m.end())})
    for w in SOFT_EMOTION:
        for m in re.finditer(re.escape(w), text):
            soft.append({"where": where, "rule": "情绪词(提示)", "hit": w, "context": clip(text, m.start(), m.end())})
    for w in VERDICT_WORDS:
        for m in re.finditer(re.escape(w), text):
            lo, hi = max(0, m.start() - ATTR_WINDOW), min(len(text), m.end() + ATTR_WINDOW)
            ctx = text[lo:hi]
            ok = bool(ATTRIBUTION_MARKERS.search(ctx)) or bool(ATTRIBUTION_SOURCE.search(ctx))
            if not ok:
                attr.append({"where": where, "rule": "定性词缺归属", "hit": w, "context": clip(text, m.start(), m.end())})
    return hard, soft, attr


def clip(text, s, e, pad=12):
    lo, hi = max(0, s - pad), min(len(text), e + pad)
    return ("…" if lo else "") + text[lo:hi] + ("…" if hi < len(text) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--min-chars", type=int, default=280)
    ap.add_argument("--max-chars", type=int, default=420)
    ap.add_argument("--report", default=None)
    ap.add_argument("--strict-emotion", action="store_true", help="把情绪词也当失败(默认只提示)")
    args = ap.parse_args()

    ep = Path(args.episode_dir).expanduser()
    sp = ep / "script.json"
    if not sp.exists():
        print(f"[FAIL] 找不到 {sp}")
        return 1
    data = json.loads(sp.read_text(encoding="utf-8"))
    sensitive = load_sensitive(ep)
    secs = sections_of(data)

    hard, soft, attr, struct = [], [], [], []
    total = 0
    for i, s in enumerate(secs):
        text = str(s.get("narration", "") or s.get("text", ""))
        where = f"sections[{i}]({s.get('title','')})"
        total += len(CJK_PUNCT.sub("", text))
        h, so, a = check_text(text, where, sensitive)
        hard += h; soft += so; attr += a
        src = (s.get("source") or "").strip()
        if not src:
            struct.append({"where": where, "rule": "缺少史料出处(source)", "hit": "", "context": text[:40]})

    # 钩子/结尾也过一遍风控（不进字数）
    for key in ("opening_hook", "hook", "ending_hook", "ending"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            h, so, a = check_text(v, key, sensitive)
            hard += h; soft += so; attr += a

    if not (args.min_chars <= total <= args.max_chars):
        struct.append({"where": "全文", "rule": f"字数越界(需{args.min_chars}~{args.max_chars})", "hit": str(total), "context": ""})

    report = {
        "episode_dir": str(ep),
        "total_chars": total,
        "hard_fail": hard,
        "attribution_fail": attr,
        "struct_fail": struct,
        "soft_warnings": soft,
        "pass": not (hard or attr or struct or (args.strict_emotion and soft)),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"字数: {total} (要求 {args.min_chars}~{args.max_chars})")
    if hard:
        print(f"\n❌ 硬拦 {len(hard)} 处:")
        for x in hard:
            print(f"  - [{x['rule']}] {x['hit']} @ {x['where']}: {x['context']}")
    if attr:
        print(f"\n❌ 定性词缺归属 {len(attr)} 处（需补'谁说的'或出处）:")
        for x in attr:
            print(f"  - {x['hit']} @ {x['where']}: {x['context']}")
    if struct:
        print(f"\n❌ 结构/格式 {len(struct)} 处:")
        for x in struct:
            print(f"  - [{x['rule']}] {x['where']}: {x['context']}")
    if soft:
        print(f"\n⚠️ 情绪词提示 {len(soft)} 处（不拦截，评审判断是否叙事需要）:")
        for x in soft:
            print(f"  - {x['hit']} @ {x['where']}")

    print("\n结论:", "PASS ✅" if report["pass"] else "FAIL ❌（修改后重跑）")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
