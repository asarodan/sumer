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


class TestBasicTransaction:
    def test_issuer_and_quantity(self, ext):
        lines = _tablet("1. 8(asz) sze gur", "2. ki lugal-ta", "3. kiszib3 ur-saga")
        txs = ext.extract_transactions(lines, "P900000")
        assert any(t.issuer == "lugal" and t.quantity == 2400.0 for t in txs)

    def test_empty_tablet_no_transactions(self, ext):
        assert ext.extract_transactions(_tablet("1. [...]"), "P900000") == []
