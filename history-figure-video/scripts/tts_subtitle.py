#!/usr/bin/env python3
"""
百炼TTS + 字幕生成脚本 (轻量版)
调用 tts_common 公共模块完成 TTS + SRT 生成

用法:
  python3 tts_subtitle.py <episode_dir> [--voice Vincent] [--pause-period 0.5] [--pause-comma 0.2]

episode_dir 示例: ~/workspace/data/ai_drama/2026/07/历史人物_上官婉儿_序列篇/E01_刀下留人
"""

import os, json, sys, argparse

# 将脚本所在目录加入 path,确保能 import tts_common
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_common import run_tts_pipeline

parser = argparse.ArgumentParser(description='百炼TTS + 字幕生成')
parser.add_argument('episode_dir', help='集目录路径')
parser.add_argument('--voice', default='Vincent', help='百炼TTS音色 (默认: Vincent)')
parser.add_argument('--pause-period', type=float, default=0.5, help='句号/问号/感叹号后停顿秒数 (默认: 0.5)')
parser.add_argument('--pause-comma', type=float, default=0.2, help='逗号后停顿秒数 (默认: 0.2)')
parser.add_argument('--pause-semicolon', type=float, default=0.4, help='分号后停顿秒数 (默认: 0.4)')
args = parser.parse_args()

E01_DIR = args.episode_dir
AUDIO_DIR = os.path.join(E01_DIR, "audio")
SUB_DIR = os.path.join(E01_DIR, "sub")

# 加载API Key
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

# 执行TTS流水线
run_tts_pipeline(
    script=script,
    audio_dir=AUDIO_DIR,
    sub_dir=SUB_DIR,
    voice=args.voice,
    api_key=DASHSCOPE_API_KEY,
    pause_period=args.pause_period,
    pause_comma=args.pause_comma,
    pause_semicolon=args.pause_semicolon
)
