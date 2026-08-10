#!/usr/bin/env python3
"""
generate_tweet.py
Anthropic APIを使い、YU KIペルソナでツイート本文を1件生成して標準出力する。

- 朝モード: 考察系（ブランド論・トレンド分析）。固定テーマから選ぶ。
- 夜モード: 曜日ごとの柔らかい日記トーン（Instagramと世界観を統一）。

必要な環境変数:
  ANTHROPIC_API_KEY

使い方:
  python3 generate_tweet.py --mode morning
  python3 generate_tweet.py --mode evening
"""

import os
import sys
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
from persona import PERSONA, THEMES_MORNING, THEMES_EVENING_BY_WEEKDAY, COMMON_RULES, EVENING_RULES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], required=True)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("環境変数 ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    if args.mode == "morning":
        prompt = (
            f"{PERSONA}\n\n"
            f"# 今回のモード\n{THEMES_MORNING}\n\n"
            f"# ルール\n{COMMON_RULES}\n\n"
            f"上記の設定に沿って、ツイート本文を1件だけ生成してください。"
        )
    else:
        weekday = datetime.now(ZoneInfo("Asia/Tokyo")).weekday()  # 0=月曜 ... 6=日曜
        mood = THEMES_EVENING_BY_WEEKDAY[weekday]
        print(f"今日の夜のテーマ: {mood}", file=sys.stderr)
        prompt = (
            f"{PERSONA}\n\n"
            f"# 今回のモード（夜・曜日テーマ）\n{mood}\n\n"
            f"# ルール\n{EVENING_RULES}\n\n"
            f"上記の設定に沿って、ツイート本文を1件だけ生成してください。"
        )

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
