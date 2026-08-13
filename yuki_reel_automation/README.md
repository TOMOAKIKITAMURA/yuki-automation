# YU KI Reel Automation

7枚の縦画像 + Claudeが出力したJSONから、Instagram Reel用のMP4を自動生成するスターターです。

## できること
- 7枚の画像を自動で9:16 / 1080x1920に整形
- 各画像を指定秒数で配置
- ゆっくりしたズーム
- 日本語テロップを自動挿入
- BGMがあれば自動でミックス
- MP4を書き出し
- GitHub Actionsで自動実行

## 最短手順
1. `assets/01.jpg` 〜 `assets/07.jpg` に画像を置く
2. ClaudeのJSONを `reel_config.json` に保存
3. ローカル:
   `pip install -r requirements.txt`
   `python render_reel.py --config reel_config.json --output yuki_reel.mp4`
4. GitHub Actionsではpush後にArtifactからMP4を取得

画像生成自体はこのスターターには含めていません。
