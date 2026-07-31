#!/usr/bin/env python3
"""
fetch_corpus.py — Download CDLI tablets in bulk for the ATF pipeline.

CDLI publishes its ENTIRE corpus as a single ATF dump in the cdli-gh/data
GitHub repository (file: cdliatf_unblocked.atf, ~87 MB, stored with Git LFS).
This script pulls that dump — optionally filtering to just the tablets you
want — and writes a file that the atf_pipeline package / parse_tablet.py can
read directly.

The raw github URL only returns the LFS *pointer*; the real bytes live on
media.githubusercontent.com, which is what we use below.

Examples
--------
  # Download the full corpus (cached at data/cdli_export.txt)
  python3 fetch_corpus.py

  # Just one publication series
  python3 fetch_corpus.py --pub "AnOr 07" -o anor07.atf

  # A contiguous P-number range (inclusive)
  python3 fetch_corpus.py --range P101296-P102295 -o batch.atf

  # An explicit list of P-numbers (one per line, '#' comments allowed)
  python3 fetch_corpus.py --ids my_ids.txt -o batch.atf

Then run the pipeline on the result:
  python3 -m atf_pipeline anor07.atf
  python3 parse_tablet.py anor07.atf
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request
from typing import Callable, Iterable, Iterator, List, Optional, Set

CORPUS_URL = (
    "https://media.githubusercontent.com/media/"
    "cdli-gh/data/master/cdliatf_unblocked.atf"
)
DEFAULT_CACHE = os.path.join("data", "cdli_export.txt")

# &P101296 = AnOr 07, 001
_RE_HEADER = re.compile(r"^&(P\d+)\s*=\s*(.*)$")
_RE_PNUM   = re.compile(r"P(\d+)")


def _iter_lines(source: str, save_full: Optional[str] = None) -> Iterator[str]:
    """
    Yield text lines from a local file or the network URL.

    When streaming from the network and `save_full` is given, the raw bytes
    are also written to that path so the next run can work offline.
    """
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line.rstrip("\n")
        return

    # Network stream.
    req = urllib.request.Request(source, headers={"User-Agent": "sumer-fetch/1.0"})
    sink = None
    if save_full:
        os.makedirs(os.path.dirname(save_full) or ".", exist_ok=True)
        sink = open(save_full, "w", encoding="utf-8")
    seen_bytes = 0
    next_tick = 5 * 1024 * 1024
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            buf = ""
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                seen_bytes += len(chunk)
                if seen_bytes >= next_tick:
                    sys.stderr.write(f"\r  downloaded {seen_bytes // (1024*1024)} MB…")
                    sys.stderr.flush()
                    next_tick += 5 * 1024 * 1024
                text = chunk.decode("utf-8", errors="replace")
                if sink:
                    sink.write(text)
                buf += text
                lines = buf.split("\n")
                buf = lines.pop()          # keep the partial last line
                for line in lines:
                    yield line
            if buf:
                yield buf
        sys.stderr.write(f"\r  downloaded {seen_bytes // (1024*1024)} MB total.\n")
    finally:
        if sink:
            sink.close()


def _make_filter(args: argparse.Namespace) -> Callable[[str, str], bool]:
    """Build a predicate (pnum, designation) -> keep?  from the CLI args."""
    if args.pub:
        needle = args.pub.lower()
        return lambda pnum, desig: needle in desig.lower()

    if args.range:
        m = re.match(r"P?(\d+)\s*-\s*P?(\d+)$", args.range.strip())
        if not m:
            sys.exit(f"--range must look like P101296-P102295, got: {args.range!r}")
        lo, hi = int(m.group(1)), int(m.group(2))
        return lambda pnum, desig: lo <= int(pnum[1:]) <= hi

    if args.ids:
        wanted: Set[str] = set()
        with open(args.ids, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.split("#", 1)[0].strip()
                if not raw:
                    continue
                m = _RE_PNUM.search(raw)
                if m:
                    wanted.add("P" + m.group(1).zfill(6))
        if not wanted:
            sys.exit(f"No P-numbers found in {args.ids}")
        sys.stderr.write(f"  filtering to {len(wanted)} requested ID(s).\n")
        return lambda pnum, desig: pnum.zfill(7) in {w.zfill(7) for w in wanted} \
            or pnum in wanted

    return lambda pnum, desig: True   # no filter → keep everything


def fetch(args: argparse.Namespace) -> int:
    # Prefer a local cache of the full dump if present and we're filtering.
    source = CORPUS_URL
    save_full: Optional[str] = None
    if os.path.isfile(DEFAULT_CACHE):
        source = DEFAULT_CACHE
        sys.stderr.write(f"  using cached corpus: {DEFAULT_CACHE}\n")
    elif args.no_filter_requested:
        # Full download → cache it as we go.
        save_full = args.output or DEFAULT_CACHE
    else:
        # Filtering but no cache yet → stream and also save the full dump
        # so subsequent filtered runs are instant/offline.
        save_full = DEFAULT_CACHE

    keep = _make_filter(args)
    out_path = args.output or DEFAULT_CACHE

    # If we're doing a no-op full download straight to the cache path, the
    # streaming sink already wrote it — just drain the iterator.
    writing_subset = not (save_full and os.path.abspath(save_full) ==
                          os.path.abspath(out_path) and args.no_filter_requested)

    kept = 0
    total = 0
    out_fh = open(out_path, "w", encoding="utf-8") if writing_subset else None
    current_keep = False
    try:
        for line in _iter_lines(source, save_full=save_full):
            m = _RE_HEADER.match(line)
            if m:
                total += 1
                pnum, desig = m.group(1), m.group(2).strip()
                current_keep = keep(pnum, desig)
                if current_keep:
                    kept += 1
            if out_fh and current_keep:
                out_fh.write(line + "\n")
    finally:
        if out_fh:
            out_fh.close()

    if writing_subset:
        sys.stderr.write(
            f"  wrote {kept} tablet(s) (of {total} scanned) → {out_path}\n"
        )
    else:
        sys.stderr.write(f"  cached full corpus ({total} tablets) → {save_full}\n")
    return kept


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Download CDLI tablets in bulk for the ATF pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pub", help='publication series, e.g. "AnOr 07"')
    g.add_argument("--range", help="P-number range, e.g. P101296-P102295")
    g.add_argument("--ids", help="path to a file listing P-numbers (one per line)")
    ap.add_argument("-o", "--output", help="output path (default: data/cdli_export.txt)")
    args = ap.parse_args()
    args.no_filter_requested = not (args.pub or args.range or args.ids)

    n = fetch(args)
    if n == 0 and not args.no_filter_requested:
        sys.stderr.write(
            "  No tablets matched. Check the publication name / range / IDs.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
