# 来歴（Provenance）— 何をいつ、どう取得し、どう検証したか

## 1. 取得の概要

| 項目 | 値 |
|---|---|
| 取得日 | **2026-10-01 (UTC)** |
| 取得者 | Arena.ai Agent Mode（作業ブランチ `arena/01a0f4e4-glm5-3-collector-s-edition`） |
| 取得元 | `huggingface.co`（Hugging Face Hub API の model info / tree API） |
| 取得時点の状態 | 全4リポジトリ **公開・gated=false**（無認証で取得可能） |
| 対象リビジョン | `zai-org/GLM-5.3` = `aca966e4e02791568aa6a4ced368624b3d897f42`（他は `manifests/REPOS.json`） |

### 取得方法の重要な制約（このスナップショットの限界）

作業環境（サンドボックス）のネットワークポリシーにより、
**`huggingface.co` への TLS 接続は SNI 単位で遮断**されていた
（`SSL_ERROR_SYSCALL` / TCP は成立、HTTP はリセット）。到達可能だったのは GitHub と PyPI のみ。

そのため:

* **重み本体（755 GB / 1.51 TB）のダウンロードは実行できなかった**（物理的ディスクも 20 GB のみ）。
* メタデータは、外部取得経路（フェッチツール）を介した **テキスト転記** で取得し、
  **git blob SHA-1 による完全一致検証**で正しさを担保した。
* 目録（ファイル一覧・サイズ・SHA-256）は tree API の応答を 1 件ずつ転記し、
  **合計サイズが上流の `usedStorage` と 0.0024% 以内で一致**することを確認した。

---

## 2. 検証済みキャプチャ（バイト完全一致）

`metadata/zai-org__GLM-5.3/` 内の以下のファイルは、上流の **git blob SHA-1** と
**完全一致**した（＝ 1 バイトも違わない）。

| ファイル | サイズ | git blob SHA-1 | 検証 |
|---|---:|---|---|
| `LICENSE` | 4,263 B | `f860919cd5a5377c0bc9d590ea9d1b8743475ca5` | ✅ 一致 |
| `.gitattributes` | 1,635 B | `a09db2ea4d1bd1fc1c09f6fca45e8e4054953535` | ✅ 一致 |
| `generation_config.json` | 194 B | `216bbb092d0df0dda1dc4cedd789b92286c4c001` | ✅ 一致 |
| `tokenizer_config.json` | 761 B | `e375fa0a4e16660ce0e2026e39374d35dad4c079` | ✅ 一致 |
| `chat_template.jinja` | 10,734 B | `9aff9c44583c869853049724ffe67b1070344f2d` | ✅ 一致 |

検証方法（再現可能）:

```bash
cd metadata/zai-org__GLM-5.3
git hash-object LICENSE .gitattributes generation_config.json tokenizer_config.json chat_template.jinja
```

## 3. 再構成（バイト検証は未達）

| ファイル | 上流サイズ | 本版サイズ | 上流 git blob SHA-1 | 状態 |
|---|---:|---:|---|---|
| `README.model-card.reconstructed.md` | 14,209 B | 14,211 B | `e965a0a6ea0da381140a9ce4cc2c571058a31d05` | △ +2 バイト差（内容は実質同一・自動探索でも特定できず） |

* 共有部分（ベンチマーク表・脚注）は、公式 GitHub リポジトリ `zai-org/GLM-5` の
  README（別文書）と**行単位で一致**することを確認済み。
* 正本が必要な場合は、ネットが使える環境で
  `python3 tools/snapshot_metadata.py --repo zai-org/GLM-5.3 --verify` を実行すること
  （blob SHA-1 照合つきで取得される）。

## 4. 指紋のみ（実バイト未収録）のファイル

| ファイル | サイズ | 記録したダイジェスト | 理由 |
|---|---:|---|---|
| `config.json` | 29,464 B | git blob SHA-1 `f4dd8fe8be2a6fee923d5ecc8de0a14892631b61` | 700 行の反復配列を含み、人手転記は誤り混入リスクが高いため意図的に除外 |
| `tokenizer.json` | 20,217,442 B | LFS SHA-256 `19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d` | サイズ過大 |
| `model.safetensors.index.json` | 11,359,251 B | LFS SHA-256 `e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf` | サイズ過大 |
| 重み 141 シャード | 計 755.63 GB | LFS SHA-256 ×141（目録に全件） | 物理的に不可能（容量・回線） |

いずれも `tools/snapshot_metadata.py` / `tools/download_weights.py` で
**照合つき取得**が可能。

---

## 5. 目録（マニフェスト）の内容と検証

* `manifests/zai-org__GLM-5.3.manifest.json`
  * 155 ファイル（重みシャード 141 + メタデータ 14）
  * 合計 **755,663,689,206 バイト（755.6637 GB）**
  * 派生値の突合:
    * 上流 `usedStorage` = 755,681,496,428 B → 差 **0.0024%**（LFS ポインタ等）
    * 独立報道の「755.6〜755.7 GB」と一致
    * safetensors メタデータ: F8_E4M3 751,226,191,872 B / BF16 2,103,729,152 B /
      F32 19,456 B / 合計 **753,329,940,480 パラメータ**（= 744B 級 MoE）
* 目録自身の完全性: `manifests/MANIFEST.sha256`（`sha256sum -c` で検証）
  * `zai-org__GLM-5.3.manifest.json` → `5a361f3cfffad1bcaa64634b702ef2d6de2a281157d45ba705294d067da85f90`

### 転記の品質管理

141 シャードのサイズ・ハッシュは人手転記であるため、次で検査した:

1. 全サイズが 8 の倍数であること（FP8 パラメータブロックの性質）
2. サイズが 4.0〜6.0 GB の妥当域にあること
3. シャード番号 00001〜00141 が欠番なく揃うこと
4. **合計が上流 `usedStorage` と 0.0024% 以内で一致すること**
5. 目録と独立に、外部報道値（755.6/755.7 GB）と一致すること

> 万一 1 件でも転記誤りがあれば合計値がずれる確率が高く、
> 上記 4・5 の一致は強い傍証である。ただし**完全な保証が必要な場合は、
> 下記の手順で目録を再生成して突き合わせること**。

```bash
python3 tools/snapshot_metadata.py --repo zai-org/GLM-5.3 --verify
diff manifests/zai-org__GLM-5.3.manifest.json <(git show HEAD:manifests/zai-org__GLM-5.3.manifest.json)
```

---

## 6. 第三者による再検証の手順（推奨）

```bash
# 1) 本リポジトリの目録を取得
git clone https://github.com/2chkakinie-arch/GLM5.3-Collector-s-edition
cd GLM5.3-Collector-s-edition
sha256sum -c manifests/MANIFEST.sha256        # 目録が改竄されていないこと

# 2) 上流から再取得して目録と突合（ネット必要）
python3 tools/snapshot_metadata.py --repo zai-org/GLM-5.3 --verify
diff manifests/zai-org__GLM-5.3.manifest.json /tmp/regenerated.json

# 3) 手元/第三者のミラーを検証（ネット不要）
python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root /path/to/copy
```

---

## 7. 参照した外部情報（取得時点）

* Hugging Face Hub API
  * `GET /api/models/zai-org/GLM-5.3`（sha / usedStorage / safetensors メタデータ）
  * `GET /api/models/zai-org/GLM-5.3/tree/main?recursive=true`（155 ファイルの一覧）
  * `GET /api/models/zai-org/GLM-5.3/raw/main/{LICENSE,config.json,...}`（実バイト）
* 公式 GitHub リポジトリ `zai-org/GLM-5`（README の突合に使用）
* 報道・解説（サイズの傍証）: 755.6 GB / 755.7 GB との一致を確認

> 注: 上流の内容は将来変更され得る。本リポジトリの記録は
> **上記リビジョン時点のスナップショット**である。
