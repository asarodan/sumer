"""Date parsing: month, day, and king/year resolution from ``mu`` year-names."""

import re
from typing import List, Optional, Tuple

from atf_pipeline.chronology import KING_TABLES, KING_YEAR_MAP
from atf_pipeline.models import UrIIIDate


def _match_year(lower: str, entries) -> Optional[int]:
    """First entry whose fragments all appear in the string wins."""
    for yr_num, fragments in entries:
        if all(frag.lower() in lower for frag in fragments):
            return yr_num
    return None


# Accession years: the year-name is just "<king> lugal" with nothing after it
# but damage markers.  "us2-sa <king> lugal" ("year after <king became> king")
# names the second year.  A trailing "-e" (ergative) means the king is the
# *agent* of an event year, never an accession formula.
_RE_ACCESSION_TAIL = re.compile(r"\s+lugal(?P<rest>.*)$")
_TRAIL_JUNK = " \t[]#!?x."


def _accession_year(lower: str, king_key: str) -> Optional[int]:
    idx = lower.find(king_key)
    if idx < 0:
        return None
    m = _RE_ACCESSION_TAIL.match(lower[idx + len(king_key):])
    if not m:
        return None
    if m.group("rest").strip(_TRAIL_JUNK):
        return None
    return 2 if lower.lstrip().startswith("us2-sa") else 1


class DateMixin:
    """Resolve ``iti``/``u4``/``mu`` lines into a :class:`UrIIIDate`."""

    def _resolve_king_year(self, year_str: str, date: "UrIIIDate") -> None:
        lower = year_str.lower()

        # 1. Explicit king named in the year-name: use that king's table.
        for key, (canonical, entries) in KING_YEAR_MAP.items():
            if key in lower:
                if canonical != date.king:
                    # King is changing: year_number from the previous king must
                    # not bleed into this king's date record.
                    date.year_number = None
                date.king = canonical
                yr = _match_year(lower, entries)
                if yr is None:
                    # No event matched: a bare "<king> lugal" is the accession
                    # year, "us2-sa <king> lugal" the year after it.
                    yr = _accession_year(lower, key)
                if yr is not None:
                    date.year_number = yr
                return

        # 2. No king named (the common case): search every king's table and
        #    accept the match only if exactly one king's formulary fits.
        #    Formulas shared across reigns (e.g. "sza-asz-ru ba-hul" = Šulgi 42
        #    and Amar-Suen 6) match under several kings and stay unresolved.
        matched = [
            (canonical, yr)
            for canonical, entries in KING_TABLES
            if (yr := _match_year(lower, entries)) is not None
        ]
        if len(matched) == 1:
            canonical, yr = matched[0]
            if canonical != date.king:
                date.year_number = None
            date.king = canonical
            date.year_number = yr
            return

        # 3. Ambiguous or unrecognised year-name: fall back to the corpus
        #    default king (if any) without inventing a year number.
        if self._default_king and date.king is None:
            date.king = self._default_king

    def _parse_date(
        self, lines: List[str]
    ) -> Tuple[Optional["UrIIIDate"], Optional[str]]:
        date = UrIIIDate()
        raw_mu: Optional[str] = None
        for line in lines:
            clean = self._strip_linenum(line.strip())
            m = self._RE_ITI.match(clean)
            if m:
                date.month = m.group(1).strip()
                if m.group(2):
                    date.day = int(m.group(2))
            m_day = self._RE_U4.search(clean)
            if m_day and date.day is None and not self._RE_ITI.match(clean):
                date.day = int(m_day.group(1))
            m = self._RE_MU.match(clean)
            if m:
                year_str = m.group(1).strip()
                date.year_name = year_str
                raw_mu = year_str
                self._resolve_king_year(year_str, date)
        if date.king or date.month or date.year_name:
            return date, raw_mu
        return None, None
