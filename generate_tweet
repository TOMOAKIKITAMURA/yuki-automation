#!/usr/bin/env python3
"""
generate_tweet.py
Anthropic APIを使い、YU KIペルソナの朝/夜モードでツイート本文を1件生成して標準出力する。

必要な環境変数:
  ANTHROPIC_API_KEY

使い方:
  python3 generate_tweet.py --mode morning
  python3 generate_tweet.py --mode evening
"""

import os
import sys
import argparse

import anthropic
from persona import PERSONA, THEMES_MORNING, THEMES_EVENING, COMMON_RULES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], required=True)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("環境変数 ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    theme_block = THEMES_MORNING if args.mode == "morning" else THEMES_EVENING

    prompt = f"{PERSONA}\n\n# 今回のモード\n{theme_block}\n\n# ルール\n{COMMON_RULES}\n\n上記の設定に沿って、ツイート本文を1件だけ生成してください。"

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    print(text)


if __name__ == "__main__":
    main()
