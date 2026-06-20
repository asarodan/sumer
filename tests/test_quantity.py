"""Metrology: sexagesimal grain capacity, weights, animals, and the
capacity/weight split on mixed lines."""
import pytest


class TestGrainCapacity:
    def test_compound_gur_to_sila3(self, ext):
        # 8 gur*300 + 2 barig*60 + 1 ban2*10 = 2400 + 120 + 10 = 2530 sila3
        assert ext.extract_quantity("8(asz) 2(barig) 1(ban2) sze gur") == (2530.0, "sila3")

    def test_single_gur(self, ext):
        assert ext.extract_quantity("5(asz) sze gur") == (1500.0, "sila3")

    def test_bare_sila3_ration(self, ext):
        assert ext.extract_quantity("5(disz) sila3 ninda") == (5.0, "sila3")

    def test_fraction(self, ext):
        assert ext.extract_quantity("1/2(disz) sila3 i3-nun") == (0.5, "sila3")

    @pytest.mark.parametrize("line,sila3", [
        ("1(barig) sze",  60.0),
        ("1(ban2) sze",   10.0),
        ("2(asz) sze gur", 600.0),
    ])
    def test_subunits(self, ext, line, sila3):
        assert ext.extract_quantity(line) == (sila3, "sila3")


class TestWeights:
    def test_silver_gin2(self, ext):
        assert ext.extract_quantity("3(disz) gin2 ku3-babbar") == (3.0, "gin2")

    def test_weight_stays_gin2_not_sila3(self, ext):
        # gin2 is a weight unit; it must never be reported as a capacity sila3.
        _, unit = ext.extract_quantity("1(u) gin2 ku3-babbar")
        assert unit == "gin2"


class TestAnimalsAndNonGrain:
    def test_animal_head(self, ext):
        assert ext.extract_quantity("5(disz) gu4") == (5.0, "head")

    def test_wool_rejected(self, ext):
        # siki (wool) is not a grain capacity — must not convert.
        assert ext.extract_quantity("2(asz) gu2 siki") == (None, None)

    def test_gu2_talent_rejected(self, ext):
        # gu2 = talent (weight); '5(asz) gu2 gesz-gal' is timber by weight, not
        # 5 gur of grain — it must not produce a phantom sila3 total.
        assert ext.extract_quantity("5(asz) gu2 gesz-gal") == (None, None)

    def test_labor_line_not_grain(self, ext):
        assert ext.extract_quantity("20(disz) gurusz u4 1(disz)-sze3") == (None, None)


class TestMixedCapacityWeight:
    def test_mixed_line_reports_capacity(self, ext):
        # "5 sila3 beer + 5 gin2 onion" — the capacity portion wins the unit and
        # the gin2 weight add-on is excluded from the sila3 total.
        assert ext.extract_quantity("5(disz) sila3 kasz 5(disz) gin2 szum2") == (5.0, "sila3")

    def test_pure_weight_unchanged(self, ext):
        # No capacity context → stays gin2 (3 + 2 shekels).
        assert ext.extract_quantity("3(disz) gin2 i3 2(disz) gin2 naga") == (5.0, "gin2")


class TestSegmentation:
    def test_three_allotments(self, ext):
        segs = ext._segment_allotments(
            "5(disz) sila3 kasz 5(disz) sila3 ninda 5(disz) gin2 szum2"
        )
        assert len(segs) == 3

    def test_single_commodity_not_split(self, ext):
        # A compound capacity number is ONE allotment, returned unchanged.
        line = "8(asz) 2(barig) sze gur"
        assert ext._segment_allotments(line) == [line]

    def test_trailing_name_not_split(self, ext):
        line = "1(asz) 2(barig) 3(ban2) sze gur ur-e2-mah"
        assert ext._segment_allotments(line) == [line]

    def test_split_buckets_units_correctly(self, ext):
        segs = ext._segment_allotments("5(disz) sila3 kasz 5(disz) gin2 szum2")
        results = [ext.extract_quantity(s) for s in segs]
        assert results == [(5.0, "sila3"), (5.0, "gin2")]


class TestLargeGrainUnits:
    def test_szar_u(self, ext):
        # 1(szar'u) = 36,000 gur = 10,800,000 sila3
        assert ext.extract_quantity("1(szar'u) sze gur") == (10_800_000.0, "sila3")

    def test_szargal(self, ext):
        # 1(szargal) = 216,000 gur = 64,800,000 sila3
        assert ext.extract_quantity("1(szargal) sze gur") == (64_800_000.0, "sila3")

    def test_compound_with_szar_u(self, ext):
        # 3(szar'u) 1(gesz2) 4(asz) 3(barig) = 32,400,000 + 18,000 + 1,200 + 180 = 32,419,380 sila3
        q, u = ext.extract_quantity("3(szar'u) 1(gesz2) 4(asz) 3(barig) sze gur")
        assert u == "sila3"
        assert q == 3 * 10_800_000 + 1 * 18_000 + 4 * 300 + 3 * 60

    def test_szar2_still_works(self, ext):
        # Regression: szar2 = 3,600 gur = 1,080,000 sila3
        assert ext.extract_quantity("1(szar2) sze gur") == (1_080_000.0, "sila3")

    def test_u_unit_without_sze_gur(self, ext):
        # Abbreviated second line on a tablet: "2(gesz2) 4(u) 5(asz) 1(barig) 5(ban2)"
        # without an explicit "sze gur" — the grain_ind from asz/barig must make
        # u resolve to 10 gur = 3,000 sila3, not 0.
        # Expected: (2*60 + 4*10 + 5)*300 + 1*60 + 5*10 = 165*300 + 110 = 49,610
        q, u = ext.extract_quantity("2(gesz2) 4(u) 5(asz) 1(barig) 5(ban2)")
        assert u == "sila3"
        assert q == 49_610.0

    def test_guru7_count_stripped(self, ext):
        # "N guru7 QUANTITY gur" — N is the granary count, not part of the grain.
        # 1(asz) guru7 = 1 granary; quantity = 1(gesz'u) 3(gesz2) 5(u) 4(asz) gur
        # = (1*600 + 3*60 + 5*10 + 4)*300 = 834*300 = 250,200 sila3
        q, u = ext.extract_quantity(
            "1(asz) guru7 1(gesz'u) 3(gesz2) 5(u) 4(asz) 2(barig) 3(disz) sila3 sze gur"
        )
        assert u == "sila3"
        # Count tokens (1 asz = 300) must NOT be added
        assert q == (1*600 + 3*60 + 5*10 + 4)*300 + 2*60 + 3

    def test_guru7_multi_granary(self, ext):
        # Large granary count: "3(gesz2) 3(u) 6(asz) guru7 2(gesz'u) 8(gesz2)..."
        # Only the post-guru7 quantity matters.
        q, u = ext.extract_quantity(
            "3(gesz2) 3(u) 6(asz) guru7 2(gesz'u) 8(gesz2) 1(u) 3(asz) 3(barig) 2(ban2) 5(disz) sila3 gur"
        )
        assert u == "sila3"
        expected = (2*600 + 8*60 + 1*10 + 3)*300 + 3*60 + 2*10 + 5
        assert q == expected


class TestLa2Subtraction:
    """la2 = 'lacking/minus' subtracts the following token(s) from the total."""

    def test_la2_asz_gur(self, ext):
        # 3(gesz2) 5(u) la2 1(asz) gur = (180+50-1)*300 = 68,700 sila3
        q, u = ext.extract_quantity("3(gesz2) 5(u) la2 1(asz) gur")
        assert u == "sila3"
        assert q == (3*60 + 5*10 - 1) * 300

    def test_la2_barig_gur(self, ext):
        # 3(u) 9(asz) la2 2(barig) gur = 39 gur minus 2 barig
        q, u = ext.extract_quantity("3(u) 9(asz) la2 2(barig) gur")
        assert u == "sila3"
        assert q == (3*10 + 9)*300 - 2*60

    def test_la2_sze_gur(self, ext):
        # 4(asz) la2 1(barig) sze gur = 1200 - 60 = 1140 sila3
        q, u = ext.extract_quantity("4(asz) la2 1(barig) sze gur")
        assert u == "sila3"
        assert q == 4*300 - 60

    def test_la2_gin2(self, ext):
        # 1(gesz2) la2 1(u) gin2 = 60 - 10 = 50 gin2 (silver weight)
        q, u = ext.extract_quantity("1(gesz2) la2 1(u) gin2")
        assert u == "gin2"
        assert q == 50.0

    def test_la2_ia3_still_suppressed(self, ext):
        # la2-ia3 (deficit) must NOT be treated as a la2 subtraction
        q, u = ext.extract_quantity("la2-ia3 1(gesz2) 5(asz) gur")
        assert q is None


class TestBalanceLines:
    def test_la2_ia3_suppressed(self, ext):
        # la2-ia3 = deficit/shortfall — must never be counted as a transaction
        assert ext.extract_quantity("la2-ia3 1(gesz2) 5(asz) gur") == (None, None)

    def test_la2_ia3_bracketed(self, ext):
        # Square-bracket prefix (CDLI damaged text restoration) must still be caught
        assert ext.extract_quantity("[la2-ia3] 1(gesz2) 5(asz) gur") == (None, None)

    def test_diri_trailing_suppressed(self, ext):
        # "N gur diri" = surplus — the quantity is a residual, not a new movement
        assert ext.extract_quantity("1(gesz2) 5(asz) gur diri") == (None, None)

    def test_diri_leading_suppressed(self, ext):
        assert ext.extract_quantity("diri 1(gesz2) 5(asz) gur") == (None, None)

    def test_diri_bracketed(self, ext):
        # [diri] at line start (damaged restoration) must also be suppressed
        assert ext.extract_quantity("[diri] 1(szar2) 2(gesz'u) gur") == (None, None)

    def test_sza3_bi_ta_bracketed(self, ext):
        assert ext.extract_quantity("[sza3-bi-ta] 3(asz) sze gur") == (None, None)

    def test_sza3_bi_ta_suppressed(self, ext):
        assert ext.extract_quantity("sza3-bi-ta 3(asz) sze gur") == (None, None)

    def test_normal_delivery_not_suppressed(self, ext):
        # mu-kux delivery lines ARE real grain movements — must not be filtered
        q, u = ext.extract_quantity("mu-kux 3(asz) sze gur")
        assert q == 900.0 and u == "sila3"

    def test_la2_ia3_am3_trailing_suppressed(self, ext):
        # "N gur la2-ia3-am3" = "N gur it is the deficit" — a total of the shortfall,
        # not a delivery; suppress it.
        assert ext.extract_quantity(
            "3(gesz'u) 3(gesz2) 8(asz) 3(ban2) 4(disz) sila3 gur la2-ia3-am3"
        ) == (None, None)

    def test_la2_ia3_am3_on_szunigin_suppressed(self, ext):
        # szunigin + la2-ia3-am3 = grand total of a deficit; must not produce a tx
        assert ext.extract_quantity(
            "szunigin 9(gesz2) 8(asz) 3(barig) 5(ban2) gur la2-ia3-am3"
        ) == (None, None)


class TestScribalCorrections:
    """CDLI <<...>> marks text the scribe crossed out; it must be stripped."""

    def test_scribal_correction_stripped(self, ext):
        # "5 sila3 beer + <<5 sila3>> (correction) + 5 sila3 bread" — the <<5>>
        # was the scribe's error and is deleted; only the two real allotments remain.
        q, u = ext.extract_quantity(
            "5(disz) sila3 kasz 5(disz) sila3 <<5(disz) sila3>> ninda"
        )
        assert q == 10.0 and u == "sila3"

    def test_correction_does_not_add_quantity(self, ext):
        # A plain quantity with a crossed-out unit must not double-count.
        # "3 ban2 <<3 ban2>> gur" → only 3 ban2 = 30 sila3 (correction discarded).
        q, u = ext.extract_quantity("3(ban2) <<3(ban2)>> gur")
        assert q == 30.0 and u == "sila3"


class TestKu3BiSilverNote:
    """ku3-bi ("its silver [equivalent]") introduces a weight annotation, not grain."""

    def test_standalone_ku3bi_not_grain(self, ext):
        # "ku3-bi 6(asz) gin2-kam" = "its silver is 6 gin2" — asz here is a
        # counting unit, NOT the grain-capacity gur-scale unit.  Must not
        # produce 1800 sila3.
        assert ext.extract_quantity("ku3-bi 6(asz@c) gin2-kam") == (None, None)

    def test_grain_before_ku3bi_preserved(self, ext):
        # "N sila3 commodity ku3-bi M gin2" — the grain quantity before the
        # silver note must still be extracted.
        q, u = ext.extract_quantity("1(ban2) 8(disz) sila3 lal3 ku3-bi 1(u) 5/6(disz) gin2")
        assert u == "sila3" and q == 18.0  # 1 ban2 (10) + 8 disz (8)

    def test_pure_ku3bi_line_none(self, ext):
        # Whole line is just the silver note with no preceding grain quantity.
        # ku3-bi stripped → empty string → (None, None).
        assert ext.extract_quantity("ku3-bi 3(disz) 1/2(disz) gin2 5(disz) sze") == (None, None)
