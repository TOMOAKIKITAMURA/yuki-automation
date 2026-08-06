#!/usr/bin/env python3
"""
generate_ig_caption.py
Anthropic APIを使い、YU KIペルソナでInstagramキャプションを1件生成して標準出力する。

必要な環境変数:
  ANTHROPIC_API_KEY

使い方:
  python3 generate_ig_caption.py
"""

import os
import sys

import anthropic
from persona import PERSONA
from ig_persona import IG_THEMES, IG_CAPTION_RULES


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("環境変数 ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    prompt = (
        f"{PERSONA}\n\n# テーマ\n{IG_THEMES}\n\n# ルール\n{IG_CAPTION_RULES}\n\n"
        f"上記の設定に沿って、Instagramのキャプションを1件だけ生成してください。"
    )

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    print(message.content[0].text.strip())


if __name__ == "__main__":
    main()
