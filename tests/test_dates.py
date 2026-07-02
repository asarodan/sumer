"""King / year-name resolution across all five Ur III reigns, including the
us2-sa ('year after') precedence that first-match-wins depends on, king-less
year-name resolution across all royal formularies, accession years, and
cross-reign ambiguity handling."""
import pytest


def _yr(ext, mu):
    date, _ = ext._parse_date(["mu " + mu])
    return (date.king, date.year_number) if date else (None, None)


class TestYearResolution:
    @pytest.mark.parametrize("mu,expected", [
        # Šulgi (resolved via default_king when no king name in the dateline).
        # Standard chronology: wall of the land = Š37 (Sallaberger OBO 160/3).
        ("bad3 ma-da ba-du3",                         ("Šulgi", 37)),
        ("us2-sa bad3 ma-da mu-du3",                  ("Šulgi", 38)),
        ("e2 puzur4-isz-{d}da-gan ba-du3",            ("Šulgi", 39)),
        ("ki-masz{ki} hu-ur5-ti{ki} u3 ma-da-bi u4 asz-a ba-hul", ("Šulgi", 46)),
        ("us2-sa ki-masz{ki} ba-hul",                 ("Šulgi", 47)),
        ("ha-ar-szi{ki} ki-masz{ki} hu-ur5-ti{ki} u3 ma-da-bi u4 asz-a ba-hul",
                                                      ("Šulgi", 48)),
        ("si-mu-ru-um{ki} lu-lu-bu{ki} a-ra2 1(u) la2 1(disz)-kam ba-hul",
                                                      ("Šulgi", 44)),
        ("ur-bi2-lum{ki} si-mu-ru-um{ki} lu-lu-bu{ki} u3 kar2-har{ki}-sze3 "
         "asz-sze3 sag-bi szu-tibir-ra im-mi-ra",     ("Šulgi", 45)),
        ("an-sza-an{ki} ba-hul",                      ("Šulgi", 34)),
        # Amar-Suen
        ("amar-{d}suen lugal-e ur-bi2-lum{ki} mu-hul", ("Amar-Suen", 2)),
        ("gu-za {d}en-lil2-la2 ba-dim2",               ("Amar-Suen", 3)),
        ("en-mah-gal-an-na en {d}nanna ba-hun",        ("Amar-Suen", 4)),
        ("en-unu6-gal {d}inanna ba-hun",               ("Amar-Suen", 5)),
        ("hu-uh2-nu-ri{ki} ba-hul",                    ("Amar-Suen", 7)),
        ("en eridu{ki} ba-hun",                        ("Amar-Suen", 8)),
        # Šu-Suen: boat of Enki = ŠS2, Martu wall = ŠS4 (standard chronology)
        ("ma2 {d}en-ki ba-ab-du8",                     ("Šu-Suen", 2)),
        ("ma2-dara3-abzu {d}en-ki ba-ab-du8",          ("Šu-Suen", 2)),
        ("us2-sa ma2 {d}en-ki ba-ab-du8",              ("Šu-Suen", 3)),
        ("si-ma-num2{ki} ba-hul",                      ("Šu-Suen", 3)),
        ("us2-sa si-ma-num2{ki} ba-hul",               ("Šu-Suen", 4)),
        ("{d}szu-{d}suen lugal-e bad3 mar-tu mu-ri-iq-ti-id-ni-im mu-du3",
                                                       ("Šu-Suen", 4)),
        ("us2-sa {d}szu-{d}suen lugal uri5{ki}-ma-ke4 bad3 mar-tu mu-du3",
                                                       ("Šu-Suen", 5)),
        ("na-ru2-a-mah ba-du3",                        ("Šu-Suen", 6)),
        ("ma-da za-ab-sza-li{ki} ba-hul",              ("Šu-Suen", 7)),
        ("ma2-gur8-mah ba-dim2",                       ("Šu-Suen", 8)),
        ("e2 {d}szara2 ba-du3",                        ("Šu-Suen", 9)),
        # Ibbi-Suen: Simurrum = IS3 (standard chronology)
        ("i-bi2-{d}suen lugal-e si-mu-ru-um{ki} mu-hul", ("Ibbi-Suen", 3)),
    ])
    def test_year(self, ext, mu, expected):
        assert _yr(ext, mu) == expected

    def test_us2sa_takes_precedence_over_base(self, ext):
        # The "year after the wall" (38) must not collapse into the base wall
        # year (37); the us2-sa fragment is checked first.
        assert _yr(ext, "us2-sa bad3 ma-da mu-du3")[1] == 38
        assert _yr(ext, "bad3 ma-da ba-du3")[1] == 37


class TestKinglessResolution:
    """Year-names without a king name must search every royal formulary."""

    def test_kingless_amar_suen_year(self, ext):
        # "en of Eridu installed" belongs uniquely to Amar-Suen: the resolver
        # must find it even though the default king is Šulgi.
        assert _yr(ext, "en eridu{ki} ba-hun") == ("Amar-Suen", 8)

    def test_kingless_szu_suen_year(self, ext):
        assert _yr(ext, "si-ma-num2{ki} ba-hul") == ("Šu-Suen", 3)

    def test_cross_reign_ambiguity_left_unresolved(self, ext):
        # Šašrum was destroyed under both Šulgi (42) and Amar-Suen (6); a
        # king-less formula must not be guessed.  The default king is kept
        # but no year number is assigned.
        king, yr = _yr(ext, "sza-asz-ru{ki} ba-hul")
        assert yr is None

    def test_karzida_ambiguity_left_unresolved(self, ext):
        # en of Nanna of Karzida installed = Šulgi 43 AND Amar-Suen 9.
        king, yr = _yr(ext, "en {d}nanna kar-zi-da ba-hun")
        assert yr is None


class TestAccessionYears:
    @pytest.mark.parametrize("mu,expected", [
        ("{d}amar-{d}suen lugal",   ("Amar-Suen", 1)),
        ("{d}szu-{d}suen lugal",    ("Šu-Suen", 1)),
        ("{d}i-bi2-{d}suen lugal",  ("Ibbi-Suen", 1)),
        # "year after <king became> king" names the second year
        ("us2-sa {d}szu-{d}suen lugal", ("Šu-Suen", 2)),
    ])
    def test_accession(self, ext, mu, expected):
        assert _yr(ext, mu) == expected

    def test_lugal_e_is_not_accession(self, ext):
        # "lugal-e" (ergative) introduces an event clause; if the event is
        # unrecognised the year must stay unresolved rather than become 1.
        king, yr = _yr(ext, "{d}szu-{d}suen lugal-e nig2 x-x mu-dim2")
        assert king == "Šu-Suen"
        assert yr is None


class TestDefaultKing:
    def test_no_default_leaves_king_unset(self, ext):
        # Unrecognised year-name, no default king → both fields stay open.
        assert _yr(ext, "x x x ba-hul") == (None, None)

    def test_default_king_stamps_unresolved(self, ext_sulgi):
        # With an explicit default, an unrecognised year-name gets the default
        # king but never an invented year number.
        assert _yr(ext_sulgi, "x x x ba-hul") == ("Šulgi", None)

    def test_default_king_never_overrides_unique_match(self, ext_sulgi):
        # A year-name that resolves uniquely to another king must win over
        # the default.
        assert _yr(ext_sulgi, "en eridu{ki} ba-hun") == ("Amar-Suen", 8)


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
