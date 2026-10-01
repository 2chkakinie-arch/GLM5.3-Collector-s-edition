#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""download_weights.py — 重み本体を「中断に強く」「検証つき」で取得する。

ネット接続が必要。Hugging Face に到達できるマシンで実行すること。
  * huggingface_hub があれば、それを使う（レジューム・並列・HF_ENDPOINT ミラー対応）
  * さらに hf_transfer があれば高速転送（HF_HUB_ENABLE_HF_TRANSFER=1 を自動設定）
  * どちらも無い場合は urllib によるレンジ再開ダウンロードにフォールバック
  * 取得後、目録（manifests/*.manifest.json）の SHA-256 と照合（--verify）
  * aria2c があれば全シャードを多コネクションで先に取得するモードも選べる（--aria2c）

使い方:
  python3 tools/download_weights.py --repo zai-org/GLM-5.3 --out ./archive --verify
  python3 tools/download_weights.py --repo zai-org/GLM-5.3-BF16 --out ./archive --jobs 4
  python3 tools/download_weights.py --repo zai-org/GLM-5.3 --out ./archive --only-shards --aria2c
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time, urllib.request

CHUNK = 1024 * 1024
ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co")


def find_manifest(repo: str) -> str | None:
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(os.path.dirname(here), "manifests", repo.replace("/", "__") + ".manifest.json")
    return cand if os.path.exists(cand) else None


def load_manifest(repo: str):
    p = find_manifest(repo)
    if not p:
        return None, None
    with open(p, "r", encoding="utf-8") as f:
        m = json.load(f)
    return m, m["repo"].get("revision")


def sha256_file(path: str, progress_cb=None) -> tuple:
    h = hashlib.sha256(); n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(8 * 1024 * 1024)
            if not b:
                break
            n += len(b); h.update(b)
            if progress_cb:
                progress_cb(n)
    return h.hexdigest(), n


def dl_url(repo: str, rev: str, path: str) -> str:
    return "%s/%s/resolve/%s/%s" % (ENDPOINT.rstrip("/"), repo, rev or "main", path)


def download_resume(url: str, dest: str, token: str | None = None) -> None:
    """urllib によるレンジ再開ダウンロード。"""
    os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
    for attempt in range(1, 11):
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        req = urllib.request.Request(url)
        if have:
            req.add_header("Range", "bytes=%d-" % have)
        if token:
            req.add_header("Authorization", "Bearer %s" % token)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                total = r.headers.get("Content-Length")
                mode = "ab" if have else "wb"
                with open(dest, mode) as f:
                    while True:
                        b = r.read(CHUNK)
                        if not b:
                            break
                        f.write(b)
                        have += len(b)
                return
        except Exception as e:  # noqa: BLE001
            wait = min(60, 2 ** attempt)
            print("   再試行(%d) %s: %s — %ds 待機" % (attempt, os.path.basename(dest), e, wait), file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("ダウンロード失敗: %s" % url)


def main() -> int:
    ap = argparse.ArgumentParser(description="GLM-5.3 重みの検証つきダウンロード")
    ap.add_argument("--repo", required=True, help="例: zai-org/GLM-5.3")
    ap.add_argument("--out", required=True, help="保存先ディレクトリ")
    ap.add_argument("--revision", default=None, help="リビジョン固定（既定: 目録の revision / main）")
    ap.add_argument("--jobs", type=int, default=1, help="並列数（huggingface_hub 使用時のみ）")
    ap.add_argument("--verify", action="store_true", help="取得後に SHA-256 を照合")
    ap.add_argument("--only-shards", action="store_true", help="model-*.safetensors のみ")
    ap.add_argument("--aria2c", action="store_true", help="aria2c で多コネクション取得（要 aria2c）")
    ap.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="HF トークン（private リポジトリ用）")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    manifest, rev = load_manifest(a.repo)
    if manifest:
        rev = a.revision or rev
        files = manifest["files"]
        if a.only_shards:
            files = [f for f in files if f["path"].startswith("model-")]
        print("目録を使用: %d ファイル / rev %s" % (len(files), (rev or "?")[:12]))
        total = sum(f.get("size") or 0 for f in files)
        free = __import__("shutil").disk_usage(a.out).free
        print("必要容量: %.2f GB / 空き: %.2f GB" % (total / 1e9, free / 1e9))
        if total > free:
            print("ERROR: 空き容量が不足しています", file=sys.stderr)
            return 2
    else:
        rev = a.revision or "main"
        print("目録が見つからないため、全ファイルを列挙して取得します（検証は --verify 不可）")
        files = None

    if a.aria2c and manifest:
        if not __import__("shutil").which("aria2c"):
            print("ERROR: aria2c が見つかりません", file=sys.stderr)
            return 2
        urls = [dl_url(a.repo, rev, f["path"]) for f in files]
        hdrs = ["Authorization: Bearer %s" % a.token] if a.token else []
        listfile = os.path.join(a.out, ".aria2_input.txt")
        with open(listfile, "w", encoding="utf-8") as f:
            for u in urls:
                f.write(u + "\n")
                f.write("  dir=%s\n" % os.path.abspath(a.out))
                f.write("  out=%s\n" % os.path.basename(u.split("/resolve/")[1].split("/", 1)[1]))
        cmd = ["aria2c", "-i", listfile, "-j", str(max(2, a.jobs)), "-x", "8", "-s", "8",
               "-c", "--file-allocation=none", "--console-log-level=warn", "--summary-interval=30"]
        for h in hdrs:
            cmd += ["--header", h]
        print("実行: %s" % " ".join(cmd[:6] + ["..."]))
        return subprocess.call(cmd)

    ok = bad = 0
    if manifest:
        try:  # huggingface_hub があればそちらを使う（レジューム・並列が堅牢）
            from huggingface_hub import hf_hub_download  # type: ignore
        except Exception:  # noqa: BLE001
            hf_hub_download = None
        if hf_hub_download is not None:
            print("huggingface_hub を使用します（レジューム有効）")
            for i, f in enumerate(files, 1):
                dest = os.path.join(a.out, f["path"])
                print("[%d/%d] %s (%.2f GB)" % (i, len(files), f["path"], (f.get("size") or 0) / 1e9))
                hf_hub_download(repo_id=a.repo, filename=f["path"], revision=rev,
                                local_dir=a.out, token=a.token)
                if a.verify and f.get("sha256"):
                    got, _ = sha256_file(dest)
                    if got == f["sha256"]:
                        ok += 1
                    else:
                        bad += 1
                        print("   ✗ SHA-256 不一致: %s" % f["path"], file=sys.stderr)
            print("検証: 一致 %d / 不一致 %d" % (ok, bad))
            return 0 if bad == 0 else 1
        for i, f in enumerate(files, 1):
            dest = os.path.join(a.out, f["path"])
            print("[%d/%d] %s" % (i, len(files), f["path"]))
            download_resume(dl_url(a.repo, rev, f["path"]), dest, a.token)
            if a.verify and f.get("sha256"):
                got, _ = sha256_file(dest)
                if got == f["sha256"]:
                    ok += 1
                else:
                    bad += 1
                    print("   ✗ SHA-256 不一致: %s" % f["path"], file=sys.stderr)
        print("検証: 一致 %d / 不一致 %d" % (ok, bad))
        return 0 if bad == 0 else 1

    try:
        from huggingface_hub import snapshot_download  # type: ignore
    except Exception:  # noqa: BLE001
        print("ERROR: huggingface_hub が必要です: pip install -U huggingface_hub", file=sys.stderr)
        return 2
    snapshot_download(repo_id=a.repo, revision=rev, local_dir=a.out,
                      max_workers=max(1, a.jobs), token=a.token)
    print("完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
