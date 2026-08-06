#!/usr/bin/env python3
"""
post_to_x.py
yukiさんのXアカウントへの自動投稿スクリプト

事前準備:
  pip install tweepy --break-system-packages

必要な環境変数 (X Developer Portalで取得):
  X_API_KEY
  X_API_SECRET
  X_ACCESS_TOKEN
  X_ACCESS_SECRET

使い方:
  # テキストのみ投稿
  python3 post_to_x.py --text "こんにちは！今日のコーデはこちら"

  # 画像付き投稿（1枚〜4枚まで）
  python3 post_to_x.py --text "本日の1枚" --media photo1.jpg photo2.jpg

  # 動画付き投稿
  python3 post_to_x.py --text "今日のvlog" --media video.mp4

  # キャプションファイルから読み込み（自動投稿ジョブ向け）
  python3 post_to_x.py --text-file caption.txt --media photo1.jpg
"""

import os
import sys
import argparse
import logging

try:
    import tweepy
except ImportError:
    print("tweepy がインストールされていません。`pip install tweepy --break-system-packages` を実行してください。", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("post_to_x")

REQUIRED_ENV_VARS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]


def load_credentials():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        log.error("環境変数が不足しています: %s", ", ".join(missing))
        log.error("X Developer Portal (https://developer.x.com) で取得したキーを設定してください。")
        sys.exit(1)
    return {
        "api_key": os.environ["X_API_KEY"],
        "api_secret": os.environ["X_API_SECRET"],
        "access_token": os.environ["X_ACCESS_TOKEN"],
        "access_secret": os.environ["X_ACCESS_SECRET"],
    }


def build_clients(creds):
    # v1.1 API (画像/動画アップロード用。メディアアップロードは今もv1.1のみ対応)
    auth = tweepy.OAuth1UserHandler(
        creds["api_key"], creds["api_secret"],
        creds["access_token"], creds["access_secret"],
    )
    api_v1 = tweepy.API(auth)

    # v2 API (投稿作成用)
    client_v2 = tweepy.Client(
        consumer_key=creds["api_key"],
        consumer_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_secret"],
    )
    return api_v1, client_v2


def upload_media(api_v1, media_paths):
    media_ids = []
    for path in media_paths:
        if not os.path.exists(path):
            log.error("メディアファイルが見つかりません: %s", path)
            sys.exit(1)
        log.info("アップロード中: %s", path)
        media = api_v1.media_upload(filename=path)
        media_ids.append(media.media_id)
    return media_ids


def post_tweet(client_v2, text, media_ids=None, reply_to=None, quote_tweet_id=None):
    kwargs = {"text": text}
    if media_ids:
        kwargs["media_ids"] = media_ids
    if reply_to:
        kwargs["in_reply_to_tweet_id"] = reply_to
    if quote_tweet_id:
        kwargs["quote_tweet_id"] = quote_tweet_id
    response = client_v2.create_tweet(**kwargs)
    tweet_id = response.data.get("id")
    log.info("投稿成功: https://x.com/i/web/status/%s", tweet_id)
    return tweet_id


def main():
    parser = argparse.ArgumentParser(description="Xへ自動投稿する")
    parser.add_argument("--text", help="投稿本文")
    parser.add_argument("--text-file", help="投稿本文が書かれたテキストファイルのパス")
    parser.add_argument("--media", nargs="*", default=[], help="画像/動画ファイルのパス（最大4枚の画像 or 1本の動画）")
    parser.add_argument("--reply-to", help="返信先のツイートID（指定するとリプライとして投稿）")
    parser.add_argument("--quote-tweet-id", help="引用元のツイートID（指定すると引用リツイートとして投稿）")
    args = parser.parse_args()

    if not args.text and not args.text_file:
        parser.error("--text か --text-file のどちらかを指定してください")

    text = args.text
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read().strip()

    creds = load_credentials()
    api_v1, client_v2 = build_clients(creds)

    media_ids = upload_media(api_v1, args.media) if args.media else None
    post_tweet(client_v2, text, media_ids, reply_to=args.reply_to, quote_tweet_id=args.quote_tweet_id)


if __name__ == "__main__":
    main()
