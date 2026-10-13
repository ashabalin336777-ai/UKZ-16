#!/usr/bin/env python3
"""Download non-video docs/CSV from customer Drive folder (no full video dump)."""

from __future__ import annotations

import sys
from pathlib import Path

from gdown.download import _get_session, download
from gdown.download_folder import _GoogleDriveFile, _parse_embedded_folder_view

FOLDER = "1CndIUnFec3-94ke-wOEgbviMu2XkqzuL"
OUT = Path("data/customer_drive")
LOG = OUT / "_fetch_log.txt"

WANT_FOLDERS = {
    "03_индексы_CSV",
    "04_документы",
    "05_перечень_и_словарь",
    "07_материалы_проверки_HEALTH_ID",
    "08_новые_материалы_Drive",
    "09_НИР_кандидаты_Drive",
}
WANT_EXTS = {".md", ".csv", ".xlsx", ".xls", ".json", ".txt", ".pdf", ".docx", ".doc"}


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def is_doc(name: str) -> bool:
    return Path(name).suffix.lower() in WANT_EXTS


def dl_file(fid: str, fname: str, dest: Path) -> str | None:
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / fname
    if out.exists() and out.stat().st_size > 0:
        log(f"skip exists {out}")
        return str(out)
    log(f"DL {fname} -> {out}")
    return download(
        url=f"https://drive.google.com/uc?id={fid}",
        output=str(out),
        quiet=True,
        use_cookies=True,
    )


def walk_folder(sess, fid: str, folder_name: str, dest: Path, depth: int = 0) -> None:
    if depth > 8:
        return
    dest.mkdir(parents=True, exist_ok=True)
    _, kids = _parse_embedded_folder_view(sess=sess, folder_id=fid, verify=True, timeout=90)
    log(f"{'  ' * depth}[{folder_name}] kids={len(kids)}")
    for kid_id, kid_name, kid_type in kids:
        if kid_type == _GoogleDriveFile.TYPE_FOLDER:
            walk_folder(sess, kid_id, kid_name, dest / kid_name, depth + 1)
        elif is_doc(kid_name) or kid_type.startswith("application/vnd.google-apps."):
            try:
                dl_file(kid_id, kid_name, dest)
            except Exception as exc:  # noqa: BLE001
                log(f"FAIL {kid_name}: {exc}")


def main() -> int:
    if LOG.exists():
        LOG.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    sess, _ = _get_session(
        proxy=None,
        use_cookies=True,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
        ),
        cookies_file=None,
    )
    try:
        name, children = _parse_embedded_folder_view(
            sess=sess, folder_id=FOLDER, verify=True, timeout=90
        )
        log(f"ROOT={name!r} children={len(children)}")
        for cid, cname, ctype in children:
            log(f"  top: {cname} type={ctype} id={cid}")
            if ctype == _GoogleDriveFile.TYPE_FOLDER:
                if cname in WANT_FOLDERS:
                    walk_folder(sess, cid, cname, OUT / cname)
            elif is_doc(cname):
                try:
                    dl_file(cid, cname, OUT)
                except Exception as exc:  # noqa: BLE001
                    log(f"FAIL root {cname}: {exc}")
    finally:
        sess.close()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
