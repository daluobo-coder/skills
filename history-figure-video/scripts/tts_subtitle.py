#!/usr/bin/env python3
"""
TTS + 字幕生成脚本 (轻量版)
默认引擎: edge-tts (免费); 备选: 百炼 qwen3-tts-flash

用法:
  python3 tts_subtitle.py <episode_dir> [--engine edge|qwen] [--voice zh-CN-YunjianNeural]
                                  [--rate +8%] [--pause-period 0.5] [--pause-comma 0.2]
  python3 tts_subtitle.py --list-voices

episode_dir 示例: ~/workspace/data/ai_drama/2026/07/历史人物_上官婉儿_序列篇/E01_刀下留人
"""

import os, json, sys, argparse

# 将脚本所在目录加入 path,确保能 import tts_common
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_common import run_tts_pipeline, EDGE_DEFAULT_VOICE, EDGE_VOICES

parser = argparse.ArgumentParser(description='TTS + 字幕生成 (默认 edge-tts)')
parser.add_argument('episode_dir', nargs='?', help='集目录路径')
parser.add_argument('--engine', default='edge', choices=['edge', 'qwen'], help='TTS引擎 (默认: edge)')
parser.add_argument('--voice', default=None, help=f'音色 (edge默认 {EDGE_DEFAULT_VOICE}; qwen默认 Vincent)')
parser.add_argument('--rate', default='+8%', help='edge语速, 如 +8% / -5% (默认: +8%%, 历史解说偏快一点)')
parser.add_argument('--pause-period', type=float, default=0.5, help='句号/问号/感叹号后停顿秒数 (默认: 0.5)')
parser.add_argument('--pause-comma', type=float, default=0.2, help='逗号后停顿秒数 (默认: 0.2)')
parser.add_argument('--pause-semicolon', type=float, default=0.4, help='分号后停顿秒数 (默认: 0.4)')
parser.add_argument('--list-voices', action='store_true', help='列出可用 edge 音色')
args = parser.parse_args()

if args.list_voices:
    print("edge-tts 常用中文音色:")
    for k, v in EDGE_VOICES.items():
        print(f"  {k:<24} {v}")
    sys.exit(0)

if not args.episode_dir:
    parser.error("需要 episode_dir 参数")

E01_DIR = args.episode_dir
AUDIO_DIR = os.path.join(E01_DIR, "audio")
SUB_DIR = os.path.join(E01_DIR, "sub")

# 加载API Key (仅 qwen 引擎需要)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.expanduser("~"), ".openclaw/.env"))
DASHSCOPE_API_KEY = os.environ.get("TTS_API_KEY", "")

# 加载文案
script_path = os.path.join(E01_DIR, "script.json")
if not os.path.exists(script_path):
    print(f"❌ 找不到文案: {script_path}")
    sys.exit(1)

with open(script_path) as f:
    script = json.load(f)

voice = args.voice or (EDGE_DEFAULT_VOICE if args.engine == "edge" else "Vincent")

# 执行TTS流水线
run_tts_pipeline(
    script=script,
    audio_dir=AUDIO_DIR,
    sub_dir=SUB_DIR,
    voice=voice,
    api_key=DASHSCOPE_API_KEY,
    pause_period=args.pause_period,
    pause_comma=args.pause_comma,
    pause_semicolon=args.pause_semicolon,
    engine=args.engine,
    rate=args.rate
)
