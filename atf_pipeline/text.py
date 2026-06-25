"""Generic ATF text helpers: line-number stripping, name cleaning, and the
"is this a personal name?" heuristic."""

import re
from typing import Optional

from atf_pipeline.patterns import ExtractorBase


class TextMixin:
    """Low-level string normalisation shared across all extraction passes."""

    # Scribal corrections in CDLI ATF: <<deleted text>> marks text the scribe
    # wrote and then crossed out.  It must be removed before quantity parsing
    # so that the original (wrong) tokens are not summed alongside the correction.
    _RE_SCRIBAL_CORR = re.compile(r"<<[^>]*>>")
    # CDLI ATF italic markup: _text_ marks Sumerian logograms in Akkadian context.
    # Strip the underscore delimiters but keep the textual content.
    _RE_ATF_ITALIC = re.compile(r"_")

    def _strip_linenum(self, line: str) -> str:
        line = self._RE_LINENUM.sub("", line).strip()
        line = self._RE_SCRIBAL_CORR.sub("", line).strip()
        return self._RE_ATF_ITALIC.sub("", line).strip()

    @staticmethod
    def _is_content(line: str) -> bool:
        s = line.strip()
        return bool(s) and s[0].isdigit()

    @staticmethod
    def _clean_atf_name(name: str) -> str:
        """Strip damage markers and trailing grammatical suffixes from a name."""
        name = re.sub(r"\(\$[^)]*\$\)", "", name)   # CDLI editorial markers ($...$)
        name = re.sub(r"\([A-Za-z][A-Za-z0-9\-]*\)", "", name)  # sign variant: ensi2(PA-TE), kas4(DU)
        # ATF editorial additions <word> — keep the content, strip the markers.
        # "<sza3>" in "nam-<sza3>-tam" means the scribe omitted the sign but the
        # reading is certain; we want "nam-sza3-tam", not "nam--tam".
        name = re.sub(r"<([^>]*)>", r"\1", name)
        name = re.sub(r"[!?*#]", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        name = re.sub(r"\[[^\]]*$", "", name)    # unclosed bracket at end of string
        # Strip all ATF determinatives ({d}, {gesz}, {ki}, {gar}, etc.) and
        # phonetic complements that appear inside or after sign readings.
        # Also handles unclosed braces ({gar without closing }) from damaged lines.
        name = re.sub(r"\{[^}]*\}", "", name)
        name = re.sub(r"\{[^}]*$", "", name)    # unclosed brace at end of string
        # Strip sign-form modifier suffixes (@g, @c, @t, @v, @n …) on sign names.
        # They encode alternative sign forms and are never part of personal names.
        name = re.sub(r"@[A-Za-z0-9]+", "", name)
        name = re.sub(r"\bx\b", "", name)            # ATF unknown-sign token
        # CDLI sign catalog references (REC344, KWU147, LAK123, etc.) are
        # sign-list numbers, not readable syllables — strip them from names.
        name = re.sub(r"\b[A-Z]{2,}[0-9]+\b", "", name)
        # Collapse multiple hyphens left when damaged brackets are stripped
        # e.g. "lugal-[gur8]-re" → bracket strip → "lugal--re" → "lugal-re"
        name = re.sub(r"-{2,}", "-", name)
        # A dangling hyphen before a space means the hyphenated segment was
        # stripped (e.g. "nam-sza3-[tam] ur" → "nam-sza3- ur").
        # Replace "hyphen + space" with just a space to rejoin cleanly.
        name = re.sub(r"-\s+", " ", name)
        name = re.sub(r"-ta\s*$", "", name)
        name = re.sub(r"-sze3\s*$", "", name)        # terminative suffix — never part of a stored name
        # Dangling hyphen left when a damaged bracket like "[ta]" is stripped:
        # "dub-sar-[ta]" → after bracket strip → "dub-sar-" → strip trailing "-"
        name = re.sub(r"-\s*$", "", name)
        # Strip Sumerian conjunction "and" at either end: "u3 NAME" or "NAME u3"
        name = re.sub(r"^u3\s+", "", name, flags=re.I)
        name = re.sub(r"\s+u3\s*$", "", name, flags=re.I)
        # Strip genealogy suffix: "NAME dumu FATHER" → "NAME"
        name = re.sub(r"\s+dumu(?:-munus)?\b.+$", "", name, flags=re.I)
        # Strip leading title when followed by space: "nu-banda3 NAME" → "NAME"
        name = ExtractorBase._RE_TITLE_PREFIX.sub("", name)
        # Strip trailing administrative title: "NAME nu-banda3" → "NAME"
        name = ExtractorBase._RE_TITLE_SUFFIX.sub("", name)
        return re.sub(r"\s+", " ", name).strip()

    def _looks_like_name(self, clean: str) -> bool:
        """Heuristic: does this look like a standalone personal name line?"""
        if self._RE_NOT_NAME.match(clean):
            return False
        # Damaged-bracket fragments like "[...]-mu" → after cleaning leave "-mu";
        # a real name always starts with a letter or determinative brace.
        if clean.startswith("-"):
            return False
        if re.search(r"\b(?:gur|barig|ban2|sila3|gin2|ninda)\b", clean):
            return False
        if re.search(r"\(\$", clean):      # CDLI editorial marker ($ blank space $)
            return False
        if len(clean) < 2 or len(clean) > 60:
            return False
        # Bare commodity/animal/material words cannot be standalone personal names.
        # Compound names containing these syllables (e.g. "udu-ni-ba") are safe —
        # the exact-match check only blocks the isolated word.
        if clean.lower() in self._GRAIN_UNIT_WORDS:
            return False
        # All-uppercase tokens are CDLI's notation for signs with uncertain reading
        # (e.g. KA, SZIM, LAM) — never personal names.
        first_word = clean.split()[0] if clean.split() else clean
        if first_word.isupper() and len(first_word) >= 2:
            return False
        return True
