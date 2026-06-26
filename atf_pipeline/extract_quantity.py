"""Quantity and commodity parsing: the sexagesimal grain system, animal
counts, silver weights, and commodity detection."""

import re
from typing import Optional, Tuple


class QuantityMixin:
    """Parse metrological quantities and detect the commodity of a line."""

    _RE_LA2_MINUS = re.compile(r"\bla2\b(?!-ia3)", re.I)

    def _parse_grain(
        self, line: str, context_gur: bool = False
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse commodity quantity; return (value_in_native_unit, unit_name).

        Handles four quantity formats:
          1. Standard CDLI grain: N(asz/barig/ban2/sila3) → sila3
          2. Bare-gur context: N(u)/N(gesz2) sze gur → gur→sila3
          3. Bare-sila3 context: N(disz) sila3 → sila3  (small ration tablets)
          4. Bare-gin2 context: N(u)/N(disz) gin2 → gin2  (silver weight tablets)
          5. Animal count: N(disz) gu4/udu/… → head

        When context_gur=True (caller knows we are inside a grain-distribution
        section), lines containing ONLY large-sexagesimal tokens (gesz2, gesz'u,
        szar2, u, disz) without a bare sila3/gin2 context word are treated as
        gur-scale grain amounts.  This recovers entries like
        "4(gesz2) du-ug-ga" or "1(gesz'u) 2(gesz2) szu-{d}utu" in grain-ration
        tablets where each line's unit is implied by section context.

        The Sumerian subtraction operator "la2" ("lacking") is handled by parsing
        the portion before la2 as a positive quantity and the portion after as a
        negative quantity, then returning their difference.
        """
        # Strip per-person rate specifiers before summing the main quantity.
        # "7(asz) 2(barig) sze gur sila3 1(barig)-ta" → "7(asz) 2(barig) sze gur sila3"
        line = self._RE_RATE_SPEC.sub("", line).strip()
        # Strip ordinal phrases — "a-ra2 2(disz)-kam" embeds a count that is
        # an installment number, not a commodity amount.
        line = self._RE_ARA2_KAM.sub("", line).strip()
        # Handle la2 ("minus"/"lacking") subtraction operator.
        # "3(gesz2) 5(u) la2 1(asz) gur" = (180+50-1) gur, NOT 231 gur.
        # We parse the positive tokens (before la2) and negative tokens (after
        # la2) separately, then subtract.  Unit-context words (sze, gur, gin2)
        # that follow the subtrahend are appended to BOTH halves so that the
        # unit is correctly resolved (e.g. bare "3(gesz2) 5(u)" needs "gur"
        # to know it's a gur-scale number).
        m_la2 = self._RE_LA2_MINUS.search(line)
        if m_la2:
            pos_part = line[:m_la2.start()].strip()
            neg_tail = line[m_la2.end():].strip()
            # Find the context suffix: everything after the last CDLI token in neg_tail.
            all_cdli_in_neg = list(self._RE_QTY_CDLI.finditer(neg_tail))
            if all_cdli_in_neg:
                last_tok_end = all_cdli_in_neg[-1].end()
                ctx_suffix = neg_tail[last_tok_end:].strip()
            else:
                ctx_suffix = neg_tail
            pos_line = (pos_part + " " + ctx_suffix).strip()
            neg_line = neg_tail
            q_pos, u_pos = self._parse_grain(pos_line, context_gur=context_gur)
            q_neg, u_neg = self._parse_grain(neg_line, context_gur=context_gur)
            if q_pos is not None and q_neg is not None and u_pos == u_neg:
                result = q_pos - q_neg
                return (result, u_pos) if result > 0 else (None, None)
            # If subtraction doesn't resolve cleanly, fall through to normal parse.
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
            # Context-gur: caller knows this section is a grain distribution.
            # Treat lines with ONLY large-sexagesimal tokens (gesz2, gesz'u,
            # szar2, u, disz) as gur-scale grain when no sila3/gin2 context
            # word is present (those would indicate beer/silver allotments that
            # happen to use the same counting units).
            _GUR_SCALE = {"gesz2", "gesz'u", "szar2", "szar'u", "szargal", "u", "disz"}
            if (context_gur and not grain_ind
                    and not bare_sila3 and not bare_gin2
                    and units and units <= _GUR_SCALE):
                # Guard: the remainder after stripping all quantity tokens must not
                # contain "[" (CDLI damaged-text bracket) — damaged text may hide a
                # commodity word (e.g. "8(szar2) [...]" could be reed bundles).
                # Also block when the remainder contains:
                #   - A CDLI determinative other than {d} (divine) or {ki} (place):
                #     {gesz}=wood, {u2}=plant/herb, {uruda}=copper, {kusz}=leather…
                #     These mark commodities, never personal names.
                #   - Worker terms (gurusz=male worker, geme2=female worker): lines
                #     like "N(gesz2) gurusz u4 N-sze3" count labor days, not grain.
                #     Lines with explicit grain indicators (sila3, ban2) still extract
                #     via the normal path (context_gur doesn't activate when bare_sila3
                #     is true).
                _remainder = self._RE_QTY_CDLI.sub("", line).strip()
                # Commodity determinatives: {gesz}=wood, {u2}=plant, {uruda}=copper…
                # block context_gur because they mark non-grain commodity words.
                # Exception: {d} divine and {ki} place appear in personal names.
                # Exception: a determinative preceded by "-" is embedded in a
                # hyphenated personal name compound (e.g. lugal-{gesz}gigir-re,
                # ur-{gesz}kiri6) not on a standalone commodity word.
                _has_det = bool(
                    re.search(r'(?<!-)\{(?!d\b|ki\b)[^}]+\}', _remainder, re.I)
                )
                _has_worker = bool(
                    re.search(r'\b(?:gurusz|geme2)\b', _remainder, re.I)
                )
                # ninda = bread loaf counts (e.g. "5(gesz2) ninda-bi" = N loaves,
                # not N gesz2 of grain).  Note: sa-bundle patterns (sa gi, sa szum2)
                # are already blocked by _RE_NON_GRAIN before _parse_grain is called.
                _has_bread = bool(
                    re.search(r'\bninda\b', _remainder, re.I)
                )
                # nig2 standalone (not hyphenated) = item/object count classifier
                # in artisan-accountability lines: "N(gesz2) nig2 PERSON" or
                # "N nig2 lu2-X" tallies manufactured items, never grain.
                # Hyphenated forms (nig2-dag, nig2-bi, nig2-gal2-la) are unaffected
                # because (?!-) blocks matches where nig2 is followed by a hyphen.
                _has_nig2 = bool(
                    re.search(r'\bnig2\b(?!-)', _remainder, re.I)
                )
                # szum2 standalone (not hyphenated) = garlic/onion commodity.
                # Garlic tablets measure in capacity units (barig, ban2, gesz2/u/disz)
                # identical to grain — but the content is garlic, not grain.
                # Verbal form "given" is always hyphenated (ba-szum2, mu-szum2),
                # so (?<!-) correctly exempts verb forms in grain delivery lines.
                # Lines with explicit bare gin2 (onion silver price) already bypass
                # the context_gur block (bare_gin2 is set → this block is skipped).
                _has_szum2 = bool(
                    re.search(r'(?<!-)\bszum2\b', _remainder, re.I)
                )
                # Large-denomination tokens (gesz2, gesz'u, szar2, …) without a
                # sub-gur anchor (asz/barig/ban2) are sila3-scale ration entries.
                # In individual ration lists, "3(gesz'u) 4(gesz2) worker-name"
                # means 2,063 sila3 (~7 gur), NOT 2,063 gur — the szunigin at the
                # bottom converts to gur.  Sub-gur tokens (asz = 1 gur, barig, ban2)
                # are already in _GRAIN_IND, so their presence sets grain_ind=True
                # above and this block is never reached.  If only gesz2+ appears
                # here, the line is NOT in gur scale; skip context_gur.
                _LARGE_DENOM = {"gesz2", "gesz'u", "szar2", "szar'u", "szargal"}
                _has_large_denom = bool(units & _LARGE_DENOM)
                if "[" not in _remainder and _remainder and not _has_det and not _has_worker and not _has_bread and not _has_nig2 and not _has_szum2 and not _has_large_denom:
                    grain_ind = True
                    bare_gur  = True   # activates the 10-gur-per-u factor
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

            # Mixed capacity + weight line, e.g.
            #   "5(disz) sila3 kasz 5(disz) gin2 szum2"  (5 sila3 beer + 5 shekels onion)
            # The gin2 tokens are a separate weight allotment: they must not be
            # summed into the grain total, nor flip the whole line's unit to gin2
            # (which mislabels the capacity commodity as a weight).  Bucket each
            # token by the unit word that follows it and keep only the capacity
            # (sila3-scale) portion.  Guarded to lines that genuinely mix the two
            # systems so pure-weight (silver/oil) and pure-grain lines are
            # untouched.
            if bare_gin2 and (grain_ind or bare_gur or bare_sila3):
                cap_total = 0.0
                matches = list(self._RE_QTY_CDLI.finditer(line))
                for i, mt in enumerate(matches):
                    ul = mt.group(2).split("@")[0].lower()
                    seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
                    ctx = line[mt.end():seg_end]
                    # Weight token: the first unit word after it is gin2 (and the
                    # token is not itself a grain-capacity unit like asz/barig).
                    gpos = ctx.find("gin2")
                    smatch = self._RE_BARE_SILA3.search(ctx)
                    spos = smatch.start() if smatch else -1
                    if (ul not in self._GRAIN_IND
                            and gpos != -1 and (spos == -1 or gpos < spos)):
                        continue
                    factor = self._GRAIN_CONV.get(ul)
                    if factor is None:
                        if bare_gur and ul == "u":
                            factor = 10.0 * 300.0
                        elif ul == "u":
                            factor = 10.0
                        elif ul == "disz":
                            factor = 1.0
                    if factor is None:
                        continue
                    num_s = mt.group(1)
                    if "/" in num_s:
                        n, d = num_s.split("/", 1)
                        coeff = float(n) / float(d)
                    else:
                        coeff = float(num_s)
                    cap_total += coeff * factor
                if cap_total > 0:
                    return cap_total, "sila3"
                # No capacity content resolved → fall through to the weight path.

            total = 0.0
            first_unit = cdli[0][1].lower()
            for num_s, unit in cdli:
                ul = unit.lower()
                factor = self._GRAIN_CONV.get(ul)
                if factor is None:
                    if (bare_gur or grain_ind) and ul == "u":
                        factor = 10.0 * 300.0      # 10 gur per u-unit (sexagesimal)
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

    def extract_quantity(
        self, line: str, context_gur: bool = False
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse grain quantity; return (value_in_sila3, primary_unit).
        Non-grain lines (worker-days, animals, area) return (None, None).

        On mixed labor/grain lines ("N gurusz u4 N-sze3 N(asz) sze gur"),
        the labor prefix is stripped and grain is parsed from the remainder.
        """
        # Strip scribal corrections (crossed-out text): <<deleted>> → ""
        line = self._RE_SCRIBAL_CORR.sub("", line).strip()
        # Field area + grain line: "N(esze3) N(iku) GAN2 N(asz) N(gur) FARMER"
        # In field-accounting tablets, the area measurement precedes GAN2 and
        # the grain allocation follows on the SAME line.  Strip the area+GAN2
        # prefix so _parse_grain can extract the grain portion.
        # Guard 1: left side must contain a known area unit (esze3/iku/bur3/
        #          bur'u/sar) or a damaged restoration bracket "[...]" to confirm
        #          GAN2 is functioning as the area-summary word, not a label.
        # Guard 2: right side must contain a CDLI grain token.
        # Guard 3: right side must NOT end with a -ta/-[ta rate suffix — those
        #          mark per-area rates (P100089 pattern), not absolute totals.
        # When the strip fires, bypass _RE_NON_GRAIN so that GAN2 inside a
        # personal name on the right side (e.g. "lugal-GAN2-re6") doesn't
        # re-block the already-validated grain content.
        _skip_non_grain = False
        _m_gan2 = re.search(r"\bGAN2[#!?\w-]*\s+", line, re.I)
        if _m_gan2:
            _gl = line[:_m_gan2.start()].strip()
            _gr = line[_m_gan2.end():]
            _left_has_area = bool(re.search(
                r"\b(?:esze3|iku|bur3|bur'u|sar)\b|\[\.+\]", _gl, re.I
            ))
            _right_has_grain = bool(re.search(
                r"\d+(?:/\d+)?\((?:asz|barig|ban2|gur|sila3|gesz2|szar2)\)",
                _gr, re.I,
            ))
            _right_has_ta = bool(re.search(r"-ta\b|\[ta\b", _gr, re.I))
            if _left_has_area and _right_has_grain and not _right_has_ta:
                line = _gr
                _skip_non_grain = True
        if not _skip_non_grain and self._RE_NON_GRAIN.search(line):
            return None, None
        # Accounting balance lines (deficit, surplus, carry-forward subtotals) represent
        # residuals already embedded in surrounding totals — do not sum them.
        if self._RE_BALANCE_LINE.search(line):
            return None, None
        # igi-N-gal2 = "1/N-th fraction" (rate/share notation) — the N(unit) inside
        # is a denominator, never a commodity quantity.  Strip before parsing so that
        # "igi-5(disz)-gal2-bi 5(asz) 4(barig) gur" gives 5 asz 4 barig, not 5+5 asz.
        line = re.sub(r"\bigi-\d+(?:/\d+)?\([^)]+\)-gal2(?:-bi)?\b", "", line).strip()
        # ku3-bi = "its silver [equivalent]" — always introduces a weight note,
        # never a grain capacity.  Truncate the line at ku3-bi so that
        # "N sila3 commodity ku3-bi M gin2" returns N sila3, not N + M-derived.
        # When the entire line is "ku3-bi …", stripping yields an empty string → None.
        m_ku3bi = re.search(r"\bku3-bi\b", line, re.I)
        if m_ku3bi:
            line = line[:m_ku3bi.start()].strip()
            if not line:
                return None, None
        # guru7 (granary) lines: "N guru7 QUANTITY gur" — the N before guru7 is
        # the granary count, not part of the grain quantity.  Strip the count and
        # the guru7 word, then parse only the grain portion that follows.
        m_guru7 = re.search(r"\bguru7\b", line, re.I)
        if m_guru7:
            line = line[m_guru7.end():].strip()
            if not line:
                return None, None
        # Animal ration lines: "N(szar2/gesz'u) ANIMAL RATE gur" — the large
        # sexagesimal count before the animal word is a head-count, not grain.
        # When bare_gur is set, GRAIN_CONV would inflate szar2 (×1,080,000) or
        # gesz'u (×180,000) massively.  Strip everything up to and including the
        # animal word so only the per-head rate is parsed.
        # Guard: require the animal word to be whitespace-bounded (not part of a
        # hyphenated compound personal name like "{d}nanna-masz-x").
        m_anim = re.search(
            r"(?:^|(?<=\s))(?:udu|gu4|ab2|sila4|masz2?|ansze)(?=\s|$)", line, re.I
        )
        if m_anim:
            prefix = line[: m_anim.start()]
            if re.search(r"\b(?:szar2|gesz'u|szar'u|szargal)\b", prefix, re.I):
                line = line[m_anim.end() :].strip()
                if not line:
                    return None, None
        # Strip day-count date expressions globally: "u4 N(unit) [N(unit)][-suffix]"
        # These trail dated grain delivery lines, e.g. "3(asz) sze gur u4 1(u) 7(disz)-kam".
        # Compound form (two tokens) encodes days 11–30; both tokens must be removed so
        # the bare N(u) / N(disz) tokens are not summed into the grain total.
        line = re.sub(
            r"\bu4\s+\d+(?:/\d+)?\([^)]+\)(?:\s+\d+(?:/\d+)?\([^)]+\))?(?:-(?:sze3|a|kam))?\b",
            "",
            line,
        ).strip()
        if not line:
            return None, None
        if self._RE_LABOR_LINE.search(line):
            # Attempt grain extraction from the part after the labor token.
            parts = self._RE_LABOR_LINE.split(line, 1)
            if len(parts) > 1:
                # Drop the work-period clause "u4 N(unit)[-sze3/-a/-kam]" before
                # grain scan.  The count token (N days) must not be summed into
                # grain.  Suffixes: -sze3 (terminative), -a (locative), -kam (ordinal).
                remainder = re.sub(
                    r"\bu4\s+\d+(?:/\d+)?\([^)]+\)(?:-(?:sze3|a|kam))?\b", "", parts[-1]
                )
                q, u = self._parse_grain(remainder, context_gur=context_gur)
                if q is not None:
                    return q, u
                # Grain may precede the labor keyword: "N sze-ba gurusz NAME"
                # (ration-to-workers lines where gurusz marks the recipient type).
                q2, u2 = self._parse_grain(parts[0].strip(), context_gur=context_gur)
                if q2 is not None:
                    return q2, u2
            return None, None
        return self._parse_grain(line, context_gur=context_gur)

    def _segment_allotments(self, line: str) -> list:
        """
        Split a line that packs several commodity allotments into one segment
        each, e.g.
            "5(disz) sila3 kasz 5(disz) sila3 ninda 5(disz) gin2 szum2"
        becomes three segments (beer / bread / onion), so capacity and weight
        goods are not summed into a single conflated total.

        A new allotment begins at a quantity token that follows a token already
        carrying a commodity word.  Lines with zero or one commodity return the
        original string unchanged, so single-commodity extraction is identical.
        """
        toks = line.split()
        bounds = []
        seen = False
        for i, t in enumerate(toks):
            if seen and self._RE_QTY_TOKEN.match(t):
                bounds.append(i)
                seen = False
            if self._detect_commodity(t):
                seen = True
        if not bounds:
            return [line]
        segs, prev = [], 0
        for b in bounds:
            segs.append(" ".join(toks[prev:b]))
            prev = b
        segs.append(" ".join(toks[prev:]))
        return segs

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
        # If what remains after stripping qty/unit tokens is itself a commodity
        # word (e.g. "i3-gesz", "dabin", "i3-szah2"), it is not a personal name.
        if self._detect_commodity(stripped):
            return None
        if self._looks_like_name(stripped):
            name = self._clean_atf_name(stripped)
            # Re-check the cleaned form: stripping can reveal commodity words
            # (e.g. "udu   -ta" → "udu" after stripping sze from sze-ta then -ta).
            if name and self._looks_like_name(name):
                return name
        return None

    def _detect_commodity(self, line: str) -> Optional[str]:
        if self._RE_OP_DESC.search(line):  return None
        # Silver/gold are tested before barley: on a precious-metal line
        # ("ku3-bi N gin2 M sze") the sze is the barleycorn weight sub-unit
        # (1/180 shekel), not the barley commodity, so barley must not win.
        if re.search(r"\bku3-sig17\b", line, re.I): return "gold"
        if self._RE_SILVER.search(line):  return "silver"
        if self._RE_MALT.search(line):    return "malt"
        if self._RE_BARLEY.search(line):
            # "sze" alongside a gin2/ma-na weight but no capacity unit is the
            # barleycorn weight sub-unit (1/180 shekel), not barley grain.
            # Such a line weighs metal: attribute it to the metal if named.
            if ((self._RE_BARE_GIN2.search(line) or re.search(r"\bma-na\b", line, re.I))
                    and not self._RE_BARE_SILA3.search(line)
                    and not self._RE_BARE_GUR.search(line)
                    and not re.search(r"\b(?:asz|barig|ban2)\b", line, re.I)):
                if re.search(r"\bku3\b|\bku3-", line, re.I): return "silver"
                if re.search(r"\buruda\b", line, re.I):      return "copper"
                return None
            return "barley"
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
