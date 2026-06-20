"""King / year-name resolution across all five Ur III reigns, including the
us2-sa ('year after') precedence that first-match-wins depends on."""
import pytest


def _yr(ext, mu):
    date, _ = ext._parse_date(["mu " + mu])
    return (date.king, date.year_number) if date else (None, None)


class TestYearResolution:
    @pytest.mark.parametrize("mu,expected", [
        # Šulgi (resolved via default_king when no king name in the dateline)
        ("bad3 ma-da ba-du3",                         ("Šulgi", 43)),
        ("us2-sa bad3 ma-da mu-du3",                  ("Šulgi", 44)),
        # Amar-Suen
        ("amar-{d}suen lugal-e ur-bi2-lum{ki} mu-hul", ("Amar-Suen", 2)),
        # Šu-Suen
        ("{d}szu-{d}suen lugal-e bad3 mar-tu mu-du3",  ("Šu-Suen", 2)),
        ("us2-sa {d}szu-{d}suen lugal bad3 mar-tu",    ("Šu-Suen", 3)),
        # Ibbi-Suen
        ("i-bi2-{d}suen lugal-e si-mu-ru-um{ki} mu-hul", ("Ibbi-Suen", 2)),
    ])
    def test_year(self, ext, mu, expected):
        assert _yr(ext, mu) == expected

    def test_us2sa_takes_precedence_over_base(self, ext):
        # The "year after the wall" (44) must not collapse into the base wall
        # year (43); the us2-sa fragment is checked first.
        assert _yr(ext, "us2-sa bad3 ma-da mu-du3")[1] == 44
        assert _yr(ext, "bad3 ma-da ba-du3")[1] == 43


class TestMonthDay:
    def test_month_extracted(self, ext):
        date, _ = ext._parse_date(["iti sze-sag11-ku5", "mu en ba-hun"])
        assert date.month == "sze-sag11-ku5"

    def test_day_extracted(self, ext):
        date, _ = ext._parse_date(["iti szu-numun u4 5-kam"])
        assert date.day == 5

    def test_no_date_returns_none(self, ext):
        date, raw = ext._parse_date(["1. 5(asz) sze gur", "2. ki lugal-ta"])
        assert date is None and raw is None
