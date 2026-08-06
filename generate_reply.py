#!/usr/bin/env python3
"""
generate_reply.py
search_x.py の検索結果(JSON)を読み込み、YU KIペルソナとして返信すべきツイートを最大3件選び、
それぞれの返信文を生成してJSONで出力する。

必要な環境変数:
  ANTHROPIC_API_KEY

使い方:
  python3 search_x.py --query "..." > candidates.json
  python3 generate_reply.py --candidates candidates.json
"""

import os
import sys
import json
import argparse

import anthropic
from persona import PERSONA

SELECTION_RULES = """
# 返信するツイートを選ぶ基準（最大3件まで）

- ファッション・ブランド・アパレル業界に関する、具体的で建設的な内容であること
- 政治・宗教・炎上中の話題・誹謗中傷・センシティブな内容は絶対に避ける
- スパムっぽいアカウントや、明らかに機械的な投稿は避ける
- YU KIの専門性(ブランド作りの視点)が本当に価値を追加できる内容であること
- 該当するものが1件もなければ、無理に選ばず空リストを返してよい

# 返信文のルール

- そのツイート内容を踏まえた、共感と気づきのある返信を1件作成する
- 全角60〜90文字程度
- 絵文字は0〜1個まで
- ただの「いいですね」ではなく、ブランド視点での気づきや問いかけを加える
- 上から目線にならないこと
"""

OUTPUT_FORMAT = """
# 出力形式

以下のJSON形式のみを出力してください。説明文やコードブロックの記号(```)は一切つけないこと。

[
  {"tweet_id": "対象のツイートID", "reply_text": "返信本文"},
  ...
]

該当するツイートがなければ空配列 [] を出力してください。
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="search_x.py の出力(JSONファイルパス)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("環境変数 ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    with open(args.candidates, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    if not candidates:
        print("[]")
        return

    prompt = (
        f"{PERSONA}\n\n{SELECTION_RULES}\n\n{OUTPUT_FORMAT}\n\n"
        f"# 検索結果(候補ツイート一覧)\n{json.dumps(candidates, ensure_ascii=False, indent=2)}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        print("Claudeの出力がJSONとして解釈できませんでした:", file=sys.stderr)
        print(text, file=sys.stderr)
        sys.exit(1)

    print(json.dumps(parsed[:3], ensure_ascii=False))


if __name__ == "__main__":
    main()
