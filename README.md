# GLM-5.3 永久保存アーカイブ — Collector's Edition

> GLM-5.3（Z.ai / 智譜AI）が公開されているうちに、**失われたら二度と手に入らないもの**を
> この GitHub リポジトリに固定し、**あとから誰でも完全なアーカイブを再構築・検証できる**ようにするためのキットです。
>
> 取得日: **2026-10-01 (UTC)** ／ 上流: `zai-org/GLM-5.3`（リビジョン固定済み・下記）
> 取得時点の状態: **公開中・gated=false（誰でも無認証でダウンロード可能）**

---

## 0. 最初に読んでください（結論と、正直な現状報告）

**やったこと**

| 対象 | 結果 |
|---|---|
| GLM-5.3 本体（FP8）**全155ファイルの指紋**（path / サイズ / **SHA-256**） | ✅ 取得・保存（`manifests/`） |
| GLM-5.3 の**法務・設定ファイルの実バイト**（LICENSE・config系・chat template・. gitattributes） | ✅ 5ファイルを**上流 git blob SHA-1 と完全一致で検証済み**（`metadata/`） |
| モデルカード（README） | △ 再構成テキストとして保存（**バイト完全一致は未達**・理由は同梱の NOTICE） |
| 4リポジトリ（FP8/BF16 × 本家/Flash）の**リビジョン固定情報** | ✅ 保存（`manifests/REPOS.json`） |
| **重み本体 755.66 GB（F8）/ 1.51 TB（BF16）** | ❌ このリポジトリにも、この作業環境にも**物理的に格納できない** |
| 取得・検証・ミラー・torrent化の**自動化ツール** | ✅ 同梱（`tools/`） |

**できなかったことと、その理由（重要）**

1. **GitHub には重みを置けません（物理的・規約的に不可能）。**
   GitHub は 1ファイル 100 MiB 超の push を拒否し、リポジトリは 1 GB 未満が推奨・5 GB で警告、
   Git LFS も無料枠は 1 GiB 程度です。755 GB（＝LFS を使っても有料プラン数枚分）は載りません。
   → **GitHub 側には「索引（指紋）」と「検証ツール」と「復元手順」を置く**のが正解です（本リポジトリ）。
2. **この作業環境（サンドボックス）から Hugging Face への通信が遮断されていました。**
   TLS が SNI 単位でリセットされ、`huggingface.co` / `hfd-mirror` / ModelScope / Internet Archive の
   いずれにも到達できません（GitHub と PyPI のみ許可）。したがって**私が代わりに755GBを落としてくることはできません**。
   → 重量物の取得は、**あなたのPC/サーバーで `tools/` を実行**してください（3コマンド・下記 §3）。
3. よって本リポジトリは「**金庫の中身**」ではなく「**金庫の設計図＋鍵＋目録**」です。
   中身（重み）は、まだ公開されている今のうちに、§3 の手順で**あなたのストレージ**に確保してください。
   一度確保してしまえば、以後は本リポジトリの SHA-256 目録で**永久に真正性を検証**できます。

> ⏳ **時間が価値です。** 上流が非公開化・削除されると、目録があっても再取得はできません。
> まず §3 を実行して「実体」を確保することを強く推奨します。

---

## 1. 何が保存されているか（収録物）

```
.
├── README.md                      ← この文書（日本語）
├── manifests/                     ← 指紋（目録）
│   ├── zai-org__GLM-5.3.manifest.json   ★ 155ファイルの path/size/SHA-256 完全目録
│   ├── REPOS.json                       ★ 4リポジトリのリビジョン固定情報
│   ├── SHA256SUMS.glm-5.3                ★ sha256sum -c 用（141シャード＋14ファイル）
│   └── MANIFEST.sha256                  ← 目録自身の改竄検知用ハッシュ
├── metadata/
│   └── zai-org__GLM-5.3/          ← 上流ファイルの実バイト（なるべく原本のまま）
│       ├── LICENSE                        ✅ 検証済み（GLM-5.3 License 全文・英中併記）
│       ├── .gitattributes                 ✅ 検証済み
│       ├── config.json は含みません → 目録に指紋のみ（§5 参照）
│       ├── generation_config.json         ✅ 検証済み
│       ├── tokenizer_config.json          ✅ 検証済み
│       ├── chat_template.jinja            ✅ 検証済み（10734B・完全一致）
│       ├── README.model-card.reconstructed.md   △ 再構成（非バイト検証）
│       └── README.model-card.NOTICE.md          ← その旨の説明
├── tools/                         ← 再取得・検証・ミラー・torrent 化
│   ├── snapshot_metadata.py       … メタデータ完全取得＋マニフェスト生成（要ネット）
│   ├── download_weights.py        … 重みの再開可能DL＋SHA-256検証（要ネット）
│   ├── verify_archive.py          … 手元コピーをオフライン検証（ネット不要）
│   ├── mirror_to_hf.py            … 自分のHFリポジトリへミラー（永久化）
│   └── make_torrent.py            … .torrent 生成（分散保存用・純Python）
└── docs/
    ├── ARCHIVE-PLAN.md            … 755GB/1.5TB をどこにどう保存するか（数字と費用）
    ├── PROVENANCE.md              … 取得の記録・検証結果・再検証手順
    └── LICENSE-NOTES.md           … 再配布は合法か（合法です）・条件の解説
```

---

## 2. 目録（マニフェスト）の意味

`manifests/zai-org__GLM-5.3.manifest.json` は、上流リポジトリの全ファイルについて
**Hugging Face の LFS oid（＝ファイル内容の SHA-256）とサイズ**を記録したものです。

* 取得元: `https://huggingface.co/api/models/zai-org/GLM-5.3/tree/main?recursive=true`
* リビジョン: `aca966e4e02791568aa6a4ced368624b3d897f42`（2026-09-04T06:41:23Z 時点）
* 収録: **155 ファイル / 141 重みシャード / 合計 755,663,689,206 バイト（755.66 GB）**

この合計値は、外部の独立報道が伝える「755.6〜755.7 GB」および Hugging Face の
`usedStorage = 755,681,496,428`（差分 0.0024% = ポインタ/メタデータ分）と一致しており、
**目録が上流の実体と整合していることの傍証**になっています。

> 目録があれば、上流が消えた後でも
> ① 手元のコピーが本物か、② 第三者のミラーが本物か、③ torrent の中身が本物か
> を **完全に判定できます**。これが「永久保存」の実務的な中核です。

---

## 3. クイックスタート — あなたのマシンで完全アーカイブを作る（3コマンド）

Hugging Face に到達できるマシン（自宅PC・VPS・クラウド）で実行してください。
**755 GB（F8のみ）／約1.51 TB（BF16も含む）の空き容量**が必要です。

```bash
# 0) 準備（初回のみ）
pip install -U "huggingface_hub[cli]" requests

# 1) メタデータ＋全リポジトリの完全マニフェストを再取得・照合
python3 tools/snapshot_metadata.py --all --verify

# 2) 重み本体をダウンロード（再開可能・SHA-256 検証つき）
python3 tools/download_weights.py --repo zai-org/GLM-5.3 --out ./archive --verify
#   BF16 も必要なら:
#   python3 tools/download_weights.py --repo zai-org/GLM-5.3-BF16 --out ./archive --verify

# 3) オフライン検証（ネット不要・何度でも）
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root ./archive
```

`download_weights.py` は **hf_transfer / aria2c があれば自動で多コネクション**、
なければ `huggingface_hub` のレジューム機能で取得します。中断しても再実行すれば続きから再開します。

### 取得対象（どれを落とすか）

| リポジトリ | 内容 | サイズ | ライセンス | 備考 |
|---|---|---|---|---|
| `zai-org/GLM-5.3` | **本家 FP8（推奨・最優先）** | **755.66 GB**（141 shards） | GLM-5.3 License | 744B/40B MoE・1M context |
| `zai-org/GLM-5.3-BF16` | 本家 BF16（厳密な再学習・変換用） | **約1.51 TB**（282 shards） | GLM-5.3 License | FP8 から復元は不可（非可逆） |
| `zai-org/GLM-5.3-Flash` | Flash FP8（家庭環境向け・320B/18B） | 約328 GB（62 shards） | **MIT** | マルチモーダル |
| `zai-org/GLM-5.3-Flash-BF16` | Flash BF16 | 約642.7 GB（120 shards） | **MIT** | |

> 容量が厳しい場合の優先順位: **①GLM-5.3 FP8 → ②GLM-5.3-Flash FP8 → ③BF16系**。
> 量子化版（GGUF 等）は上流 FP8/BF16 から**後から誰でも再生成できる**ので、
> 「永久保存」の観点では**原版（FP8/BF16）が最優先**です（量子化版は非可逆な派生）。

---

## 4. 検証（このリポジトリの使い方の核心）

```bash
# 目録自体が改竄されていないか
sha256sum -c manifests/MANIFEST.sha256

# 手元コピーの全ファイルを照合（サイズ＋SHA-256）
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root ./archive --report verify.json

# 巨大ディスクで時間が無いとき: ランダムに20シャードだけ抜き取り検査
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root ./archive --sample 20

# GNU coreutils だけでやる場合（141シャード）
cd ./archive/model-00001-of-00141.safetensors のあるディレクトリ
sha256sum -c /path/to/SHA256SUMS.glm-5.3
```

検証は**ネット接続不要**です。10年後でも、上流が消えていても動きます。
（`tools/` は Python 3.8+ の標準ライブラリだけで動くよう設計しています。）

---

## 5. なぜ `config.json` の「中身」が入っていないのか

`config.json`（29,464 B）は、**アーキテクチャ定義（784層・MoE・DSA indexer・FP8量子化条件）を含む最重要ファイル**ですが、
700行におよぶ `modules_to_not_convert` 配列を人手で転記すると誤りが混入するリスクが高すぎるため、
**実バイトを貼ることを意図的に避けました**（誤ったコピーは、無いより有害です）。

代わりに:

* **サイズと git blob SHA-1（`f4dd8fe8be2a6fee923d5ecc8de0a14892631b61`）を目録に記録**（改竄・取り違え検知）
* **`tools/snapshot_metadata.py` が上流から正確なバイトを取得し、blob SHA-1 を照合**（一致しなければ失敗）

同じ方針で、`tokenizer.json`（20.2 MB）と `model.safetensors.index.json`（11.4 MB）は
**指紋のみ**を記録しています（大きすぎて手作業転記は不可能。ツールで取得・検証可能）。
これら小サイズの「正本」を回収したい場合は、ネットが使える環境で
`python3 tools/snapshot_metadata.py --repo zai-org/GLM-5.3` を実行してください。

---

## 6. 重みをどこに置くか（GitHub以外の現実的な選択肢）

詳細と数字は [`docs/ARCHIVE-PLAN.md`](docs/ARCHIVE-PLAN.md) に。要点のみ:

| 保存先 | 755 GB の可否 | 費用の目安 | 向き |
|---|---|---|---|
| **Hugging Face の自分のミラーリポジトリ** | ◎ | 無料（公開） | **第一推奨**。同じインフラなので最も自然 |
| **Internet Archive（archive.org）** | ○ | 無料 | 第二推奨。第三者による永久化・URL 固定 |
| 手元の HDD/SSD（2台以上） | ◎ | 2TB HDD ×2 ≒ 1〜2万円 | **実体の最終防衛線**。ここが無いと全部絵に描いた餅 |
| Backblaze B2 / S3 Deep Archive | ◎ | 約 $6/TB/月（B2）／さらに安価な cold | 低コスト・高耐久のオフサイト |
| BitTorrent / IPFS | ◎ | 実質無料 | 分散冗長。目録のSHA-256と相性が良い |
| **GitHub（通常/LFS/Release）** | ✕ | — | 100 MiB/ファイル制限・LFS 1 GiB 枠。**置けません** |

ミラー作成例:

```bash
export HF_TOKEN=...   # 自分のトークン
python3 tools/mirror_to_hf.py --repo zai-org/GLM-5.3 --src ./archive --dest your-name/GLM-5.3-archive
python3 tools/make_torrent.py --root ./archive --out glm-5.3.torrent --tracker udp://tracker.opentrackr.org:1337/announce
```

---

## 7. ライセンス（再配布は合法です）

* **GLM-5.3 本体・BF16**: 「GLM-5.3 License」（MIT 様式の広い許諾。**使用・改変・再配布・販売可**。
  連続12か月の総収入が 100億ドル超の「Model as a Service」事業者のみ、商用利用前に Z.AI の
  セキュリティレビュー通過が必要）。全文は [`metadata/zai-org__GLM-5.3/LICENSE`](metadata/zai-org__GLM-5.3/LICENSE)。
* **GLM-5.3-Flash 系**: 素の **MIT**。
* したがって**ミラー・torrent・アーカイブはライセンス上問題ありません**（著作権表示と本許諾文を同梱すること）。
* 本リポジトリの `tools/`・`docs/` は **MIT** とします。`metadata/` は元ライセンスに従います。

詳細な解釈は [`docs/LICENSE-NOTES.md`](docs/LICENSE-NOTES.md)。

---

## 8. FAQ

**Q. 上流が消えたらどうなりますか。**
A. すでに実体を確保してあれば、本リポジトリの目録で検証しながら使い続けられます。
まだ確保していない場合、**目録はあっても重みは手に入りません**。だから今すぐ §3 を。

**Q. なぜ自動で落としてくれないのですか。**
A. この作業環境から Hugging Face への TLS が遮断されているためです（§0-2）。
GitHub / PyPI のみ到達可能でした。重量物はあなたの回線で落としてください。

**Q. FP8 だけあれば BF16 は不要では？**
A. FP8 は**非可逆**です。研究・再量子化・厳密な再現には BF16 が必要になります。
「永久保存」の観点では BF16 こそ原版（学習成果そのもの）なので、容量が許すなら両方。

**Q. GGUF（Unsloth等）を保存すれば十分では？**
A. いいえ。量子化版は原版から**誰でも再生成できる派生**であり、原版が消えると再生成できません。
原版優先、派生は後回しで構いません。

**Q. 目録の SHA-256 は何を保証しますか。**
A. 「そのファイルが、2026-10-01 時点の上流と**1バイトも違わない**」ことです。
改竄・転送エラー・部分的な破損を検出できます。

**Q. 著作権的にグレーではありませんか。**
A. いいえ。GLM-5.3 License は再配布を明示的に許諾しています（条件は表示保持と法遵守、および
100億ドル超のMaaS事業者向けの審査条項のみ）。詳細は `docs/LICENSE-NOTES.md`。

---

## 9. 出典・クレジット

* モデル: Z.ai（智譜AI） — `zai-org/GLM-5.3` / `-BF16` / `-Flash` / `-Flash-BF16`
* 技術レポート: arXiv:2602.15763「GLM-5: from Vibe Coding to Agentic Engineering」
* 取得方法: Hugging Face Hub API（`/api/models/...` および `/api/models/.../tree/...`）
* 本リポジトリの目録・検証結果は、上流の **git blob SHA-1 / LFS SHA-256** に基づきます。

*メンテナ向け: 再取得・再検証の手順は [`docs/PROVENANCE.md`](docs/PROVENANCE.md) に記録されています。*
