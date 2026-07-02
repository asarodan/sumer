"""Commodity detection, including the precedence rules that keep silver-weight
'sze' (barleycorn) from being mislabelled as barley grain."""
import pytest


class TestStaples:
    @pytest.mark.parametrize("line,comm", [
        ("5(asz) sze gur",            "barley"),
        ("3(asz) ziz2 gur",           "emmer"),
        ("2(asz) gig gur",            "wheat"),
        ("2(disz) sila3 esza",        "flour"),   # eša fine flour
        ("1(barig) dabin",            "flour"),
        ("5(disz) sila3 ninda",       "bread"),   # ninda loaves
        ("2(ban2) kasz",              "beer"),
        ("1(disz) sila3 i3-gesz",     "oil"),
        ("1(disz) sila3 i3-szah2",    "oil"),     # lard / animal fat
        ("3(asz) zu2-lum gur",        "dates"),
    ])
    def test_detect(self, ext, line, comm):
        assert ext._detect_commodity(line) == comm


class TestMetalPrecedence:
    def test_ku3_babbar_is_silver(self, ext):
        assert ext._detect_commodity("3(disz) gin2 ku3-babbar") == "silver"

    def test_ku3_sig17_is_gold(self, ext):
        assert ext._detect_commodity("1(disz) gin2 ku3-sig17") == "gold"

    def test_silver_value_note_before_barley(self, ext):
        # "ku3-bi N gin2 M sze" = silver value; the sze is the barleycorn weight
        # sub-unit, NOT the barley commodity. Silver must win.
        assert ext._detect_commodity("ku3-bi 3(disz) gin2 5(disz) sze") == "silver"

    def test_weight_sze_is_not_barley(self, ext):
        # 'sze' in a pure gin2 weight context (no capacity unit) is not barley.
        assert ext._detect_commodity("1(disz) gin2 1(u) sze") is None

    def test_weight_sze_copper(self, ext):
        assert ext._detect_commodity("2(disz) gin2 1(u) sze uruda") == "copper"

    def test_real_barley_still_barley(self, ext):
        # A genuine capacity barley line keeps its label.
        assert ext._detect_commodity("8(asz) 2(barig) sze gur") == "barley"


class TestOperationDescriptionsExcluded:
    @pytest.mark.parametrize("line", [
        "sze gesz ra-a",     # threshing
        "sze de2-a",         # pouring grain
    ])
    def test_op_desc_not_commodity(self, ext, line):
        assert ext._detect_commodity(line) is None


class TestNextLineCommodityBackfill:
    def test_split_entry_backfilled(self, ext):
        # P144069: quantity line + continuation line carrying the commodity
        # and the closing unit word ("gur") — one entry split across two lines.
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 7(asz) 3(barig) 4(ban2) 8(disz) sila3",
            "2. zi3 ISZ ba-ba gur",
            "3. ki ur-tur-ta",
        ], "TEST-BACKFILL")
        assert txs
        assert txs[0].quantity == 2328.0
        assert txs[0].commodity == "flour"

    def test_commodity_line_with_own_quantity_does_not_backfill(self, ext):
        # A following line that has its own quantity is a new entry, not a
        # continuation — the untyped entry above must stay untyped.  Two
        # different commodities are attested so tablet-level propagation
        # (which only fires for single-commodity tablets) stays off and the
        # back-fill guard is what is actually under test.
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 3(disz) sila3",
            "2. 2(disz) sila3 kasz",
            "3. 1(disz) sila3 i3-gesz",
            "4. ki ur-tur-ta",
        ], "TEST-NOBACKFILL")
        pairs = [(t.quantity, t.commodity) for t in txs if t.quantity]
        assert (3.0, None) in pairs, pairs
