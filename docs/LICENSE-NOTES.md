# ライセンス解説 — ミラー・torrent・再配布は合法か

> 本書は技術者向けの要約です。法的助言ではありません。実際の利用判断は
> 必ず原文（[`metadata/zai-org__GLM-5.3/LICENSE`](../metadata/zai-org__GLM-5.3/LICENSE)）と
> 必要に応じて専門家の確認によってください。

## 1. 結論

| 対象 | ライセンス | 再配布・ミラー・torrent | 商用利用 |
|---|---|---|---|
| `zai-org/GLM-5.3` / `-BF16`（744B 本家） | **GLM-5.3 License**（独自・MIT 様式） | ✅ **可能**（表示保持が条件） | ✅ 原則可能（下記の大口 MaaS 条項に注意） |
| `zai-org/GLM-5.3-Flash` / `-Flash-BF16`（320B） | **MIT** | ✅ 可能（ほぼ無条件） | ✅ 可能 |

したがって、**本リポジトリの内容（目録・LICENSE 全文・メタデータ）の公開や、
重みのミラー作成・torrent 配布はライセンス上問題ありません**。

## 2. GLM-5.3 License の要点

原文冒頭（英語）: *"Permission is hereby granted, free of charge, to any person or entity
obtaining a copy of this software — including the model weights, parameters, configuration
files, inference and training code, and associated documentation (the "Software") — to deal in
the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software; …"*

つまり MIT とほぼ同じ広い許諾で、**重みの再配布が明示的に許諾**されています。

### 条件（3点）

1. **表示の保持** — 上記の著作権表示と本許諾文を、**コピーまたは実質的部分に同梱**すること。
   さらに、適用法令の遵守。
   → ミラーを作る際は `LICENSE` を必ず同梱する（本リポジトリの `tools/mirror_to_hf.py` は
   来歴 README を自動生成します）。
2. **大口「Model as a Service」事業者向けの審査条項** —
   被許可者（および関連会社）が Model-as-a-Service 事業を運営し、**任意の連続12か月の
   合計収入が 100 億米ドル（または等価額）を超える**場合、商用利用の前に
   **Z.AI のセキュリティレビュー**を受ける必要がある。
   なお「Model as a Service」の定義からは、(a) モデル能力が特定機能・ハーネスに
   埋め込まれたエンドユーザー製品、(b) 他者がホストするモデルへの単なる中継、は除外される。
   → **個人・中小事業者・研究用途には実質的に影響しない**条項です。
3. **無保証** — "AS IS"。Z.AI および関連会社は一切の責任を負わない。

質問先（原文記載）: `glmlicense@z.ai`

### MIT（Flash 系）

`GLM-5.3-Flash` と `GLM-5.3-Flash-BF16` は **素の MIT**（追加条項・収益閾値・
用途制限なし）。帰属表示のみが条件です。

## 3. 再配布時のチェックリスト

- [ ] 元の `LICENSE` 全文を同梱した（改変しない）
- [ ] 著作権表示（`Copyright (c) 2026 Z.AI`）を保持した
- [ ] どのリビジョンの再配布かを明記した（本リポジトリの `manifests/REPOS.json` の `revision`）
- [ ] 改変を加えた場合は改変した旨を明記した（無改変ミラーならその旨を明記）
- [ ] 目録の SHA-256 を併せて公開し、検証可能にした（推奨）

## 4. 本リポジトリ自身のライセンス

| 部分 | ライセンス |
|---|---|
| `tools/`（スクリプト）, `docs/`, 本 README などの独自記述 | **MIT**（自由に利用可） |
| `metadata/zai-org__GLM-5.3/*`（上流ファイルの複製） | 元ライセンス（GLM-5.3 License / MIT）に従う |
| `manifests/*`（事実データ＝ファイル名・サイズ・ハッシュ） | 事実の記録であり著作物性は乏しいが、公開は Z.AI の利益に資する |

## 5. 注意

* ライセンスは将来変更される可能性があります。**再配布前に必ず最新の原文を確認**し、
  本リポジトリの `metadata/.../LICENSE`（取得日 2026-10-01 時点）と比較してください。
* API（`z.ai` のサービス）の利用条件は**別文書**です。本リポジトリが扱うのは
  「公開された重みとそのメタデータ」であり、API 利用規約とは無関係です。
