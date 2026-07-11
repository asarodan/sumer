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


class TestAuditCaughtFalsePositives:
    """Bugs found by the 30-transaction manual audit (2026-07)."""

    def test_royal_measure_lugal_is_not_a_recipient(self, ext):
        # P110751: "N sze gur lugal" — lugal qualifies the measure (royal gur);
        # the real receiver is on the szu ba-ti line.
        s = ext.extract_records([
            "@tablet", "@obverse",
            "1. 2(u) 9(asz) 4(barig) 2(ban2) sze gur lugal",
            "2. sza3-gal erin2-na",
            "3. ki gu3-de2-a-ta",
            "4. ur-e2-ninnu szu ba-ti",
        ], "TEST-LUGAL")
        entry_recips = [e.recipient for r in s.records for e in r.entries]
        assert "lugal" not in entry_recips
        # the genuine receiver must be recoverable somewhere on the record
        all_recips = entry_recips + [
            getattr(r, "recipient", None) for r in s.records
        ]
        assert "ur-e2-ninnu" in all_recips

    def test_lugal_compound_names_survive(self, ext):
        # Personal names beginning with lugal- must still be extracted.
        assert ext._extract_inline_qty_recipient(
            "1(asz) 1(barig) gur lugal-e2-mah-e") == "lugal-e2-mah-e"

    def test_interest_rate_lugal_masz2_rejected(self, ext):
        # P209771: "7(asz) sze gur lugal masz2 1(barig)-ta" — royal measure +
        # interest rate, not a recipient called "lugal masz2".
        got = ext._extract_inline_qty_recipient("7(asz) sze gur lugal masz2")
        assert got is None

    def test_coriander_is_not_barley(self, ext):
        # P454001: sze-lu2 = coriander.
        assert ext._detect_commodity("6(asz) sze-lu2 gur") != "barley"

    def test_dairy_ga_sze_a_is_not_barley(self, ext):
        # P208651: ga-sze-a = dairy product measured in gur.
        assert ext._detect_commodity("1(asz) 3(ban2) ga-sze-a gur") != "barley"

    def test_plain_barley_still_detected(self, ext):
        assert ext._detect_commodity("5(asz) sze gur") == "barley"
        assert ext._detect_commodity("2(barig) sze-ba") == "barley"


class TestDateLineCommodityBleed:
    def test_harvest_month_does_not_set_barley_context(self, ext):
        # "iti sze-sag11-ku5" contains the barley sign; it must not type the
        # following animal head-count as barley (P201081).
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. iti sze-sag11-ku5",
            "2. 3(disz) udu",
            "3. ki lu2-utu-ta",
            "4. ur-ku3-nun-na i3-dab5",
        ], "TEST-ITI-BLEED")
        heads = [t for t in txs if t.unit == "head"]
        assert heads and all(t.commodity == "animal" for t in heads)

    def test_head_count_never_labeled_grain(self, ext):
        # Even with genuine barley context above, a head-count is an animal.
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 5(asz) sze gur",
            "2. 3(disz) udu",
            "3. ki lu2-utu-ta",
            "4. ur-ku3-nun-na i3-dab5",
        ], "TEST-HEAD")
        heads = [t for t in txs if t.unit == "head"]
        assert heads and all(t.commodity == "animal" for t in heads)


class TestOrchardYieldLines:
    def test_gesz_kiri6_lines_are_grain(self, ext):
        # P100892: garden-yield assessment — "N {gesz}kiri6 NAME" is barley
        # per orchard plot, not a wooden-object count.  The scribe's nested
        # subtotals confirm the readings arithmetically.
        s = ext.extract_records([
            "@tablet", "@obverse",
            "1. 6(asz) 4(barig) 5(ban2) sze gur lugal",
            "2. {gesz}kiri6 {d}szul-gi-a2-kalam-ma",
            "3. 1(asz) 2(ban2) {gesz}kiri6 gesztin gar3-szum{ki}",
            "4. 2(barig) 2(ban2) {gesz}kiri6 ur-{d}nin-gir2-su",
        ], "TEST-KIRI6")
        qs = [e.quantity for r in s.records for e in r.entries if e.unit == "sila3"]
        assert 2090.0 in qs      # 6;4;5
        assert 320.0 in qs       # 1;0;2
        assert 140.0 in qs       # 0;2;2

    def test_wooden_object_counts_still_blocked(self, ext):
        # "4(u) gesz {gesz}asal2" = 40 poplar logs — must stay non-grain.
        assert ext.extract_quantity("4(u) {gesz}asal2", context_gur=True) == (None, None)
