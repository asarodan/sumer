"""Document-structure extraction: tablet classification, section splitting, and
the transaction / allocation / ration / labor record builders."""

import logging
import re
from typing import Dict, List, Optional, Tuple

from atf_pipeline.models import (
    RecordEntry,
    TabletRecord,
    TabletSummary,
    Transaction,
    UrIIIDate,
)

logger = logging.getLogger(__name__)


class StructureMixin:
    """Split tablets into sections and assemble structured records."""

    @classmethod
    def _classify_tablet(cls, lines: List[str]) -> str:
        """
        Classify a tablet by its primary administrative function.

        Types (in priority order):
          yield_ledger  — agricultural balance sheet (sze-bi + mu-kux + la2-ia3)
          account       — reconciliation document (nig2-ka9-ak / nig2-kas7-ak)
          labor         — day-labour tally (many gurusz/geme2 lines)
          allocation    — field-farmer account (many engar lines)
          receipt       — receipt of goods (szu ba-ti / in-ba-ti / ba-an-ti)
          expenditure   — disbursement record (ba-zi dominant, no receipt formula)
          transfer      — catch-all for bilateral transfers and unclassified documents
        """
        lines_text = " ".join(l.lower() for l in lines)

        # Yield-balance ledger: sze-bi + mu-kux + la2-ia3 together identify an
        # agricultural accounting balance sheet, not a flat transaction list.
        if "sze-bi" in lines_text and "mu-kux" in lines_text and "la2-ia3" in lines_text:
            return "yield_ledger"

        # Balanced account / audit document
        if re.search(r"\bnig2-ka9-ak\b|\bnig2-kas7-ak\b", lines_text):
            return "account"

        labor    = sum(1 for l in lines if cls._RE_LABOR_LINE.search(l))
        transfer = sum(1 for l in lines if cls._RE_TRANSFER_SIGNAL.search(l))
        engar    = sum(1 for l in lines if re.search(r"\bengar\b", l, re.I))

        if engar >= 2:
            return "allocation"
        if labor >= 3 and labor >= transfer * 2:
            return "labor"

        # Receipt vs. expenditure — determined by the closing administrative formula.
        has_receipt     = bool(re.search(
            r"\bszu\s+ba-ti\b|\bin-ba-ti\b|\bba-an-ti\b", lines_text))
        has_expenditure = bool(re.search(r"\bba-zi\b", lines_text))

        if has_receipt and not has_expenditure:
            return "receipt"
        if has_expenditure and not has_receipt:
            return "expenditure"

        return "transfer"

    @staticmethod
    def _strip_secondary_sections(lines: List[str]) -> List[str]:
        """
        Remove @envelope and @seal sections from a tablet's lines.

        Ur III tablets often have an outer clay envelope (@envelope) with the
        same text as the inner tablet, and @seal sign-list sections.  Parsing
        these would double-count quantities.  Only @tablet is the primary body;
        @envelope and @seal are secondary and are stripped until the next
        top-level @tablet marker (or end of tablet).
        """
        _TOP_LEVEL = re.compile(r"^@(tablet|envelope|seal)\b", re.I)
        _SECONDARY = re.compile(r"^@(envelope|seal)\b", re.I)
        result: List[str] = []
        skip = False
        for line in lines:
            s = line.strip()
            if _TOP_LEVEL.match(s):
                skip = bool(_SECONDARY.match(s))
            if not skip:
                result.append(line)
        return result

    # "szunigin2 sze-bi N(asz) guru7" — the combined barley-equivalent total
    # has no inline grain quantity; it appears on the very next line.
    _RE_SZUNIGIN_SZE_BI_GURU7 = re.compile(
        r"^\d+[a-z]?[!?*'ʼ]?\.\s*\[?(?:szunigin2?|szu-nigin2?)\b.*\bsze-bi\b.*\bguru7\b",
        re.I,
    )

    def _split_sections(self, lines: List[str]) -> List[List[str]]:
        """Split tablet into sections at szunigin total lines only."""
        sections: List[List[str]] = []
        current: List[str] = []
        absorb_next = False  # pull continuation line into current section
        for line in lines:
            stripped = line.strip()
            if absorb_next:
                # This line is the quantity continuation of a two-line szunigin;
                # keep it in the current section so _extract_single_tx can filter it.
                current.append(line)
                absorb_next = False
                continue
            if self._RE_SZUNIGIN.match(stripped):
                current.append(line)
                # Two-line szunigin: "szunigin2 sze-bi N(asz) guru7" with the
                # grain total on the next line — include that line in this section.
                if self._RE_SZUNIGIN_SZE_BI_GURU7.match(stripped):
                    szu_clean = self._strip_linenum(stripped)
                    q_szu, u_szu = self.extract_quantity(szu_clean)
                    if q_szu is None or u_szu != "sila3":
                        absorb_next = True
                        continue  # don't close section yet; next line goes here too
                sections.append(current)
                current = []
            else:
                current.append(line)
        if current:
            sections.append(current)
        return sections if sections else [lines]

    def _split_sub_entries(self, content: List[str]) -> List[List[str]]:
        """
        Split a multi-issuer section's content lines into per-sub-entry chunks.

        Each chunk contains the lines that belong to one (quantity, ki NAME-ta)
        pair.  The szunigin closing-total line is excluded because its quantity
        would otherwise trigger a spurious new chunk.
        """
        filtered = [
            l for l in content
            if not self._RE_SZUNIGIN.match(l.strip())
        ]
        chunks: List[List[str]] = []
        current: List[str] = []
        has_qty    = False
        has_issuer = False
        for line in filtered:
            clean = self._strip_linenum(line)
            q, _  = self.extract_quantity(clean)
            iss   = self._extract_issuer(clean)
            # When current chunk already has both qty AND issuer, a new qty or
            # issuer signals the start of the next sub-entry — flush first.
            if has_qty and has_issuer and (q is not None or iss):
                chunks.append(current)
                current    = []
                has_qty    = False
                has_issuer = False
            current.append(line)
            if q is not None:
                has_qty    = True
            if iss:
                has_issuer = True
        if current:
            chunks.append(current)
        return chunks

    def _extract_from_section(
        self, section: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Extract bilateral transactions from a section.

        Returns a list because a section may contain multiple ki NAME-ta
        sub-entries (e.g. three separate receipts under one szunigin total).
        Each sub-entry produces its own Transaction instead of the first one
        swallowing the whole section.
        """
        content = [l.strip() for l in section if self._is_content(l.strip())]
        if not content:
            return []
        # Count only personal ki NAME-ta issuers (patterns A-B), not
        # institutional ablatives like "a-sza3 X-ta" or "e2-X-ta" which
        # describe the source location but coexist with a personal ki-ta
        # in the same sub-entry — counting them would falsely trigger the
        # multi-entry split and tear apart a single transaction.
        n_issuers = sum(
            1 for l in content
            if self._RE_KI_TA.match(self._strip_linenum(l))
            or self._RE_KI_ONLY.match(self._strip_linenum(l))
        )
        if n_issuers > 1:
            chunks = self._split_sub_entries(content)
            date, raw_mu = self._parse_date(section)
            results: List[Transaction] = []
            for chunk in chunks:
                for tx in self._extract_single_tx(chunk, tablet_id):
                    if tx.date is None and date is not None:
                        tx.date     = date
                        tx.raw_date = raw_mu
                    results.append(tx)
            return results
        return self._extract_single_tx(section, tablet_id)

    def _extract_single_tx(
        self, section: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Extract transactions from a single-issuer section.

        Collects every quantity line as a separate entry so that a section
        with barley on line 1 and dabin on line 2 (same issuer/recipient)
        produces two transactions instead of discarding the second commodity.
        The szunigin closing-total line is skipped — its quantity is the sum
        of the individual lines above, not an additional movement.
        """
        issuer:           Optional[str]   = None
        recipient:        Optional[str]   = None
        agent:             Optional[str]   = None
        pending_dative:    Optional[str]   = None
        prev_name:         Optional[str]   = None
        kiszib_name:       Optional[str]   = None
        first_linenum:     Optional[str]   = None
        pending_commodity: Optional[str]   = None
        # Personal ki NAME-ta issuer (patterns A-B) takes priority over
        # institutional ablatives (e2-X-ta, a-sza3 X-ta — pattern D) which
        # describe the source location rather than the responsible person.
        personal_issuer:   Optional[str]   = None
        any_issuer:        Optional[str]   = None
        # Each element: (quantity, unit, commodity_at_that_line)
        qty_entries: List[Tuple[float, str, Optional[str]]] = []
        # sza3-bi-ta ("from the subtotal / carry-forward") is a two-line
        # pattern: the label appears on one line, the actual balance amount
        # on the next.  Suppress the amount that follows the header.
        skip_carryforward = False
        # "szunigin2 sze-bi N(asz) guru7" with no inline grain quantity:
        # the combined barley-equivalent total is on the next line.  Suppress
        # that continuation line to avoid counting the grand total twice.
        skip_szunigin_continuation = False
        # sag-nig2-gur11-ra-kam ("it is the opening/income balance") marks
        # the boundary between the income section (already counted) and the
        # expenditure section that follows.  Entries after this label are
        # distributions of the received grain, NOT new inbound deliveries —
        # counting them again would double the tablet's grain total.
        skip_income_balance = False
        # mu-kux(DU) / la2-ia3 su-ga pattern: in multi-supervisor accounts,
        # a grain quantity between "mu-kux(DU)" and "la2-ia3 su-ga" records
        # a deficit repayment from a previous period — not a new delivery.
        # Track the index into qty_entries where the mu-kux window opened
        # so we can delete those entries if la2-ia3 su-ga follows.
        after_mukux = False
        mukux_start_idx = 0

        content = [l.strip() for l in section if self._is_content(l.strip())]
        if not content:
            return []

        # Pre-scan: mark content-list indices whose grain quantities are the
        # immediate predecessor of a label-only "la2-ia3 …" line.  Such lines
        # record deficit labels (su-ga = repaid, kab2-du11-ga = assessed, etc.).
        # The preceding grain quantity is the deficit amount — not a new delivery.
        # Guard: if the la2-ia3 line itself carries an inline grain quantity the
        # inline IS the deficit; the predecessor is a valid transaction.
        _RE_LA2_PREFIX = re.compile(r"^\[?la2[#!?]*\]?-\[?ia3\b", re.I)
        la2_su_ga_suppress: set = set()
        for _i, _cline in enumerate(content):
            _cl = self._strip_linenum(_cline)
            if _RE_LA2_PREFIX.search(_cl):
                # If this la2-ia3 line has its own inline grain quantity, the
                # inline value IS the deficit — predecessor is valid, skip.
                _q_inline, _u_inline = self.extract_quantity(_cl)
                if _q_inline is not None and _u_inline == "sila3":
                    continue
                # Look backwards up to 3 lines for the first grain quantity.
                # Stop at mu-kux(DU) or another balance-line boundary.
                for _j in range(_i - 1, max(_i - 4, -1), -1):
                    _prev = self._strip_linenum(content[_j])
                    if re.search(r"\bmu-kux\b", _prev, re.I):
                        break
                    if self._RE_BALANCE_LINE.search(_prev):
                        break
                    _q, _u = self.extract_quantity(_prev)
                    if _q is not None and _u == "sila3":
                        la2_su_ga_suppress.add(_j)
                        break  # suppress only the immediate predecessor

        # Pre-scan: suppress all content lines that are breakdown allocations
        # following a bare "sag-nig2-gur11-ra" (opening balance, no -kam) +
        # "sza3-bi-ta" (carry-forward) pair.  Those lines distribute the
        # opening balance across individual workers/fields — they are NOT new
        # inbound transactions.  We scan the full section (including @column /
        # @reverse markers, which are invisible in 'content') so that suppression
        # stops at the next column or face boundary rather than bleeding into
        # the rest of the tablet.
        _RE_SAG_BARE = re.compile(r"\bsag-nig2-gur11-ra\b", re.I)
        _RE_SZA3_BI_TA_START = re.compile(
            r"^\[?sza3[#!?]*-\[?bi[#!?]*-\[?ta[#!?\]]*\b", re.I)
        _RE_COL_BREAK = re.compile(r"^@(?:column|reverse|obverse)\b", re.I)
        sag_breakdown_suppress: set = set()
        _ci = 0          # tracks index in 'content'
        _in_bd = False   # currently inside a sag breakdown zone
        _prev_sag = False
        for _fl in section:
            _fs = _fl.strip()
            if _RE_COL_BREAK.match(_fs):
                _in_bd = False
                _prev_sag = False
                continue
            if not self._is_content(_fs):
                continue
            _fc = self._strip_linenum(_fs)
            if _RE_SAG_BARE.search(_fc) and not re.search(r"-kam\b", _fc, re.I):
                _prev_sag = True
            elif _prev_sag and _RE_SZA3_BI_TA_START.match(_fc):
                _in_bd = True
                _prev_sag = False
            else:
                _prev_sag = False
            if _in_bd:
                sag_breakdown_suppress.add(_ci)
            _ci += 1

        for idx, line in enumerate(content):
            # Szunigin total closes the section; its quantity is the sum of
            # the entries already collected — do not add it as a new entry.
            if self._RE_SZUNIGIN.match(line.strip()):
                # "szunigin2 sze-bi N(asz) guru7" — the combined barley-equivalent
                # grand total has no inline grain quantity; it is on the next line.
                szu_clean = self._strip_linenum(line.strip())
                if (re.search(r"\bsze-bi\b", szu_clean, re.I) and
                        re.search(r"\bguru7\b", szu_clean, re.I)):
                    q_szu, u_szu = self.extract_quantity(szu_clean)
                    if q_szu is None or u_szu != "sila3":
                        skip_szunigin_continuation = True
                continue

            clean = self._strip_linenum(line)

            # "sze-bi N(unit) gur" = "its barley equivalent: N gur" — an
            # accounting note recording the grain value of a processed product.
            # It is derived from the entry above, not a second commodity movement.
            if self._RE_SZE_BI.match(clean):
                continue

            # Pre-scanned la2-ia3 deficit-label predecessor: skip without extracting.
            if idx in la2_su_ga_suppress:
                continue

            # Pre-scanned sag-nig2-gur11-ra (bare) + sza3-bi-ta breakdown: skip.
            if idx in sag_breakdown_suppress:
                continue

            if first_linenum is None:
                m = re.match(r"(\d+[a-z]?[!?*'ʼ]?)\.", line)
                if m:
                    first_linenum = m.group(1)

            # mu-kux(DU) marks that preceding grain entries were delivered.
            # Amounts that follow it before la2-ia3 su-ga are deficit
            # repayments from a prior period, not new grain movements.
            # The pre-scan above handles most cases; this state-machine
            # catches the rare compound pattern where multiple quantities
            # appear between mu-kux and la2-ia3 su-ga.
            if re.search(r"\bmu-kux\(", clean, re.I):
                after_mukux = True
                mukux_start_idx = len(qty_entries)
                continue

            # Commodity detection — update pending so it can carry to the
            # next quantity line when the commodity and quantity are on
            # adjacent lines rather than the same line.
            # Reset pending at structural section-dividers (GAN2-gu4, i3-dub,
            # e2-duru5, ki-su7, a-sza3, etc.) that separate sub-accounts: the
            # commodity from the previous sub-account must not bleed into the
            # next one (e.g. a "gig" entry before "GAN2-gu4 / N gur" would
            # otherwise mislabel the following barley amount as wheat).
            c = self._detect_commodity(clean)
            if c:
                # Precious metals are never measured in sila3; carrying gold/
                # silver forward as pending_commodity would mislabel subsequent
                # grain entries (sila3/gur) in the same section.  Only carry
                # forward agricultural commodities.
                if c not in ("gold", "silver"):
                    pending_commodity = c
            elif self._RE_SECTION_LABEL.search(clean):
                pending_commodity = None

            # Quantity: a single ATF line can pack several allotments
            # ("5 sila3 beer 5 gin2 onion"); split them so capacity and weight
            # goods become separate entries rather than one conflated total.
            # Single-commodity lines return one segment and behave as before.
            # Check balance filter on the full line first: _segment_allotments can
            # strip a leading keyword (e.g. "sza3 sze") that the per-segment call
            # to extract_quantity would no longer see, allowing the trailing
            # quantity to leak through the filter.
            # sag-nig2-gur11-ra-kam marks the end of the income section; all
            # grain quantities from here onward in this section are expenditure
            # distributions, not new inbound deliveries.
            if re.search(r"\bsag-nig2-gur11-ra[#!?]*-kam[#!?]*\b", clean, re.I):
                skip_income_balance = True
                continue
            if self._RE_BALANCE_LINE.search(clean):
                # la2-ia3 su-ga after mu-kux: delete post-mukux deficit
                # repayment quantities that were tentatively collected.
                if after_mukux and re.search(r"\bla2-ia3\b", clean, re.I) and "su-ga" in clean:
                    del qty_entries[mukux_start_idx:]
                after_mukux = False
                # sza3-bi-ta: when the carry-forward amount appears on the
                # NEXT line (bare label only), flag it.  When the amount is
                # inline ("sza3-bi-ta N gur"), the carry-forward is already
                # suppressed by the continue below — don't set the flag or
                # the following legitimate quantity would be skipped too.
                # Strip the prefix before calling extract_quantity because
                # the parser can't read a quantity that starts with "sza3-bi-ta".
                if re.match(r"^\[?sza3[#!?]*-\[?bi[#!?]*-\[?ta[#!?\]]*\b", clean, re.I):
                    _rest = re.sub(
                        r"^\[?sza3[#!?]*-\[?bi[#!?]*-\[?ta[#!?\]]*\s*", "", clean, flags=re.I)
                    _cf_q, _cf_u = self.extract_quantity(_rest)
                    if _cf_q is None or _cf_u != "sila3":
                        skip_carryforward = True
                continue
            segs = self._segment_allotments(clean)
            for seg in segs:
                q, u = self.extract_quantity(seg)
                if q is None:
                    continue
                # After sag-nig2-gur11-ra-kam: all entries are expenditure
                # distributions — skip them to avoid double-counting the income.
                if skip_income_balance and u == "sila3":
                    continue
                # Only consume skip_carryforward on an actual grain quantity so
                # that no-qty content lines (like "5(disz) [...]") don't absorb
                # the flag prematurely before the real carry-forward amount.
                if skip_carryforward and u == "sila3":
                    skip_carryforward = False
                    continue  # suppress this carry-forward grain quantity
                # "szunigin2 sze-bi N guru7 / NAME AMOUNT sze gur" — the amount
                # on the continuation line is a grand total, not a new entry.
                if skip_szunigin_continuation and u == "sila3":
                    skip_szunigin_continuation = False
                    continue
                seg_c = self._detect_commodity(seg) if len(segs) > 1 else c
                this_comm = seg_c or pending_commodity
                # Precious metals are never measured in sila3/gur; if a gold or
                # silver commodity is assigned to a grain quantity it came from a
                # year-name or nearby metal-accounting line — clear the label.
                if this_comm in ("gold", "silver") and u == "sila3":
                    this_comm = None
                if u == "head" and this_comm is None:
                    this_comm = "animal"
                qty_entries.append((q, u, this_comm))

            # Pattern E candidate: kiszib3 NAME (save for fallback)
            m_kiszib = self._RE_KISZIB.match(clean) or self._RE_KISZIB_INLINE.search(clean)
            if m_kiszib and kiszib_name is None:
                cand = self._clean_atf_name(m_kiszib.group(1))
                if len(cand) >= 2 and cand.lower() not in self._GRAIN_UNIT_WORDS:
                    kiszib_name = cand

            # Patterns A-D: issuer.
            # Personal ki NAME-ta (patterns A-B) overrides an earlier
            # institutional ablative (a-sza3 X-ta, e2-X-ta — pattern D)
            # because the personal signer is the accountable party.
            iss = self._extract_issuer(clean)
            if iss:
                is_personal = bool(
                    self._RE_KI_TA.match(clean) or self._RE_KI_ONLY.match(clean)
                )
                if is_personal and personal_issuer is None:
                    personal_issuer = iss
                if any_issuer is None:
                    any_issuer = iss
                continue

            # Agent (giri3 / ugula)
            ag = self._extract_agent(clean)
            if ag and agent is None:
                agent = ag

            # Pattern F: inline NAME szu ba-ti
            rec = self._extract_recipient_inline(clean)
            if rec and recipient is None:
                recipient = rec
                prev_name = None
                pending_dative = None
                continue

            # Pattern G: standalone szu ba-ti
            if self._RE_SHU_ALONE.match(clean) and recipient is None:
                recipient = prev_name or pending_dative
                prev_name = None
                pending_dative = None
                continue

            # Pattern H: NAME i3-dab5
            rec_h = self._extract_recipient_idab5(clean)
            if rec_h and recipient is None:
                recipient = rec_h
                prev_name = None
                continue

            # Pattern I: N(u) sze NAME — inline ration
            rec_i, qty_i = self._extract_recipient_u_sze(clean)
            if rec_i and recipient is None:
                recipient = rec_i
                if qty_i is not None and not qty_entries:
                    qty_entries.append((qty_i, "sila3", pending_commodity or "barley"))
                prev_name = None
                continue

            # Pattern J: ba-an-szum2 with pending dative
            if self._RE_BA_AN_SUM.search(clean) and recipient is None:
                if pending_dative:
                    recipient = pending_dative
                    pending_dative = None
                continue

            # Pattern K2: sa2-du11 NAME — statutory payment
            m_sa2 = self._RE_SA2_DU11.match(clean)
            if m_sa2 and recipient is None:
                cand = self._clean_atf_name(m_sa2.group(1).strip())
                if (self._looks_like_name(cand)
                        and not cand.endswith("-ta")
                        and not cand.endswith("-ka-ta")):
                    recipient = cand

            # Track dative -ra for pattern J
            m_dat = self._RE_DATIVE_RA.match(clean)
            if m_dat and not rec and not iss:
                cand = self._clean_atf_name(m_dat.group(1).strip())
                if self._looks_like_name(cand):
                    pending_dative = cand

            # Track previous name-like line for pattern G
            if self._looks_like_name(clean):
                prev_name = self._clean_atf_name(clean)
            elif not (self._RE_SHU_ALONE.match(clean)
                      or self._RE_BA_AN_SUM.search(clean)
                      or m_dat
                      or self._RE_NOT_NAME.match(clean)):
                prev_name = None

        # Resolve issuer: personal ki-ta > any institutional > kiszib3 fallback
        issuer = personal_issuer or any_issuer
        if issuer is None and kiszib_name:
            issuer = kiszib_name

        if not qty_entries and issuer is None and recipient is None:
            return []

        date, raw_mu = self._parse_date(section)

        if not qty_entries:
            return [Transaction(
                tablet_id=tablet_id,
                issuer=issuer,
                recipient=recipient,
                agent=agent,
                date=date,
                raw_date=raw_mu,
                line_ref=first_linenum,
                tx_type="transfer",
            )]

        return [
            Transaction(
                tablet_id=tablet_id,
                issuer=issuer,
                recipient=recipient,
                agent=agent,
                quantity=q,
                unit=u,
                commodity=comm,
                date=date,
                raw_date=raw_mu,
                line_ref=first_linenum,
                tx_type="transfer",
            )
            for q, u, comm in qty_entries
        ]

    def _extract_allocations(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Extract field-allocation transactions (szabra→engar grain distributions).

        Handles the deferred-label structure where the szabra (estate admin) is
        announced AFTER the szunigin total(s) that close his group.  Tablets with
        multiple commodities (barley + emmer + wheat) produce multiple consecutive
        szunigin lines before a single szabra label; the look-ahead scans up to
        five groups forward to find it.

        Each (szabra, engar, qty, commodity) tuple becomes one Transaction row.
        """
        date, raw_mu = self._parse_date(lines)

        events: List[Tuple[str, object]] = []
        for line in lines:
            s = line.strip()
            if not self._is_content(s):
                continue
            clean = self._strip_linenum(s)

            # Use the raw stripped line (still has line number) for szunigin
            # detection — _RE_SZUNIGIN requires a leading digit.
            if self._RE_SZUNIGIN.match(s):
                events.append(("total", None))
                continue

            m_szabra = self._RE_SZABRA.match(clean)
            if m_szabra:
                name = self._clean_atf_name(m_szabra.group(1))
                if name:
                    events.append(("szabra", name))
                continue

            if re.search(r"\bengar\b", clean):
                q_inline, u_inline = self.extract_quantity(clean)
                comm_inline = self._detect_commodity(clean)
                m_engar = self._RE_ENGAR.match(clean)
                raw_name = m_engar.group(1) if m_engar else ""
                name = re.sub(
                    r"^(?:\d+(?:/\d+)?\(\w+[2']*\)\s*)+", "", raw_name
                ).strip()
                # Strip one or more bare unit/commodity words left at start after qty removal
                # (e.g. "ziz2 gur ur-NAME" → "ur-NAME" requires two passes worth of stripping)
                name = re.sub(
                    r"^(?:(?:sze|gur|ziz2|gig|barig|ban2|sila3?)\s+)+", "", name, flags=re.I
                ).strip()
                # Strip field annotation suffixes (GAN2 = area unit, a-sza3 = field)
                name = re.sub(r"\s+(?:GAN2|a-sza3)\b.*$", "", name, flags=re.I).strip()
                # Strip trailing commodity/unit words
                name = re.sub(r"\s*(?:sze|gur|ziz2|gig)\s*$", "", name).strip()
                name = self._clean_atf_name(name)
                events.append(("engar", (name, q_inline, u_inline, comm_inline)))
                continue

            q, u = self.extract_quantity(clean)
            if q is not None:
                comm = self._detect_commodity(clean)
                events.append(("qty", (q, u, comm)))

        if sum(1 for e in events if e[0] == "engar") < 2:
            return []

        # Split into groups at szunigin boundaries
        groups: List[List[Tuple[str, object]]] = []
        current: List[Tuple[str, object]] = []
        for event in events:
            if event[0] == "total":
                groups.append(current)
                current = []
            else:
                current.append(event)
        if current:
            groups.append(current)

        results: List[Transaction] = []

        for i, group in enumerate(groups):
            issuer: Optional[str] = None

            # Look ahead through up to 5 groups to find the deferred szabra.
            # Tablets with multiple commodities have N consecutive szunigin
            # lines before the single szabra that labels them all.
            for j in range(i + 1, min(i + 6, len(groups))):
                if groups[j] and groups[j][0][0] == "szabra":
                    issuer = groups[j][0][1]  # type: ignore[assignment]
                    break

            # Fallback: szabra within this group (leading-label structure)
            if not issuer:
                for etype, edata in group:
                    if etype == "szabra":
                        issuer = edata  # type: ignore[assignment]
                        break
            if not issuer:
                continue

            pending_qty:  Optional[float] = None
            pending_unit: Optional[str]  = None
            pending_comm: Optional[str]  = None

            for etype, edata in group:
                if etype == "szabra":
                    continue
                if etype == "qty":
                    pending_qty, pending_unit, pending_comm = edata  # type: ignore[misc]
                elif etype == "engar":
                    name, q_inline, u_inline, comm_inline = edata  # type: ignore[misc]
                    qty  = q_inline  if q_inline  is not None else pending_qty
                    unit = u_inline  if q_inline  is not None else pending_unit
                    comm = comm_inline or pending_comm or "barley"
                    if qty is not None and name and len(name) >= 2:
                        results.append(Transaction(
                            tablet_id=tablet_id,
                            issuer=issuer,
                            recipient=name,
                            quantity=qty,
                            unit=unit,
                            commodity=comm,
                            date=date,
                            raw_date=raw_mu,
                            tx_type="allocation",
                        ))
                    if q_inline is None:
                        pending_qty = None

        return results

    def _extract_ration_list(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Extract multi-recipient ration lists of the form:
            N(asz) NAME
            N(asz) NAME2
            ...
        where no 'engar' keyword appears (unlike allocation tablets).
        Each quantity-name pair becomes one transaction.
        """
        date, raw_mu = self._parse_date(lines)
        results: List[Transaction] = []
        pending_qty: Optional[float] = None
        pending_comm: Optional[str] = None

        for line in lines:
            s = line.strip()
            if not self._is_content(s):
                continue
            clean = self._strip_linenum(s)

            m = self._RE_ASZ_NAME.match(clean)
            if m:
                coeff_s, raw_name = m.group(1), m.group(2).strip()
                name = self._clean_atf_name(raw_name)
                if not self._looks_like_name(name):
                    continue
                coeff = float(coeff_s) if "/" not in coeff_s else (
                    lambda p: float(p[0]) / float(p[1])
                )(coeff_s.split("/", 1))
                qty = coeff * 300.0  # asz = 1 gur = 300 sila3
                comm = pending_comm or "barley"
                results.append(Transaction(
                    tablet_id=tablet_id,
                    recipient=name,
                    quantity=qty,
                    unit="sila3",
                    commodity=comm,
                    date=date,
                    raw_date=raw_mu,
                    tx_type="transfer",
                ))
                continue

            # Commodity line that precedes the ration entries
            comm = self._detect_commodity(clean)
            if comm:
                pending_comm = comm

        return results if len(results) >= 2 else []

    def _extract_labor_transactions(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Extract a single labor-summary transaction from labor/boat tablets.
        Looks for szunigin N gurusz (total worker count) or sums gurusz lines.
        Quantity is in worker-days (worker_count × day_count).
        """
        date, raw_mu = self._parse_date(lines)
        agent: Optional[str] = None
        total_workers = 0.0
        day_count = 1.0
        found_szunigin = False

        for line in lines:
            s = line.strip()
            if not self._is_content(s):
                continue
            clean = self._strip_linenum(s)

            # szunigin N gurusz = total worker count
            m_tot = self._RE_LABOR_TOTAL.search(s)
            if m_tot:
                qty_str = m_tot.group(1)
                # Parse using pure sexagesimal labor counter, not grain factors.
                w = sum(
                    (float(n.split("/")[0]) / float(n.split("/")[1]) if "/" in n else float(n)) * f
                    for n, u in self._RE_QTY_CDLI.findall(qty_str)
                    if (f := self._LABOR_CONV.get(u.split("@")[0].lower())) is not None
                )
                if w > 0:
                    total_workers = w
                    found_szunigin = True
                continue

            # u4 N-sze3 = number of days
            m_day = re.search(r"\bu4\s+(\d+(?:/\d+)?)\([^)]+\)-sze3\b", clean)
            if m_day and day_count == 1.0:
                day_s = m_day.group(1)
                if "/" in day_s:
                    n, d = day_s.split("/", 1)
                    day_count = float(n) / float(d)
                else:
                    day_count = float(day_s)

            # ugula NAME = supervising agent
            m_ug = self._RE_UGULA.match(clean)
            if m_ug and agent is None:
                agent = self._clean_atf_name(m_ug.group(1).strip())

            # Accumulate individual gurusz lines when no szunigin total.
            # Use the pure sexagesimal labor counter (gesz2=60, u=10, disz=1),
            # NOT _GRAIN_CONV, so "2(gesz2) 2(u) 4(disz)" → 144 workers, not 36,004.
            if not found_szunigin and self._RE_LABOR_LINE.search(clean):
                parts = self._RE_LABOR_LINE.split(clean, 1)
                worker_tokens = self._RE_QTY_CDLI.findall(parts[0])
                for num_s, unit in worker_tokens:
                    ul = unit.split("@")[0].lower()
                    factor = self._LABOR_CONV.get(ul)
                    if factor is None:
                        continue
                    total_workers += (
                        float(num_s.split("/")[0]) / float(num_s.split("/")[1])
                        if "/" in num_s else float(num_s)
                    ) * factor

        if total_workers <= 0:
            return []
        worker_days = total_workers * day_count
        return [Transaction(
            tablet_id=tablet_id,
            agent=agent,
            quantity=worker_days,
            unit="worker-day",
            commodity="labor",
            date=date,
            raw_date=raw_mu,
            tx_type="labor",
        )]

    def extract_transactions(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """Extract all transactions from a tablet's ATF lines."""
        lines = self._strip_secondary_sections(lines)
        results: List[Transaction] = []
        # Skip non-administrative texts: lexical lists, bilingual glossaries,
        # royal inscriptions, literary/metrological texts, and non-Sumerian
        # tablets — these use formats incompatible with the Ur III admin parser.
        for l in lines[:10]:
            s = l.strip()
            if re.match(r"#atf:\s+use\s+(lexical|bilingual|literary|emesal)", s, re.I):
                return []
            if re.match(r"#atf:\s+lang\s+(akk|ebl|sux-x-emesal|hit)\b", s, re.I):
                return []
        # Pre-Sargonic / Early Dynastic tablets use archaic curviform (@c) tokens
        # for large grain units (szar'u@c, szar2@c, gesz'u@c).  The @c suffix is
        # stripped during unit lookup, so these tokens are misread as Ur III
        # values 100–10,000× too large.  Bail out before extracting anything.
        # Guard: only check non-szunigin lines; szunigin totals with gesz'u@c are
        # already skipped during section extraction, so their large values never
        # accumulate.  Tablets where only the total uses gesz'u@c (individual
        # entries in gesz2@c, asz@c, ban2@c) can be safely extracted.
        _ARCHAIC_LARGE = re.compile(r"\((?:szar'u|szar2|gesz'u)@c\)", re.I)
        if any(_ARCHAIC_LARGE.search(l) for l in lines
               if not self._RE_SZUNIGIN.match(l.strip())):
            return []
        # Require at least one administrative keyword before attempting extraction.
        # Metrological tables and lexical lists have numbers but no admin vocabulary.
        _ADMIN_KW = re.compile(
            r"\bszu\s+ba-ti\b|\bba-zi\b|\bi3-dab5\b|\bki\s+\S+-ta\b"
            r"|\bszunigin\b|\bengar\b|\bszabra\b|\bmu\s+\S+-ma\b"
            r"|\bgiri3\b|\bba-an-szum2?\b|\bmu-kux\b",
            re.I,
        )
        if not any(_ADMIN_KW.search(l) for l in lines):
            return []
        tablet_type = self._classify_tablet(lines)

        # Allocation tablets: only run the allocation pass.
        # Running the bilateral pass on them produces ghost transactions from
        # szunigin total lines and double-counts individual engar entries.
        if tablet_type != "allocation":
            try:
                for section in self._split_sections(lines):
                    for tx in self._extract_from_section(section, tablet_id):
                        if tx.tx_type == "transfer":
                            tx.tx_type = tablet_type
                        results.append(tx)
            except Exception as exc:
                logger.warning("Error in transfer pass for %s: %s", tablet_id, exc)

        # Allocation pass (whole-tablet scan)
        try:
            alloc = self._extract_allocations(lines, tablet_id)
            results.extend(alloc)
        except Exception as exc:
            logger.warning("Error in allocation pass for %s: %s", tablet_id, exc)

        # Allocation tablets where _extract_allocations found nothing: fall back to the
        # bilateral section pass.  This recovers grain from engar tablets that have a
        # clear grain-then-farmer structure but lack a szabra (estate admin) header,
        # which is what _extract_allocations requires to match groups.
        if not results and tablet_type == "allocation":
            try:
                for section in self._split_sections(lines):
                    for tx in self._extract_from_section(section, tablet_id):
                        if tx.tx_type == "transfer":
                            tx.tx_type = "allocation"
                        results.append(tx)
            except Exception as exc:
                logger.warning("Error in bilateral fallback for %s: %s", tablet_id, exc)

        # If still empty, try ration list (N(asz) NAME without engar)
        if not results:
            try:
                rations = self._extract_ration_list(lines, tablet_id)
                results.extend(rations)
            except Exception as exc:
                logger.warning("Error in ration-list pass for %s: %s", tablet_id, exc)

        # If still empty and tablet is labor type, extract worker totals
        if not results and tablet_type == "labor":
            try:
                labor = self._extract_labor_transactions(lines, tablet_id)
                results.extend(labor)
            except Exception as exc:
                logger.warning("Error in labor pass for %s: %s", tablet_id, exc)

        self._propagate_tablet_commodity(results)
        return results

    @staticmethod
    def _propagate_records_commodity(records: List[TabletRecord]) -> None:
        """Records-path analogue of :meth:`_propagate_tablet_commodity`.

        When a tablet's record entries attest exactly one grain-capacity (sila3)
        commodity, fill every bare sila3 entry with it; multi-commodity tablets
        stay untouched. Operates across all records so a commodity named in one
        section carries to a bare entry in another.
        """
        seen = {
            e.commodity for rec in records for e in rec.entries
            if e.unit == "sila3" and e.commodity is not None
        }
        if len(seen) != 1:
            return
        only = next(iter(seen))
        for rec in records:
            for e in rec.entries:
                if e.unit == "sila3" and e.commodity is None:
                    e.commodity = only

    @staticmethod
    def _propagate_tablet_commodity(results: List[Transaction]) -> None:
        """
        Fill in commodity for bare grain-capacity lines from tablet context.

        Many Ur III accounts name the commodity once (a header total or one
        disbursement) and then list further amounts as a bare "N gur NAME"
        with no commodity word; section splits (e.g. at sza3-bi-ta) reset the
        forward-carried pending commodity, so those lines arrive as None.

        When the whole tablet attests exactly one grain-capacity (sila3)
        commodity, every bare sila3 line is that commodity, so propagate it.
        Tablets that interleave two staples (barley + emmer) stay ambiguous
        and are left untouched rather than guessed.  Archaic (pre-Ur III)
        tablets are excluded naturally: they carry no Ur-III commodity label,
        so the attested set is empty and nothing is filled.
        """
        seen = {
            tx.commodity for tx in results
            if tx.unit == "sila3" and tx.commodity is not None
        }
        if len(seen) != 1:
            return
        only = next(iter(seen))
        for tx in results:
            if tx.unit == "sila3" and tx.commodity is None:
                tx.commodity = only

    def extract_transaction(self, lines: List[str], tablet_id: str) -> Transaction:
        """Single-transaction shim for backward compatibility."""
        txs = self.extract_transactions(lines, tablet_id)
        return txs[0] if txs else Transaction(tablet_id=tablet_id)

    def _transfer_record_from_section(
        self, section: List[str], tablet_id: str
    ) -> Optional[TabletRecord]:
        """
        Wrap _extract_from_section() result as a TabletRecord.
        Classifies record_type based on bilateral completeness:
          issuer + recipient → "transfer"
          recipient only    → "receipt"
          issuer only / qty only → "record"  (static entry)
        """
        txs = self._extract_from_section(section, tablet_id)
        if not txs:
            return None
        tx = txs[0]

        if tx.issuer and tx.recipient:
            rtype = "transfer"
        elif tx.recipient:
            rtype = "receipt"
        elif tx.tx_type == "labor":
            rtype = "labor"
        else:
            rtype = "record"

        rec = TabletRecord(
            record_idx=0,
            record_type=rtype,
            issuer=tx.issuer,
            agent=tx.agent,
            date=tx.date,
            raw_date=tx.raw_date,
        )
        if tx.quantity is not None or tx.recipient is not None or tx.commodity is not None:
            rec.entries.append(RecordEntry(
                entry_idx=1,
                recipient=tx.recipient,
                quantity=tx.quantity,
                unit=tx.unit,
                commodity=tx.commodity,
            ))
        if not rec.entries and rec.issuer is None:
            return None
        return rec

    def _allocation_records_from_lines(
        self, lines: List[str], tablet_id: str
    ) -> List[TabletRecord]:
        """
        Convert allocation groups to TabletRecords, one per szabra,
        with one RecordEntry per engar recipient inside each record.
        """
        date, raw_mu = self._parse_date(lines)
        events: List[Tuple[str, object]] = []

        for line in lines:
            s = line.strip()
            if not self._is_content(s):
                continue
            clean = self._strip_linenum(s)
            if self._RE_SZUNIGIN.match(s):
                events.append(("total", None))
                continue
            m_szabra = self._RE_SZABRA.match(clean)
            if m_szabra:
                name = self._clean_atf_name(m_szabra.group(1))
                if name:
                    events.append(("szabra", name))
                continue
            if re.search(r"\bengar\b", clean):
                q_inline, u_inline = self.extract_quantity(clean)
                comm_inline = self._detect_commodity(clean)
                m_engar = self._RE_ENGAR.match(clean)
                raw_name = m_engar.group(1) if m_engar else ""
                name = re.sub(r"^(?:\d+(?:/\d+)?\(\w+[2']*\)\s*)+", "", raw_name).strip()
                name = re.sub(r"^(?:(?:sze|gur|ziz2|gig|barig|ban2|sila3?)\s+)+", "", name, flags=re.I).strip()
                name = re.sub(r"\s+(?:GAN2|a-sza3)\b.*$", "", name, flags=re.I).strip()
                name = re.sub(r"\s*(?:sze|gur|ziz2|gig)\s*$", "", name).strip()
                name = self._clean_atf_name(name)
                events.append(("engar", (name, q_inline, u_inline, comm_inline)))
                continue
            q, u = self.extract_quantity(clean)
            if q is not None:
                comm = self._detect_commodity(clean)
                events.append(("qty", (q, u, comm)))

        if sum(1 for e in events if e[0] == "engar") < 2:
            return []

        groups: List[List] = []
        current: List = []
        for event in events:
            if event[0] == "total":
                groups.append(current)
                current = []
            else:
                current.append(event)
        if current:
            groups.append(current)

        results: List[TabletRecord] = []
        for i, group in enumerate(groups):
            issuer: Optional[str] = None
            for j in range(i + 1, min(i + 6, len(groups))):
                if groups[j] and groups[j][0][0] == "szabra":
                    issuer = groups[j][0][1]
                    break
            if not issuer:
                for etype, edata in group:
                    if etype == "szabra":
                        issuer = edata
                        break
            if not issuer:
                continue

            rec = TabletRecord(
                record_idx=0,
                record_type="allocation",
                issuer=issuer,
                date=date,
                raw_date=raw_mu,
            )
            pending_qty: Optional[float] = None
            pending_unit: Optional[str] = None
            pending_comm: Optional[str] = None

            for etype, edata in group:
                if etype == "szabra":
                    continue
                if etype == "qty":
                    pending_qty, pending_unit, pending_comm = edata  # type: ignore
                elif etype == "engar":
                    name, q_inline, u_inline, comm_inline = edata  # type: ignore
                    qty  = q_inline if q_inline is not None else pending_qty
                    unit = u_inline if q_inline is not None else pending_unit
                    comm = comm_inline or pending_comm or "barley"
                    if qty is not None and name and len(name) >= 2:
                        rec.entries.append(RecordEntry(
                            entry_idx=len(rec.entries) + 1,
                            recipient=name,
                            quantity=qty,
                            unit=unit,
                            commodity=comm,
                        ))
                    if q_inline is None:
                        pending_qty = None

            if rec.entries:
                results.append(rec)

        return results

    def _ration_record_from_lines(
        self, lines: List[str], tablet_id: str
    ) -> Optional[TabletRecord]:
        """Convert _extract_ration_list result to a single TabletRecord."""
        txs = self._extract_ration_list(lines, tablet_id)
        if not txs:
            return None
        date = txs[0].date if txs else None
        raw_mu = txs[0].raw_date if txs else None
        rec = TabletRecord(
            record_idx=0,
            record_type="ration",
            date=date,
            raw_date=raw_mu,
        )
        for i, tx in enumerate(txs, 1):
            rec.entries.append(RecordEntry(
                entry_idx=i,
                recipient=tx.recipient,
                quantity=tx.quantity,
                unit=tx.unit,
                commodity=tx.commodity,
            ))
        return rec

    def _labor_record_from_lines(
        self, lines: List[str], tablet_id: str
    ) -> Optional[TabletRecord]:
        """Convert _extract_labor_transactions result to a single TabletRecord."""
        txs = self._extract_labor_transactions(lines, tablet_id)
        if not txs:
            return None
        tx = txs[0]
        rec = TabletRecord(
            record_idx=0,
            record_type="labor",
            agent=tx.agent,
            date=tx.date,
            raw_date=tx.raw_date,
        )
        rec.entries.append(RecordEntry(
            entry_idx=1,
            quantity=tx.quantity,
            unit=tx.unit,
            commodity=tx.commodity,
        ))
        return rec

    def _scan_section_quantity_first(
        self, section: List[str], tablet_id: str
    ) -> Optional[TabletRecord]:
        """
        Quantity-first section scan.

        Every line that yields a quantity becomes a separate RecordEntry,
        regardless of whether named actors are present.  A section with
        barley + emmer + wheat on three consecutive lines produces three
        entries under one record, instead of collapsing to the first.

        Named actors (issuer, recipient, agent) are collected and attached
        to the record as context; they are NOT a prerequisite for entry
        creation.
        """
        content = [l.strip() for l in section if self._is_content(l.strip())]
        if not content:
            return None

        issuer:         Optional[str] = None
        recipient:      Optional[str] = None
        agent:          Optional[str] = None
        kiszib_name:    Optional[str] = None
        pending_dative: Optional[str] = None
        prev_name:      Optional[str] = None
        pending_comm:   Optional[str] = None   # last commodity seen on any line
        entries: List[RecordEntry] = []
        skip_carryforward = False

        date, raw_mu = self._parse_date(section)

        for line in content:
            # Szunigin total closes the section; its quantity is the sum of what came
            # before it — including it would double-count the entire section.
            if self._RE_SZUNIGIN.match(line):
                continue

            clean = self._strip_linenum(line)

            # Skip "sze-bi N gur" accounting conversion notes.
            if self._RE_SZE_BI.match(clean):
                continue

            # Commodity detection runs on every line so it can carry forward
            # to the next quantity line (commodity and quantity sometimes
            # appear on adjacent lines rather than the same line).
            c = self._detect_commodity(clean)
            if c:
                pending_comm = c

            # Issuer patterns (ki NAME-ta, institution-ta, etc.)
            iss = self._extract_issuer(clean)
            if iss and issuer is None:
                issuer = iss
                continue

            # Agent
            ag = self._extract_agent(clean)
            if ag and agent is None:
                agent = ag

            # Kiszib fallback issuer
            m_k = self._RE_KISZIB.match(clean) or self._RE_KISZIB_INLINE.search(clean)
            if m_k and kiszib_name is None:
                cand = self._clean_atf_name(m_k.group(1))
                if len(cand) >= 2:
                    kiszib_name = cand

            # Recipient — inline szu ba-ti
            rec_f = self._extract_recipient_inline(clean)
            if rec_f and recipient is None:
                recipient = rec_f
                prev_name = None
                continue

            # Recipient — standalone szu ba-ti
            if self._RE_SHU_ALONE.match(clean) and recipient is None:
                recipient = prev_name or pending_dative
                prev_name = None
                continue

            # Recipient — i3-dab5
            rec_h = self._extract_recipient_idab5(clean)
            if rec_h and recipient is None:
                recipient = rec_h
                continue

            # Inline ration: N(u) sze NAME → entry with its own recipient
            rec_i, qty_i = self._extract_recipient_u_sze(clean)
            if rec_i:
                entries.append(RecordEntry(
                    entry_idx=0,
                    recipient=rec_i,
                    quantity=qty_i,
                    unit="sila3",
                    commodity=pending_comm or "barley",
                ))
                prev_name = None
                continue

            # ba-an-szum2 with pending dative recipient
            if self._RE_BA_AN_SUM.search(clean) and recipient is None:
                if pending_dative:
                    recipient = pending_dative
                continue

            # Track dative -ra for ba-an-szum2
            m_dat = self._RE_DATIVE_RA.match(clean)
            if m_dat:
                cand = self._clean_atf_name(m_dat.group(1).strip())
                if self._looks_like_name(cand):
                    pending_dative = cand

            # *** QUANTITY-FIRST: every allotment on a line → one RecordEntry ***
            # A line may pack several goods ("5 sila3 beer 5 gin2 onion"); split
            # them so each becomes its own entry in its own unit. Single-
            # commodity lines yield one segment and behave exactly as before.
            # Balance-line guard: check the full line before segmenting so that
            # a leading keyword stripped by the segmenter (e.g. "sza3 sze")
            # cannot leave the bare quantity visible to extract_quantity.
            if self._RE_BALANCE_LINE.search(clean):
                if re.match(r"^\[?sza3[#!?]*-\[?bi[#!?]*-\[?ta[#!?\]]*\b", clean, re.I):
                    skip_carryforward = True
                continue
            segs = self._segment_allotments(clean)
            made_entry = False
            for seg in segs:
                q, u = self.extract_quantity(seg)
                if q is None:
                    continue
                if skip_carryforward and u == "sila3":
                    skip_carryforward = False
                    continue  # suppress carry-forward grain quantity
                seg_c = self._detect_commodity(seg) if len(segs) > 1 else c
                comm = seg_c or pending_comm   # same-line commodity preferred
                if u == "head" and comm is None:
                    comm = "animal"
                # sze gub-ba distribution lines carry the recipient inline:
                # "1(asz) 1(barig) gur ur-e2-mah" → recipient = "ur-e2-mah"
                inline_recip = self._extract_inline_qty_recipient(seg)
                entries.append(RecordEntry(
                    entry_idx=0,
                    recipient=inline_recip,
                    quantity=q,
                    unit=u,
                    commodity=comm,
                ))
                made_entry = True
            if made_entry:
                continue

            # Track previous name-like line (for standalone szu ba-ti)
            if self._looks_like_name(clean):
                prev_name = self._clean_atf_name(clean)
            elif not (self._RE_SHU_ALONE.match(clean)
                      or self._RE_BA_AN_SUM.search(clean)
                      or m_dat
                      or self._RE_NOT_NAME.match(clean)):
                prev_name = None

        if issuer is None and kiszib_name:
            issuer = kiszib_name

        # Nothing at all — skip
        if not entries and issuer is None and recipient is None:
            return None

        if issuer and recipient:
            rtype = "transfer"
        elif recipient:
            rtype = "receipt"
        else:
            rtype = "record"

        rec = TabletRecord(
            record_idx=0,
            record_type=rtype,
            issuer=issuer,
            agent=agent,
            date=date,
            raw_date=raw_mu,
            entries=entries,
        )
        return rec

    def extract_records(
        self, lines: List[str], tablet_id: str
    ) -> TabletSummary:
        """
        Main hierarchical extraction entry point.
        Returns a TabletSummary (tablet → records → entries).

        Uses quantity-first scanning for transfer/receipt/record tablets so
        that every commodity line in a section becomes a distinct entry —
        a section with barley + emmer + wheat yields three entries, not one.
        """
        lines = self._strip_secondary_sections(lines)
        _ARCHAIC_LARGE = re.compile(r"\((?:szar'u|szar2|gesz'u)@c\)", re.I)
        if any(_ARCHAIC_LARGE.search(l) for l in lines):
            return TabletSummary(
                tablet_id=tablet_id, tablet_type="archaic", records=[]
            )
        tablet_type = self._classify_tablet(lines)
        records: List[TabletRecord] = []

        if tablet_type == "allocation":
            records = self._allocation_records_from_lines(lines, tablet_id)
        elif tablet_type == "labor":
            lr = self._labor_record_from_lines(lines, tablet_id)
            if lr:
                records = [lr]
        else:
            for section in self._split_sections(lines):
                try:
                    rec = self._scan_section_quantity_first(section, tablet_id)
                    if rec is not None:
                        records.append(rec)
                except Exception as exc:
                    logger.warning("Record extraction error %s: %s", tablet_id, exc)

        if not records:
            rr = self._ration_record_from_lines(lines, tablet_id)
            if rr:
                records = [rr]
        if not records and tablet_type == "labor":
            lr = self._labor_record_from_lines(lines, tablet_id)
            if lr:
                records = [lr]

        self._propagate_records_commodity(records)

        for i, rec in enumerate(records, 1):
            rec.record_idx = i
            for j, entry in enumerate(rec.entries, 1):
                entry.entry_idx = j

        return TabletSummary(
            tablet_id=tablet_id,
            tablet_type=tablet_type,
            records=records,
        )
