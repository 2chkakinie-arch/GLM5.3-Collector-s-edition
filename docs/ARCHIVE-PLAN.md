# 保存計画 — 755 GB ／ 1.51 TB をどこにどう置くか

対象物のサイズ（2026-10-01 時点・上流の公式リポジトリから集計）:

| リポジトリ | 現在の配布物サイズ | ファイル数 | 備考 |
|---|---:|---:|---|
| `zai-org/GLM-5.3`（FP8） | **755.66 GB** | 155（うち重み 141） | 本目録で全ファイルを SHA-256 化済み |
| `zai-org/GLM-5.3-BF16` | **約 1.51 TB** | 292（重み 282） | 非可逆な原版 |
| `zai-org/GLM-5.3-Flash`（FP8） | 約 328 GB | 72（重み 62） | MIT |
| `zai-org/GLM-5.3-Flash-BF16` | 約 642.7 GB | 130（重み 120） | MIT |
| **合計（4リポジトリ全部）** | **約 3.23 TB** | 約 650 | 重みのみ。作業用に +1〜2TB の余裕を推奨 |

> 補足: Hugging Face の `usedStorage` は過去リビジョンを含むため、Flash では
> 656.7 GB と表示される（現行の配布物は 328 GB）。容量計画は「配布物の合計」で立てること。

---

## 1. GitHub に置けない理由（数字で）

| 制限 | 値 | 755 GB に与える影響 |
|---|---|---|
| 1ファイルのハード上限 | **100 MiB**（超過は push 拒否。50 MiB で警告） | 重みシャードは 1個約 5.36 GB。**そのままでは push すら不可能** |
| リポジトリの推奨サイズ | **1 GB 未満**（5 GB 超で警告・場合により制限） | 3.23 TB は 3000 倍以上 |
| Git LFS 無料枠 | **1 GiB ストレージ / 1 GiB 月間帯域** | 755 GB を収めるには 50 GB パックを多数購入（実質非現実的） |
| GitHub Releases の1アセット上限 | **2 GiB** | 5.36 GB シャードは 3分割が必要。全リポジトリで **1,700 超のアセット**（規約・運用上あり得ない） |
| 帯域 | パブリック資産の大量配布は濫用判定の対象 | 恒久的な配布基盤にはできない |

**結論: GitHub は「重みの倉庫」にはできません。** 本リポジトリが GitHub に置いているのは
**目録（指紋）・法務文書・取得/検証ツール・手順書**です。これは意図的な設計です。

---

## 2. 推奨アーキテクチャ（3-2-1 ルール）

```
        ┌──────────────────────────────────────────────┐
        │  一次: 自分の Hugging Face ミラーリポジトリ     │  ← 無料・最速・再開可能
        │        （公開 or 非公開。同一インフラ）        │
        └──────────────────────────────────────────────┘
                 ↓ 複製
        ┌──────────────────────────────────────────────┐
        │  二次: Internet Archive / クラウド低温ストレージ │  ← 第三者性・地理冗長
        └──────────────────────────────────────────────┘
                 ↓ 複製
        ┌──────────────────────────────────────────────┐
        │  三次: 手元の HDD/SSD（2台以上・別筐体/別拠点）  │  ← 最終防衛線（ネット不要）
        └──────────────────────────────────────────────┘
                 ↓ 配布用
        ┌──────────────────────────────────────────────┐
        │  補助: BitTorrent / IPFS（目録の SHA-256 で検証）│
        └──────────────────────────────────────────────┘
```

**「三次（手元）」が無い計画は破綻します。** クラウドはアカウント停止・規約変更・
サービス終了で一瞬で消えます。必ずローカル実体を持つこと。

### 費用の目安（2026年時点の目安。契約前に必ず最新価格を確認）

| 手段 | 755 GB（FP8のみ） | 3.23 TB（全部） | 備考 |
|---|---:|---:|---|
| HF ミラー（公開） | 0 円 | 0 円 | 実質無制限。**第一選択** |
| Internet Archive | 0 円 | 0 円 | アカウント作成＋`ia` CLI。恒久 URL |
| 外付け HDD 2TB ×2 | 1〜2 万円（買い切り） | 4TB ×2 ≒ 2〜4 万円 | オフライン保管可 |
| Backblaze B2 | 約 $6/月 | 約 $25/月 | 下りは無料枠あり |
| S3 Glacier Deep Archive | 約 $1/月 | 約 $4/月 | 取り出しに時間・別料金 |
| 自宅 NAS（4TB ×2 RAID1） | — | 3〜6 万円 | 電気代＋消耗品 |

---

## 3. 具体的な手順

### 3.1 まず実体を確保（最優先）

```bash
pip install -U "huggingface_hub[cli]"
python3 tools/download_weights.py --repo zai-org/GLM-5.3 --out /mnt/big/archive --verify --jobs 2
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root /mnt/big/archive
```

* 回線が細い場合は `HF_HUB_ENABLE_HF_TRANSFER=1` と `hf_transfer` を入れると大幅に速くなる。
* 途中で切れても再実行すれば続きから再開する。
* **取得後は必ず検証を実行**すること（転送は静かに壊れることがある）。

### 3.2 HF ミラーを作る（無料・最速の冗長化）

```bash
export HF_TOKEN=hf_xxx
python3 tools/mirror_to_hf.py --repo zai-org/GLM-5.3 \
    --src /mnt/big/archive --dest your-name/GLM-5.3-archive
```

非公開にしたい場合は `--private`。公開なら第三者が検証・保持に参加できる（推奨）。

### 3.3 Internet Archive に退避

```bash
pip install internetarchive
ia configure                     # アカウント情報を入力
cd /mnt/big
ia upload glm-5.3-fp8-archive ./archive/* \
  --metadata="title:GLM-5.3 FP8 archive (zai-org)" \
  --metadata="license:GLM-5.3 License" \
  --metadata="description:Mirror of huggingface.co/zai-org/GLM-5.3 @ aca966e4"
```

### 3.4 torrent 化（分散・第三者ミラー歓迎）

```bash
python3 tools/make_torrent.py --root /mnt/big/archive --out glm-5.3.torrent \
  --tracker udp://tracker.opentrackr.org:1337/announce \
  --tracker https://tracker.gbitt.info:443/announce \
  --piece-length-mib 16
# 出力された info-hash を本リポジトリの Issue / README に記録しておくと良い
```

### 3.5 定期検証（四半期ごと推奨）

```bash
# 全数検証（時間がかかる）
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root /mnt/big/archive
# 抜き取り（月次）
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root /mnt/big/archive --sample 20
```

### 3.6 上流の変化を検知（ドリフト監視）

```bash
# ネットが使える環境で: 目録を再生成し、リビジョンが変わっていないか確認
python3 tools/snapshot_metadata.py --repo zai-org/GLM-5.3 --verify
git diff --stat            # manifest の差分 = 上流の変化
```

* `revision` が変わっていなければ、上流は内容を変更していない。
* **上流が削除・非公開化された場合**、`snapshot_metadata.py` は失敗する。
  その失敗自体が「今すぐミラーから復元すべき」というシグナルになる。

---

## 4. よくある誤解

* **「HF が消えるなら HF にミラーしても無意味では？」**
  → 完全な対策は不可能です。だからこそ **複数の独立した保管先**（HF / IA / 手元 / torrent）に
  同じ内容を置き、**目録の SHA-256 で同一性を保証**します。1つが消えても他が生き残れば復元できます。
* **「GGUF を保存しておけば十分では？」**
  → 派生（量子化）は原版から再生成できますが、原版は派生から復元できません。**原版が最優先**です。
* **「Git LFS を有料にすれば GitHub に置けるのでは？」**
  → ストレージ課金だけで解決しません。**1ファイル 100 MiB 制限**があるため
  5.36 GB シャードは必ず分割が必要で、数百ファイルの分割アップロードは
  事実上メンテ不能・濫用判定リスクもあります。

---

## 5. 優先順位（時間と容量が限られるとき）

1. **`zai-org/GLM-5.3`（FP8 / 755.66 GB）** — 本命。まずこれ。
2. `zai-org/GLM-5.3-Flash`（FP8 / 328 GB） — MIT。実用価値が高く小さい。
3. `zai-org/GLM-5.3-BF16`（1.51 TB） — 厳密な原版。容量が許せば。
4. `zai-org/GLM-5.3-Flash-BF16`（642.7 GB） — 最後でよい。

**さらに最優先なのは「本リポジトリの目録」**です。これは数百 KB で、
GitHub 上に無期限に残り、上記すべての真正性を将来にわたって保証します。
