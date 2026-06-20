"""Date parsing: month, day, and king/year resolution from ``mu`` year-names."""

from typing import List, Optional, Tuple

from atf_pipeline.chronology import KING_YEAR_MAP
from atf_pipeline.models import UrIIIDate


class DateMixin:
    """Resolve ``iti``/``u4``/``mu`` lines into a :class:`UrIIIDate`."""

    def _resolve_king_year(self, year_str: str, date: "UrIIIDate") -> None:
        lower = year_str.lower()
        for key, (canonical, frags) in KING_YEAR_MAP.items():
            if key in lower:
                date.king = canonical
                for yr_num, fragments in frags.items():
                    if all(frag.lower() in lower for frag in fragments):
                        date.year_number = yr_num
                        break
                return
        if self._default_king:
            date.king = self._default_king
            for key, (canonical, frags) in KING_YEAR_MAP.items():
                if canonical != self._default_king:
                    continue
                for yr_num, fragments in frags.items():
                    if all(frag.lower() in lower for frag in fragments):
                        date.year_number = yr_num
                        return

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
