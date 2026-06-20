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
