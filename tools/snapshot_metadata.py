#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""snapshot_metadata.py — 上流リポジトリの「目録」と「小さいファイルの実バイト」を取得する。

ネット接続が必要（Hugging Face に到達できる環境で実行）。実行すると:

  1. 各リポジトリのファイル一覧（path / size / LFS SHA-256）を取得して
     manifests/<owner>__<name>.manifest.json を生成（revision を固定して記録）
  2. LFS でない小さいファイル（既定 32 MiB 未満）を metadata/<owner>__<name>/ に
     ダウンロードし、**git blob SHA-1 を照合**する（一致しなければエラー）
  3. manifests/SHA256SUMS.<short>.txt と manifests/MANIFEST.sha256 を生成

使い方:
  python3 tools/snapshot_metadata.py --all
  python3 tools/snapshot_metadata.py --repo zai-org/GLM-5.3 --repo zai-org/GLM-5.3-Flash --verify
  python3 tools/snapshot_metadata.py --all --metadata-limit-mb 64

注意: 目録の LFS oid は「ファイル内容の SHA-256」である。小さいファイルについては
      git blob SHA-1 が追加で記録され、ダウンロード時に検証される。
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time

REPOS_DEFAULT = [
    "zai-org/GLM-5.3",
    "zai-org/GLM-5.3-BF16",
    "zai-org/GLM-5.3-Flash",
    "zai-org/GLM-5.3-Flash-BF16",
]


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="HF メタデータの完全スナップショット")
    ap.add_argument("--repo", action="append", default=None, help="対象リポジトリ（複数可）")
    ap.add_argument("--all", action="store_true", help="既定の4リポジトリ全部")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--verify", action="store_true", help="小ファイルをダウンロードして blob SHA-1 を照合")
    ap.add_argument("--metadata-limit-mb", type=int, default=32, help="実バイトを保存する上限サイズ(MiB)")
    ap.add_argument("--revision", default=None, help="リビジョン固定（既定: 上流の最新）")
    a = ap.parse_args()

    try:
        from huggingface_hub import HfApi, hf_hub_download  # type: ignore
    except Exception:  # noqa: BLE001
        print("ERROR: huggingface_hub が必要です: pip install -U huggingface_hub", file=sys.stderr)
        return 2

    repos = REPOS_DEFAULT if (a.all or not a.repo) else a.repo
    api = HfApi()
    mdir = os.path.join(a.root, "manifests")
    os.makedirs(mdir, exist_ok=True)
    manifest_paths = []

    for repo in repos:
        print("== %s" % repo)
        info = api.model_info(repo, files_metadata=True, revision=a.revision)
        rev = info.sha
        files = []
        for s in info.siblings or []:
            entry = {"path": s.rfilename, "size": getattr(s, "size", None)}
            lfs = getattr(s, "lfs", None)
            if lfs:
                entry["lfs"] = True
                entry["sha256"] = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
            else:
                entry["lfs"] = False
                blob = getattr(s, "blob_id", None)
                if blob:
                    entry["git_blob_sha1"] = blob
            files.append(entry)
        files.sort(key=lambda f: f["path"])
        total = sum(f.get("size") or 0 for f in files)
        manifest = {
            "schema": "glm53-archive-manifest/v1",
            "repo": {
                "id": repo,
                "url": "https://huggingface.co/%s" % repo,
                "revision": rev,
                "last_modified": str(info.last_modified),
                "license": str(info.card_data.get("license") if info.card_data else None),
                "gated": bool(info.gated),
                "architecture": (info.config or {}).get("architectures") if info.config else None,
                "used_storage_bytes": getattr(info, "used_storage", None),
            },
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "captured_via": "huggingface_hub HfApi.model_info(files_metadata=True) revision=%s" % (a.revision or "main"),
            "counts": {"files": len(files),
                       "weight_shards": len([f for f in files if f["path"].endswith(".safetensors")])},
            "bytes": {"total": total},
            "files": files,
        }
        out = os.path.join(mdir, repo.replace("/", "__") + ".manifest.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        manifest_paths.append(out)
        print("   目録: %s (%d files, %.2f GB, rev %s)" % (os.path.basename(out), len(files), total / 1e9, rev[:12]))

        # SHA256SUMS（sha256sum -c 用）
        sums = os.path.join(mdir, "SHA256SUMS.%s.txt" % repo.split("/")[-1])
        with open(sums, "w", encoding="utf-8") as f:
            for e in files:
                if e.get("sha256"):
                    f.write("%s  %s\n" % (e["sha256"], e["path"]))
        print("   sha256sum用: %s" % os.path.basename(sums))

        if a.verify:
            mdir_repo = os.path.join(a.root, "metadata", repo.replace("/", "__"))
            os.makedirs(mdir_repo, exist_ok=True)
            limit = a.metadata_limit_mb * 1024 * 1024
            saved = skipped = failed = 0
            for e in files:
                if e.get("lfs"):
                    continue
                if (e.get("size") or 0) > limit:
                    skipped += 1
                    continue
                dest = os.path.join(mdir_repo, e["path"])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                p = hf_hub_download(repo_id=repo, filename=e["path"], revision=rev, local_dir=mdir_repo)
                if os.path.abspath(p) != os.path.abspath(dest):
                    os.replace(p, dest)
                if e.get("git_blob_sha1"):
                    with open(dest, "rb") as fh:
                        got = git_blob_sha1(fh.read())
                    if got != e["git_blob_sha1"]:
                        print("   ✗ blob 不一致: %s" % e["path"], file=sys.stderr)
                        failed += 1
                    else:
                        saved += 1
                else:
                    saved += 1
            print("   実バイト保存: %d / スキップ %d / 失敗 %d" % (saved, skipped, failed))

    # 目録自身のハッシュ
    if manifest_paths:
        man = os.path.join(mdir, "MANIFEST.sha256")
        with open(man, "w", encoding="utf-8") as f:
            for p in sorted(manifest_paths):
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                f.write("%s  %s\n" % (h, os.path.basename(p)))
        print("目録ハッシュ: %s" % os.path.basename(man))
    return 0


if __name__ == "__main__":
    sys.exit(main())
