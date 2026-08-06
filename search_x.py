#!/usr/bin/env python3
"""
search_x.py
ファッション/ブランディング関連の最近のツイートを検索し、返信候補をJSONで出力する。

必要な環境変数:
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET

使い方:
  python3 search_x.py --query "#ファッション OR #ブランディング -is:retweet lang:ja" --max-results 15
"""

import os
import sys
import json
import argparse
import logging

import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("search_x")

REQUIRED_ENV_VARS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]


def load_client():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        log.error("環境変数が不足しています: %s", ", ".join(missing))
        sys.exit(1)
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )


def main():
    parser = argparse.ArgumentParser(description="Xの最近のツイートを検索する")
    parser.add_argument("--query", required=True, help="検索クエリ（X APIのクエリ構文）")
    parser.add_argument("--max-results", type=int, default=15, help="取得件数（10〜100）")
    args = parser.parse_args()

    client = load_client()

    try:
        resp = client.search_recent_tweets(
            query=args.query,
            max_results=max(10, min(args.max_results, 100)),
            tweet_fields=["author_id", "created_at", "public_metrics", "lang"],
            expansions=["author_id"],
            user_fields=["username", "name", "public_metrics"],
        )
    except Exception as e:
        log.error("検索に失敗しました: %s", e)
        sys.exit(1)

    if not resp.data:
        print(json.dumps([], ensure_ascii=False))
        return

    users = {u.id: u for u in (resp.includes.get("users", []) if resp.includes else [])}

    results = []
    for tweet in resp.data:
        user = users.get(tweet.author_id)
        results.append({
            "tweet_id": tweet.id,
            "text": tweet.text,
            "created_at": str(tweet.created_at),
            "lang": tweet.lang,
            "like_count": tweet.public_metrics.get("like_count") if tweet.public_metrics else None,
            "author_username": user.username if user else None,
            "author_name": user.name if user else None,
            "author_followers": user.public_metrics.get("followers_count") if user and user.public_metrics else None,
            "url": f"https://x.com/{user.username}/status/{tweet.id}" if user else f"https://x.com/i/web/status/{tweet.id}",
        })

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
