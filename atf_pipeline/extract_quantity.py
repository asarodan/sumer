"""Quantity and commodity parsing: the sexagesimal grain system, animal
counts, silver weights, and commodity detection."""

import re
from typing import Optional, Tuple


class QuantityMixin:
    """Parse metrological quantities and detect the commodity of a line."""

    def _parse_grain(self, line: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse commodity quantity; return (value_in_native_unit, unit_name).

        Handles four quantity formats:
          1. Standard CDLI grain: N(asz/barig/ban2/sila3) → sila3
          2. Bare-gur context: N(u)/N(gesz2) sze gur → gur→sila3
          3. Bare-sila3 context: N(disz) sila3 → sila3  (small ration tablets)
          4. Bare-gin2 context: N(u)/N(disz) gin2 → gin2  (silver weight tablets)
          5. Animal count: N(disz) gu4/udu/… → head
        """
        # Strip per-person rate specifiers before summing the main quantity.
        # "7(asz) 2(barig) sze gur sila3 1(barig)-ta" → "7(asz) 2(barig) sze gur sila3"
        line = self._RE_RATE_SPEC.sub("", line).strip()
        # Strip ordinal phrases — "a-ra2 2(disz)-kam" embeds a count that is
        # an installment number, not a commodity amount.
        line = self._RE_ARA2_KAM.sub("", line).strip()
        cdli = self._RE_QTY_CDLI.findall(line)
        if cdli:
            # Strip CDLI sign-form modifiers (@c, @t, @v …) before unit lookup.
            # "1(asz@c)" and "1(asz)" both mean 1 gur.
            cdli = [(n, u.split("@")[0]) for n, u in cdli]
            units      = {u.lower() for _, u in cdli}
            bare_gur   = bool(self._RE_BARE_GUR.search(line))
            bare_sila3 = bool(self._RE_BARE_SILA3.search(line))
            bare_gin2  = bool(self._RE_BARE_GIN2.search(line))
            grain_ind  = bool(units & self._GRAIN_IND)
            if not grain_ind and not bare_gur and not bare_sila3 and not bare_gin2:
                # Not grain — check for animal count before giving up
                m_anim = self._RE_QTY_ANIMAL.search(line)
                if m_anim:
                    coeff_s, _unit = m_anim.group(1), m_anim.group(2)
                    if "/" in coeff_s:
                        n, d = coeff_s.split("/", 1)
                        return float(n) / float(d), "head"
                    return float(coeff_s), "head"
                return None, None
            total = 0.0
            first_unit = cdli[0][1].lower()
            for num_s, unit in cdli:
                ul = unit.lower()
                factor = self._GRAIN_CONV.get(ul)
                if factor is None:
                    if bare_gur and ul == "u":
                        factor = 10.0 * 300.0      # 10 gur per u-unit
                    elif bare_sila3 and ul == "u":
                        factor = 10.0              # 10 sila3
                    elif bare_sila3 and ul == "disz":
                        factor = 1.0               # 1 sila3
                    elif bare_gin2 and ul == "u":
                        factor = 10.0              # 10 gin2
                    elif bare_gin2 and ul == "disz":
                        factor = 1.0               # 1 gin2
                elif not grain_ind and not bare_gur and (bare_sila3 or bare_gin2):
                    # Bare sila3/gin2 context without grain-indicator sub-units
                    # means the sexagesimal counters are pure counts in those
                    # units (e.g. soup: "9(szar2)…sila3 tu7" = 9×3600 sila3;
                    # silver: "2(szar2)…gin2" = 2×3600 gin2).
                    # Use LABOR_CONV (szar2=3600, gesz'u=600, gesz2=60) instead
                    # of the gur-scaled GRAIN_CONV (szar2=1,080,000 sila3).
                    labor_f = self._LABOR_CONV.get(ul)
                    if labor_f is not None:
                        factor = labor_f
                if factor is None:
                    continue
                if "/" in num_s:
                    n, d = num_s.split("/", 1)
                    coeff = float(n) / float(d)
                else:
                    coeff = float(num_s)
                total += coeff * factor
            if bare_gin2:
                reported_unit = "gin2"   # silver weight — value is in gin2
            else:
                reported_unit = "sila3"  # all grain quantities stored in sila3
            return (total, reported_unit) if total > 0 else (None, None)

        # No CDLI tokens — try animal count or plain numeric formats
        m_anim = self._RE_QTY_ANIMAL.search(line)
        if m_anim:
            coeff_s = m_anim.group(1)
            if "/" in coeff_s:
                n, d = coeff_s.split("/", 1)
                return float(n) / float(d), "head"
            return float(coeff_s), "head"

        m = self._RE_QTY_PLAIN.search(line)
        if m:
            raw_val = float(m.group(1))
            raw_unit = m.group(2).lower()
            # Normalize plain-text grain units to sila3 so they're consistent
            # with CDLI-token path output ("5 gur" → 1500 sila3, "4 sila" → 4 sila3).
            conv = {"gur": 300.0, "barig": 60.0, "ban2": 10.0}
            if raw_unit in conv:
                return raw_val * conv[raw_unit], "sila3"
            if raw_unit == "sila":
                return raw_val, "sila3"
            return raw_val, raw_unit
        return None, None

    def extract_quantity(self, line: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse grain quantity; return (value_in_sila3, primary_unit).
        Non-grain lines (worker-days, animals, area) return (None, None).

        On mixed labor/grain lines ("N gurusz u4 N-sze3 N(asz) sze gur"),
        the labor prefix is stripped and grain is parsed from the remainder.
        """
        if self._RE_NON_GRAIN.search(line):
            return None, None
        if self._RE_LABOR_LINE.search(line):
            # Attempt grain extraction from the part after the labor token.
            parts = self._RE_LABOR_LINE.split(line, 1)
            if len(parts) > 1:
                # Drop the work-period clause "u4 N(unit)-sze3" before grain scan.
                remainder = re.sub(
                    r"\bu4\s+\d+\([^)]+\)(?:-sze3)?\b", "", parts[-1]
                )
                q, u = self._parse_grain(remainder)
                if q is not None:
                    return q, u
            return None, None
        return self._parse_grain(line)

    def _qty_from_u_sze(self, u_count: str) -> float:
        """N(u) sze → N×10 sila3 (small ration distribution format)."""
        return int(u_count) * 10.0

    def _extract_inline_qty_recipient(self, line: str) -> Optional[str]:
        """
        Extract a trailing personal name from a sze gub-ba distribution line.
        Format: "1(asz) 1(barig) gur ur-e2-mah" → "ur-e2-mah".
        Strips CDLI quantity tokens and commodity keywords; returns what
        remains if it looks like a personal name.
        """
        stripped = self._RE_QTY_CDLI.sub("", line)
        stripped = self._RE_COMM_KW.sub("", stripped)
        stripped = re.sub(r"[!?*#]", "", stripped)
        stripped = re.sub(r"\[.*?\]", "", stripped)
        stripped = stripped.strip()
        if not stripped or "(" in stripped or ")" in stripped:
            return None
        if self._looks_like_name(stripped):
            name = self._clean_atf_name(stripped)
            return name if name else None
        return None

    def _detect_commodity(self, line: str) -> Optional[str]:
        if self._RE_OP_DESC.search(line):  return None
        if self._RE_BARLEY.search(line):  return "barley"
        if self._RE_EMMER.search(line):   return "emmer"
        if self._RE_WHEAT.search(line):   return "wheat"
        if self._RE_DATES.search(line):   return "dates"
        if self._RE_FLOUR.search(line):   return "flour"
        if self._RE_BREAD.search(line):   return "bread"
        if self._RE_BEER.search(line):    return "beer"
        # "i3" standalone = oil/fat; "i3-nun" = ghee — but exclude verbal compounds
        # like i3-dab5 (received), i3-li2 (name), by requiring whitespace/end after
        if self._RE_OIL.search(line):     return "oil"
        if re.search(r"(?:^|\s)i3(?:-nun)?(?=\s|$)", line, re.I): return "oil"
        if self._RE_SILVER.search(line):  return "silver"
        if re.search(r"\bku3-sig17\b", line, re.I): return "gold"
        # guru7 = granary/grain-silo.  In multi-commodity granary accounts the
        # commodity word on a guru7 subtotal line is sometimes broken off, and
        # without an explicit fallback the entry inherits a stale pending
        # commodity (e.g. wheat from a line above), mislabelling a six-figure
        # barley total.  A granary defaults to barley, the staple it stores.
        # Checked LAST so any explicit ziz2/gig/etc. on the same line wins.
        if re.search(r"\bguru7\b", line, re.I): return "barley"
        # Animal commodity is inferred from unit=="head" returned by _parse_grain,
        # NOT from _detect_commodity, to avoid false positives on personal names.
        return None
