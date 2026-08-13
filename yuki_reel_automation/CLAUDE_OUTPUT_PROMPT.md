# Claude出力ルール：YU KI Reel JSON

Reel企画を作るときは、最終的に下記JSON形式でも出力してください。

- `clips` は必ず7件
- `image` は `assets/01.jpg` 〜 `assets/07.jpg`
- `duration` は原則3.0秒、最後のみ3.5秒程度
- `zoom` は `in` / `out` / `none`
- テロップは短く
- 実在ブランドの未確認情報を断定しない
- 画像自体に文字やロゴを生成しない

JSONを求められた場合は有効なJSONだけを返してください。
