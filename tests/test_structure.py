"""End-to-end extraction over synthetic tablets: commodity propagation and
multi-commodity line splitting at the transaction level."""
import pytest


def _tablet(*body):
    """Wrap content lines in a minimal ATF tablet skeleton."""
    return ["&P900000 = Synthetic", "#atf: lang sux", "@tablet", "@obverse", *body]


class TestSingleCommodityPropagation:
    def test_bare_line_inherits_sole_commodity(self, ext):
        # The bare "3(asz) gur NAME" appears BEFORE any commodity word, so the
        # section's forward-carry cannot fill it — only the tablet-level
        # single-commodity pass can. As barley is the sole staple, it is filled.
        lines = _tablet(
            "1. 3(asz) gur lugal-ba",          # bare, pre-commodity
            "2. 4(asz) sze gur a-kal-la",      # barley
            "3. szunigin 7(asz) gur",
        )
        grain = [t for t in ext.extract_transactions(lines, "P900000")
                 if t.unit == "sila3"]
        assert grain and all(t.commodity == "barley" for t in grain)

    def test_two_commodities_leave_bare_unresolved(self, ext):
        # Barley AND emmer both attested → the propagation guard must NOT guess
        # the bare pre-commodity line; it stays None.
        lines = _tablet(
            "1. 3(asz) gur lugal-ba",          # bare, pre-commodity → None
            "2. 4(asz) sze gur a-kal-la",      # barley
            "3. 6(asz) ziz2 gur a-kal-la",     # emmer
            "4. szunigin 1(u) 3(asz) gur",
        )
        comms = {t.commodity for t in ext.extract_transactions(lines, "P900000")
                 if t.unit == "sila3"}
        assert {"barley", "emmer"} <= comms
        assert None in comms


class TestMultiCommoditySplit:
    def test_mixed_ration_line_splits(self, ext):
        # One line, three goods (beer / bread / onion) → three entries.
        lines = _tablet(
            "1. 5(disz) sila3 kasz 5(disz) sila3 ninda 5(disz) gin2 szum2",
            "2. ki lugal-ta",
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000") if t.quantity]
        comms = [t.commodity for t in txs]
        assert "beer" in comms and "bread" in comms

    def test_capacity_and_weight_kept_separate(self, ext):
        lines = _tablet("1. 5(disz) sila3 kasz 5(disz) gin2 szum2", "2. ki lugal-ta")
        txs = [t for t in ext.extract_transactions(lines, "P900000") if t.quantity]
        units = {t.unit for t in txs}
        assert units == {"sila3", "gin2"}


class TestRecordsPath:
    """The hierarchical records path (extract_records) must mirror the
    transaction path: split multi-commodity lines and propagate a sole staple."""

    def _entries(self, ext, body):
        summary = ext.extract_records(_tablet(*body), "P900000")
        return [e for rec in summary.records for e in rec.entries]

    def test_multi_commodity_line_splits(self, ext):
        entries = self._entries(ext, [
            "1. 5(disz) sila3 kasz 5(disz) sila3 ninda 5(disz) gin2 szum2",
            "2. ki lugal-ta",
        ])
        comms = {e.commodity for e in entries if e.quantity}
        assert "beer" in comms and "bread" in comms

    def test_sole_commodity_propagates(self, ext):
        entries = self._entries(ext, [
            "1. 3(asz) gur lugal-ba",          # bare, pre-commodity
            "2. 4(asz) sze gur a-kal-la",
            "3. szunigin 7(asz) gur",
        ])
        grain = [e for e in entries if e.unit == "sila3"]
        assert grain and all(e.commodity == "barley" for e in grain)

    def test_multi_commodity_leaves_bare_none(self, ext):
        entries = self._entries(ext, [
            "1. 3(asz) gur lugal-ba",          # bare, pre-commodity → None
            "2. 4(asz) sze gur a-kal-la",
            "3. 6(asz) ziz2 gur a-kal-la",
        ])
        comms = {e.commodity for e in entries if e.unit == "sila3"}
        assert {"barley", "emmer"} <= comms and None in comms


class TestBasicTransaction:
    def test_issuer_and_quantity(self, ext):
        lines = _tablet("1. 8(asz) sze gur", "2. ki lugal-ta", "3. kiszib3 ur-saga")
        txs = ext.extract_transactions(lines, "P900000")
        assert any(t.issuer == "lugal" and t.quantity == 2400.0 for t in txs)

    def test_empty_tablet_no_transactions(self, ext):
        assert ext.extract_transactions(_tablet("1. [...]"), "P900000") == []


class TestEnvelopeDeduplication:
    """@envelope sections duplicate the tablet text; they must be stripped."""

    def test_envelope_not_double_counted(self, ext):
        # A tablet with an @envelope bearing the same quantity must yield
        # exactly one transaction, not two.
        lines = [
            "&P900001 = Synthetic envelope test",
            "#atf: lang sux",
            "@tablet",
            "@obverse",
            "1. 8(asz) sze gur",
            "2. ki lugal-ta",
            "@reverse",
            "1. ur-saga szu ba-ti",
            "@envelope",
            "@obverse",
            "1. 8(asz) sze gur",
            "2. ki lugal-ta",
            "@reverse",
            "1. kiszib3 ur-saga",
        ]
        txs = ext.extract_transactions(lines, "P900001")
        qtys = [t.quantity for t in txs if t.quantity]
        assert qtys.count(2400.0) == 1

    def test_seal_section_ignored(self, ext):
        lines = [
            "&P900002 = Synthetic seal test",
            "#atf: lang sux",
            "@tablet",
            "@obverse",
            "1. 5(asz) sze gur ki lugal-ta",
            "@reverse",
            "1. ur-saga szu ba-ti",
            "@seal 1",
            "1. ur-saga dub-sar",
            "2. dumu lugal-ba",
        ]
        txs = ext.extract_transactions(lines, "P900002")
        assert len([t for t in txs if t.quantity]) == 1


class TestBracketedKeywords:
    """CDLI square-bracket restorations must not defeat line-type filters."""

    def test_bracketed_sze_bi_not_extracted(self, ext):
        # "[sze-bi N gur]" = expected yield (damaged restoration); must be suppressed
        lines = _tablet(
            "1. [sze-bi 1(szar2) gur]",
            "2. 3(gesz2) sze gur",    # actual delivery (54,000 sila3)
            "3. mu-kux(DU)",
            "4. la2-ia3 2(gesz2) gur",
            "5. mu szul-gi lugal uri5{ki}-ma",
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000") if t.unit == "sila3"]
        qtys = [t.quantity for t in txs]
        assert 1_080_000.0 not in qtys   # sze-bi must be suppressed
        assert 54_000.0 in qtys           # delivery counted

    def test_bracketed_diri_not_extracted(self, ext):
        lines = _tablet(
            "1. 5(asz) sze gur ki lugal-ta szu ba-ti",
            "2. [diri] 1(asz) gur",   # surplus — must not add a second transaction
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000") if t.unit == "sila3"]
        qtys = [t.quantity for t in txs]
        assert 300.0 not in qtys or qtqs.count(300.0) <= 1   # diri not double-counted
        assert 1500.0 in qtys


class TestSzuniginNotDoubleCountedInRecords:
    """szunigin total must not produce an extra entry in the records path."""

    def _entries(self, ext, body):
        summary = ext.extract_records(_tablet(*body), "P900000")
        return [e for rec in summary.records for e in rec.entries if e.quantity]

    def test_szunigin_excluded_from_records(self, ext):
        # Two data lines → two entries; the szunigin is the sum, not a third entry.
        entries = self._entries(ext, [
            "1. 3(asz) sze gur",
            "2. 4(asz) sze gur",
            "3. szunigin 7(asz) sze gur",
        ])
        qtys = sorted(e.quantity for e in entries)
        # Should be [900, 1200] not [900, 1200, 2100]
        assert qtys == [900.0, 1200.0]

    def test_szunigin_excluded_not_splitting_total(self, ext):
        # Verify total qty sums to data lines, NOT data+total
        entries = self._entries(ext, [
            "1. 2(asz) sze gur",
            "2. szunigin 2(asz) sze gur",
        ])
        assert sum(e.quantity for e in entries) == 600.0  # one entry only

    def test_bracketed_szunigin_excluded(self, ext):
        # "[szunigin N gur]" = damaged-text restoration of the total line.
        # The bracket around the keyword must not defeat the szunigin filter.
        entries = self._entries(ext, [
            "1. 3(asz) sze gur",
            "2. 4(asz) sze gur",
            "3. [szunigin 7(asz) sze gur]",
        ])
        qtys = sorted(e.quantity for e in entries)
        assert qtys == [900.0, 1200.0]  # total line excluded

    def test_bracketed_szunigin_transactions(self, ext):
        # Same test via extract_transactions path.
        lines = _tablet(
            "1. 3(asz) sze gur",
            "2. 4(asz) sze gur",
            "3. [szunigin 7(asz) sze gur]",
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000") if t.unit == "sila3"]
        qtys = sorted(t.quantity for t in txs)
        assert qtys == [900.0, 1200.0]

    def test_szunigin2_excluded(self, ext):
        # "szunigin2" (CDLI subscript-2 variant) must be suppressed just like "szunigin".
        entries = self._entries(ext, [
            "1. 3(asz) sze gur",
            "2. 4(asz) sze gur",
            "3. szunigin2 7(asz) sze gur",
        ])
        qtys = sorted(e.quantity for e in entries)
        assert qtys == [900.0, 1200.0]


class TestYieldLedger:
    """Yield-balance ledger tablets must be classified correctly."""

    def test_yield_ledger_type(self, ext):
        # Tablet with sze-bi + mu-kux + la2-ia3 → yield_ledger type
        lines = _tablet(
            "1. a-sza3 ur-nanna",
            "2. 5(asz) GAN2",               # field area (suppressed)
            "3. sze-bi 1(szar2) gur",        # expected yield (suppressed)
            "4. mu-kux 5(gesz2) 4(asz) gur", # actual delivery (counted)
            "5. la2-ia3 2(gesz2) gur",       # deficit (suppressed)
        )
        summary = ext.extract_records(lines, "P900000")
        assert summary.tablet_type == "yield_ledger"

    def test_yield_ledger_only_counts_delivery(self, ext):
        # Only the mu-kux quantity should appear; sze-bi and la2-ia3 suppressed.
        # mu-kux itself is now an admin keyword so no additional trigger needed.
        lines = _tablet(
            "1. a-sza3 ur-nanna",
            "2. sze-bi 1(szar2) gur",         # expected: 1,080,000 sila3 — suppressed
            "3. mu-kux 5(gesz2) 4(asz) gur",  # delivered: 90,000 + 1,200 = 91,200 sila3
            "4. la2-ia3 2(gesz2) gur",         # deficit 36,000 sila3 — suppressed
            "5. iti sze-kin-ku5",
            "6. mu szul-gi lugal uri5{ki}-ma",
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000")
               if t.unit == "sila3"]
        qtys = [t.quantity for t in txs]
        assert 91_200.0 in qtys           # mu-kux delivery counted
        assert 1_080_000.0 not in qtys   # sze-bi suppressed
        assert 36_000.0 not in qtys      # la2-ia3 deficit suppressed


class TestBalanceLinesInContext:
    """Balance-line filtering must work inside full tablet extraction."""

    def test_la2_ia3_not_a_transaction(self, ext):
        lines = _tablet(
            "1. 3(asz) sze gur",
            "2. ki lugal-ta",
            "3. la2-ia3 1(asz) gur",  # deficit — must not generate a tx
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000")
               if t.unit == "sila3"]
        assert all(t.quantity == 900.0 for t in txs)

    def test_sza3_bi_ta_not_a_transaction(self, ext):
        lines = _tablet(
            "1. 4(asz) sze gur ki lugal-ta szu ba-ti",
            "2. sza3-bi-ta 4(asz) gur",   # carry-forward — must not generate a tx
        )
        txs = [t for t in ext.extract_transactions(lines, "P900000")
               if t.unit == "sila3"]
        qtys = [t.quantity for t in txs]
        assert 1200.0 in qtys
        assert qtys.count(1200.0) == 1  # not doubled by sza3-bi-ta
