"""Corpus loading: CDLI bulk exports and per-tablet ATF files."""

import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


_RE_EXPORT_NOISE = re.compile(
    r"https?://cdli\.|Page\s+\d+\s+of\s+\d+|^\s*:\s*$", re.I
)
_RE_TABLET_HEADER = re.compile(r"^&(P\d+)\s*=")


def parse_cdli_export(text: str) -> Dict[str, List[str]]:
    """
    Parse a CDLI multi-tablet bulk export into {cdli_id: [atf_lines]}.
    Handles browser/PDF page headers and multi-tablet ATF dump files.
    """
    tablets: Dict[str, List[str]] = {}
    current_id: Optional[str] = None
    current_lines: List[str] = []

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            if current_id is not None:
                current_lines.append("")
            continue
        if _RE_EXPORT_NOISE.search(stripped):
            continue
        m = _RE_TABLET_HEADER.match(stripped)
        if m:
            if current_id and current_lines:
                tablets[current_id] = current_lines
            current_id = m.group(1)
            current_lines = [stripped]
        elif current_id is not None:
            current_lines.append(stripped)

    if current_id and current_lines:
        tablets[current_id] = current_lines

    logger.info("Parsed %d tablets from CDLI export text.", len(tablets))
    return tablets


def load_cdli_export_file(filepath: str) -> Dict[str, List[str]]:
    """Load and parse a CDLI bulk ATF export text file."""
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                text = fh.read()
            result = parse_cdli_export(text)
            if result:
                logger.info(
                    "Loaded CDLI export: %s (%s, %d tablets)",
                    filepath, enc, len(result),
                )
                return result
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.error("Cannot open %s: %s", filepath, exc)
            return {}
    logger.warning("No working encoding found for %s.", filepath)
    return {}


def load_atf_file(filepath: str) -> List[str]:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                return [line.rstrip("\n") for line in fh]
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.error("Cannot open %s: %s", filepath, exc)
            return []
    return []


def load_corpus(directory: str) -> Dict[str, List[str]]:
    """Load all *.atf files from a directory."""
    if not os.path.isdir(directory):
        logger.error("Corpus directory not found: %s", directory)
        return {}
    corpus: Dict[str, List[str]] = {}
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".atf"):
            continue
        lines = load_atf_file(os.path.join(directory, filename))
        if lines:
            corpus[filename] = lines
    logger.info("Loaded %d ATF files from %s", len(corpus), directory)
    return corpus
