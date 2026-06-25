"""Issuer, recipient, and agent extraction from administrative formulae."""

import re
from typing import Optional, Tuple


class EntityMixin:
    """Pull the parties (issuer / recipient / responsible agent) from a line."""

    def _extract_issuer(self, clean: str) -> Optional[str]:
        """
        Try all issuer patterns (A–D) in order; return name or None.
        Pattern E (kiszib3) is a fallback applied outside this method.
        """
        # A: ki NAME-ta (ablative with suffix)
        m = self._RE_KI_TA.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1))
            if len(cand) >= 2:
                return cand

        # B: ki NAME (abbreviated ablative, no -ta) — strip any trailing debit
        # verb ("ki {d}iszkur-illat ba-zi") so it isn't glued onto the name.
        m = self._RE_KI_ONLY.match(clean)
        if m:
            raw = self._RE_ISSUER_TRAIL.sub("", m.group(1)).strip()
            cand = self._clean_atf_name(raw)
            # Reject known non-ablative ki compounds (threshing floor su7, geographic masz)
            if (len(cand) >= 2
                    and not cand.startswith(("su7", "masz", "en-gi"))
                    and "{ki}" not in cand):
                return cand

        # C: NAME ki at line end
        if not self._RE_KI_DET.search(clean):
            m2 = self._RE_KI_ABL.match(clean)
            if m2:
                cand = self._clean_atf_name(m2.group(1))
                # Reject if candidate contains CDLI quantity tokens like 3(asz)
                if (len(cand) >= 2
                        and not cand.startswith(("$", "#"))
                        and not re.search(r"\d+\(", cand)):
                    return cand

        # D: institution name + -ta (without ki prefix)
        m3 = self._RE_INST_ABL.match(clean)
        if m3:
            cand = self._clean_atf_name(m3.group(1))
            if len(cand) >= 2:
                return cand

        return None

    def _extract_recipient_inline(self, clean: str) -> Optional[str]:
        """Pattern F: NAME szu ba-ti on same line."""
        m = self._RE_SHU_BATI.match(clean)
        if m:
            r = self._clean_atf_name(m.group(1))
            r = re.sub(r"-ra$", "", r).strip()
            if self._looks_like_name(r):
                return r
        return None

    def _extract_recipient_idab5(self, clean: str) -> Optional[str]:
        """Pattern H: NAME i3-dab5."""
        m = self._RE_IDAB5.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1).strip())
            # Strip trailing giri3 / sukkal clauses
            cand = re.sub(r"\s+giri3.*$", "", cand).strip()
            if self._looks_like_name(cand):
                return cand
        return None

    def _extract_recipient_u_sze(
        self, clean: str
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Pattern I: N(u) sze NAME — ration distribution.
        Returns (recipient_name, quantity_sila3) or (None, None).
        Rejects matches where the 'name' is actually a grain unit word
        (e.g. '5(u) sze gur' = 50 gur of barley, not a ration to 'gur').
        """
        m = self._RE_U_SZE.match(clean)
        if m:
            qty = self._qty_from_u_sze(m.group(1))
            name = self._clean_atf_name(m.group(2))
            # Also reject "gur lugal", "barig nig2-gal2-la", etc. where the
            # first word is a unit noun qualifying the measurement standard.
            first_word = name.lower().split()[0] if name else ""
            if (len(name) >= 2
                    and name.lower() not in self._GRAIN_UNIT_WORDS
                    and first_word not in self._GRAIN_UNIT_WORDS
                    and self._looks_like_name(name)):
                return name, qty
        return None, None

    def extract_patronymics(self, lines) -> list:
        """
        Scan a tablet's lines for "NAME dumu FATHER" parentage statements.

        Returns a list of (name, father) pairs in cleaned ATF form. These let a
        shared name be split into distinct individuals: two people both called
        lu2-szara2 are distinguishable when one is "dumu ur-nigar" and the other
        "dumu lugal-ezem". Status descriptors (dumu lugal = prince, dumu eridu =
        citizen-of) are filtered out.
        """
        pairs = []
        for raw in lines:
            s = raw.strip()
            if not s or s[0] in "&#@$":
                continue
            clean = self._strip_linenum(s)
            for m in self._RE_PATRONYM.finditer(clean):
                name   = self._clean_atf_name(m.group(1))
                father = self._clean_atf_name(m.group(2))
                if (len(name) >= 2 and len(father) >= 2
                        and name[:1].isalpha() and father[:1].isalpha()
                        and father.lower() not in self._PATRONYM_STOP
                        and self._looks_like_name(name)
                        and self._looks_like_name(father)):
                    pairs.append((name, father))
        return pairs

    def _extract_agent(self, clean: str) -> Optional[str]:
        """Pattern L: giri3 NAME or ugula NAME."""
        for pat in (self._RE_GIRI3, self._RE_UGULA):
            m = pat.match(clean)
            if m:
                cand = self._clean_atf_name(m.group(1).strip())
                cand = re.sub(
                    r"\s+(?:dub-sar|sukkal|szagina|ensi2|szabra|ugula"
                    r"|nu-banda3|dumu\s+lugal|lu2\s+kin-gi4-a)\s*$", "", cand
                ).strip()
                if len(cand) >= 2:
                    return cand
        return None
