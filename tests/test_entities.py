"""Issuer / recipient / agent extraction from administrative formulae,
including the debit-verb (ba-zi) bleed fix."""
import pytest


class TestIssuer:
    def test_ablative_with_debit_verb(self, ext):
        # "ki na-sa6-ta ba-zi" ("expended from Nasa") → issuer Nasa, NOT
        # "na-sa6-ta ba-zi".
        assert ext._extract_issuer("ki na-sa6-ta ba-zi") == "na-sa6"

    def test_internal_ta_name_kept_whole(self, ext):
        assert ext._extract_issuer("ki in-ta-e3-a-ta ba-zi") == "in-ta-e3-a"

    def test_genuine_person_bazi_preserved(self, ext):
        # "ki ba-zi-ta" is the person Bazi — the name must survive intact.
        assert ext._extract_issuer("ki ba-zi-ta") == "ba-zi"

    def test_abbreviated_ablative_strips_verb(self, ext):
        # No -ta to bound the name; the trailing debit verb is stripped.
        got = ext._extract_issuer("ki {d}iszkur-illat ba-zi")
        assert "ba-zi" not in got and "iszkur-illat" in got

    def test_title_stripped(self, ext):
        assert ext._extract_issuer("ki lu2-dingir-ra szabra-ta ba-zi") == "lu2-dingir-ra"

    def test_plain_ablative(self, ext):
        assert ext._extract_issuer("ki ur-{d}szara2-ta") in ("ur-szara2", "ur-{d}szara2")


class TestRecipientAndAgent:
    def test_inline_shu_ba_ti(self, ext):
        assert ext._extract_recipient_inline("ku3-ga-ni szu ba-ti") == "ku3-ga-ni"

    def test_idab5_recipient(self, ext):
        # {d} divine determinative is normalised away by _clean_atf_name.
        assert ext._extract_recipient_idab5("lu2-{d}nanna i3-dab5") == "lu2-nanna"

    def test_giri3_agent(self, ext):
        assert ext._extract_agent("giri3 ur-{d}szul-pa-e3") == "ur-szul-pa-e3"

    def test_ugula_agent(self, ext):
        assert ext._extract_agent("ugula da-da") == "da-da"
