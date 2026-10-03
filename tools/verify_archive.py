#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_archive.py — 取得済みアーカイブを「オフラインで」検証する。

ネット接続は不要。manifests/*.manifest.json の目録（サイズ + SHA-256）と、
手元のファイルを突き合わせて、欠落・破損・改竄を検出する。

使い方:
  python3 tools/verify_archive.py --manifest manifests/zai-org__GLM-5.3.manifest.json --root ./archive
  python3 tools/verify_archive.py --manifest manifests/*.manifest.json --root ./archive --sample 20
  python3 tools/verify_archive.py --manifest ... --root ./archive --report verify.json --jobs 8

終了コード: 0 = 全て一致 / 1 = 不一致・欠落あり / 2 = 使い方のエラー
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

CHUNK = 8 * 1024 * 1024


def sha256_of(path: str) -> tuple:
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            n += len(b)
            h.update(b)
    return h.hexdigest(), n


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        m = json.load(f)
    if "files" not in m or "repo" not in m:
        raise ValueError("manifest 形式が不正です: %s" % path)
    return m


def check_one(root: str, entry: dict, small_read_limit: int = 32 * 1024 * 1024) -> dict:
    rel = entry["path"]
    p = os.path.join(root, rel)
    exp_size = entry.get("size")
    exp_sha = entry.get("sha256")
    res = {"path": rel, "status": "OK", "expected_size": exp_size, "actual_size": None, "detail": ""}
    if not os.path.exists(p):
        res["status"] = "MISSING"
        return res
    actual_size = os.path.getsize(p)
    res["actual_size"] = actual_size
    if exp_size is not None and actual_size != exp_size:
        res["status"] = "SIZE_MISMATCH"
        res["detail"] = "size %d != %d" % (actual_size, exp_size)
        return res
    # 小さいファイルで content-sha256 が未記録なら git blob SHA-1 で照合する
    if exp_sha is None and entry.get("git_blob_sha1"):
        if actual_size > small_read_limit:
            res["status"] = "SKIP"
            res["detail"] = "too large for blob check"
            return res
        with open(p, "rb") as f:
            data = f.read()
        got = git_blob_sha1(data)
        if got != entry["git_blob_sha1"]:
            res["status"] = "HASH_MISMATCH"
            res["detail"] = "blob %s != %s" % (got, entry["git_blob_sha1"])
        return res
    if exp_sha:
        got, _ = sha256_of(p)
        if got != exp_sha:
            res["status"] = "HASH_MISMATCH"
            res["detail"] = "sha256 %s != %s" % (got[:16] + "...", exp_sha[:16] + "...")
    else:
        res["status"] = "SKIP"
        res["detail"] = "no digest recorded (size-only check passed)"
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="オフライン検証（目録 vs 手元コピー）")
    ap.add_argument("--manifest", nargs="+", required=True, help="manifests/*.manifest.json")
    ap.add_argument("--root", required=True, help="検証するディレクトリ（リポジトリのルート）")
    ap.add_argument("--jobs", type=int, default=max(2, (os.cpu_count() or 4)), help="並列数")
    ap.add_argument("--sample", type=int, default=0, help="ランダムに N 件だけ検証（抜き取り）")
    ap.add_argument("--only-shards", action="store_true", help="重みシャードのみ検証")
    ap.add_argument("--report", help="JSON レポート出力先")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.root):
        print("ERROR: --root が存在しません: %s" % a.root, file=sys.stderr)
        return 2

    all_results, summary = [], {"manifests": [], "files": 0, "ok": 0, "bad": 0, "missing": 0, "skip": 0}
    for mp in a.manifest:
        m = load_manifest(mp)
        files = m["files"]
        if a.only_shards:
            files = [f for f in files if f["path"].startswith("model-") and f["path"].endswith(".safetensors")]
        if a.sample and len(files) > a.sample:
            files = random.sample(files, a.sample)
        if not a.quiet:
            print("== %s (%s / rev %s)" % (m["repo"]["id"], os.path.basename(mp), m["repo"].get("revision", "?")[:12]))
            print("   対象 %d ファイル, 合計 %.2f GB" % (
                len(files), sum(f.get("size") or 0 for f in files) / 1e9))
        results = []
        with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
            futs = {ex.submit(check_one, a.root, f): f for f in files}
            done = 0
            for fut in as_completed(futs):
                r = fut.result()
                results.append(r)
                done += 1
                if not a.quiet and (done % 20 == 0 or done == len(files)):
                    print("   ... %d/%d" % (done, len(files)))
        results.sort(key=lambda r: r["path"])
        bad = [r for r in results if r["status"] in ("HASH_MISMATCH", "SIZE_MISMATCH")]
        missing = [r for r in results if r["status"] == "MISSING"]
        skip = [r for r in results if r["status"] == "SKIP"]
        summary["manifests"].append({
            "manifest": mp, "repo": m["repo"]["id"], "checked": len(results),
            "ok": len([r for r in results if r["status"] == "OK"]),
            "bad": len(bad), "missing": len(missing), "skip": len(skip),
        })
        summary["files"] += len(results)
        summary["ok"] += len([r for r in results if r["status"] == "OK"])
        summary["bad"] += len(bad)
        summary["missing"] += len(missing)
        summary["skip"] += len(skip)
        if not a.quiet:
            for r in bad[:20]:
                print("   ✗ %s  %s (%s)" % (r["status"], r["path"], r["detail"]))
            for r in missing[:20]:
                print("   ✗ MISSING %s" % r["path"])
            if bad or missing:
                print("   → 不一致 %d 件, 欠落 %d 件" % (len(bad), len(missing)))
            else:
                print("   → すべて一致 ✅")
        all_results.extend(results)

    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "results": all_results}, f, ensure_ascii=False, indent=1)
        if not a.quiet:
            print("レポート: %s" % a.report)

    print("== 合計: 検証 %d / 一致 %d / 不一致 %d / 欠落 %d / スキップ %d" % (
        summary["files"], summary["ok"], summary["bad"], summary["missing"], summary["skip"]))
    return 0 if (summary["bad"] == 0 and summary["missing"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
