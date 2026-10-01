#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mirror_to_hf.py — 手元のアーカイブを「自分の Hugging Face リポジトリ」へミラーする。

これが最も現実的で安価な「永久化」手段である（無料・同インフラ・再開可能）。
ライセンス上も問題ない（GLM-5.3 License は再配布を許諾。MIT の Flash 系はなお自由）。

事前準備:
  export HF_TOKEN=hf_...        # write 権限のあるトークン
  huggingface-cli login         # でも可

使い方:
  python3 tools/mirror_to_hf.py --repo zai-org/GLM-5.3 --src ./archive --dest your-name/GLM-5.3-archive
  python3 tools/mirror_to_hf.py --src ./archive --dest your-name/GLM-5.3-archive --private
"""
from __future__ import annotations
import argparse, os, sys, time


def main() -> int:
    ap = argparse.ArgumentParser(description="HF へのミラー（公開アーカイブの作成）")
    ap.add_argument("--src", required=True, help="ミラーするローカルディレクトリ")
    ap.add_argument("--dest", required=True, help="作成/更新する HF リポジトリ（例: user/GLM-5.3-archive）")
    ap.add_argument("--repo", default=None, help="由来（upstream repo id）— README に記録される")
    ap.add_argument("--revision", default=None, help="由来リビジョン（manifest から自動補完）")
    ap.add_argument("--private", action="store_true", help="非公開リポジトリとして作成")
    ap.add_argument("--message", default=None, help="コミットメッセージ")
    a = ap.parse_args()

    try:
        from huggingface_hub import HfApi  # type: ignore
    except Exception:  # noqa: BLE001
        print("ERROR: huggingface_hub が必要です: pip install -U huggingface_hub", file=sys.stderr)
        return 2
    if not os.path.isdir(a.src):
        print("ERROR: --src が存在しません: %s" % a.src, file=sys.stderr)
        return 2

    api = HfApi()
    who = None
    try:
        who = api.whoami()
        print("ログイン中: %s" % who.get("name"))
    except Exception as e:  # noqa: BLE001
        print("ERROR: Hugging Face にログインできません（HF_TOKEN を設定してください）: %s" % e, file=sys.stderr)
        return 2

    print("リポジトリを作成/確認: %s (private=%s)" % (a.dest, a.private))
    api.create_repo(repo_id=a.dest, repo_type="model", private=a.private, exist_ok=True)

    # 来歴を README として同梱（MIT/GLM-5.3 License の「表示保持」条件を満たすため）
    readme = os.path.join(a.src, "MIRROR-README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "# Mirror of %s\n\n"
                "- upstream: https://huggingface.co/%s\n"
                "- upstream revision: %s\n"
                "- mirrored at: %s (UTC)\n"
                "- mirrored by: %s\n\n"
                "This is an unmodified mirror created for long-term preservation.\n"
                "License of the mirrored weights: see the LICENSE file in this repository\n"
                "(GLM-5.3 License for the 744B family, MIT for the Flash family).\n"
                "Integrity: use the manifests in GLM5.3-Collector-s-edition to verify SHA-256.\n"
                % (a.repo or "upstream", a.repo or "", a.revision or "(unspecified)",
                   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), who.get("name") if who else "?")
            )

    print("アップロード開始（既存ファイルはスキップされます）…")
    api.upload_large_folder(folder_path=a.src, repo_id=a.dest, repo_type="model") \
        if hasattr(api, "upload_large_folder") else \
        api.upload_folder(folder_path=a.src, repo_id=a.dest, repo_type="model",
                          commit_message=a.message or "mirror update")
    print("完了: https://huggingface.co/%s" % a.dest)
    print("検証: python3 tools/verify_archive.py --manifest manifests/%s.manifest.json --root %s"
          % ((a.repo or "zai-org__GLM-5.3").replace("/", "__"), a.src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
