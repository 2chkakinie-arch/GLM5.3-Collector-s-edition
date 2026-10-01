#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_torrent.py — アーカイブを BitTorrent v1 の .torrent にする（純Python・依存なし）。

分散保存は「永久保存」の要。torrent の info-hash は目録の SHA-256 と組合わせて
「本物かどうか」を誰でも検証できる形にする。

使い方:
  python3 tools/make_torrent.py --root ./archive --out glm-5.3.torrent \
      --tracker udp://tracker.opentrackr.org:1337/announce \
      --tracker https://tracker.gbitt.info:443/announce --comment "GLM-5.3 FP8 archive"

  # info-hash（magnet 用）だけ知りたい場合
  python3 tools/make_torrent.py --root ./archive --out glm-5.3.torrent
"""
from __future__ import annotations
import argparse, hashlib, os, sys, time


def bencode(o) -> bytes:
    if isinstance(o, int):
        return b"i%de" % o
    if isinstance(o, bytes):
        return b"%d:%s" % (len(o), o)
    if isinstance(o, str):
        return bencode(o.encode("utf-8"))
    if isinstance(o, list):
        return b"l" + b"".join(bencode(x) for x in o) + b"e"
    if isinstance(o, dict):
        out = b"d"
        for k in sorted(o.keys(), key=lambda x: x.encode("utf-8") if isinstance(x, str) else x):
            out += bencode(k) + bencode(o[k])
        return out + b"e"
    raise TypeError(type(o))


def collect(root: str):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            if not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            files.append((rel, os.path.getsize(full), full))
    files.sort()
    return files


def build(root: str, piece_length: int, trackers, comment: str, created_by: str, private: bool):
    files = collect(root)
    if not files:
        raise SystemExit("ERROR: ファイルがありません: %s" % root)
    total = sum(s for _, s, _ in files)
    pieces = bytearray()
    buf = b""
    for rel, size, full in files:
        with open(full, "rb") as f:
            while True:
                b = f.read(8 * 1024 * 1024)
                if not b:
                    break
                buf += b
                while len(buf) >= piece_length:
                    pieces += hashlib.sha1(buf[:piece_length]).digest()
                    buf = buf[piece_length:]
        print("  hashed: %s (%.2f GB cumulative)" % (rel, (total and size) / 1e9), file=sys.stderr) if False else None
    if buf:
        pieces += hashlib.sha1(buf).digest()

    info = {
        "name": os.path.basename(os.path.abspath(root)),
        "piece length": piece_length,
        "pieces": bytes(pieces),
        "files": [{"length": s, "path": rel.split("/")} for rel, s, _ in files],
    }
    if private:
        info["private"] = 1
    meta = {
        "info": info,
        "announce": (trackers[0] if trackers else "udp://tracker.opentrackr.org:1337/announce"),
        "creation date": int(time.time()),
        "created by": created_by,
        "comment": comment,
    }
    if len(trackers) > 1:
        meta["announce-list"] = [[t] for t in trackers]
    return meta, total, files


def main() -> int:
    ap = argparse.ArgumentParser(description="BitTorrent v1 .torrent 生成（純Python）")
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--piece-length-mib", type=int, default=16, help="ピース長（既定16MiB。大容量ほど大きめが効率的）")
    ap.add_argument("--tracker", action="append", default=[], help="トラッカー（複数可）")
    ap.add_argument("--comment", default="GLM-5.3 preservation archive")
    ap.add_argument("--created-by", default="GLM5.3-Collector-s-edition/make_torrent.py")
    ap.add_argument("--private", action="store_true", help="プライベート torrent にする")
    a = ap.parse_args()

    piece_length = max(16 * 1024, a.piece_length_mib * 1024 * 1024)
    meta, total, files = build(a.root, piece_length, a.tracker, a.comment, a.created_by, a.private)
    blob = bencode(meta)
    with open(a.out, "wb") as f:
        f.write(blob)
    info_hash = hashlib.sha1(bencode(meta["info"])).hexdigest()
    print("ファイル: %s (%d files, %.2f GB, piece=%d MiB)"
          % (a.out, len(files), total / 1e9, piece_length // 1024 // 1024))
    print("info-hash (v1): %s" % info_hash)
    print("magnet: ?xt=urn:btih:%s" % info_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())
