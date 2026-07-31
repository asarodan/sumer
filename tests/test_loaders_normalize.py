"""CDLI export parsing and entity normalisation."""
import pytest

from atf_pipeline import parse_cdli_export


class TestParseExport:
    def test_splits_tablets_by_header(self):
        text = (
            "&P100001 = Test 01\n@tablet\n1. 5(asz) sze gur\n2. ki lugal-ta\n"
            "&P100002 = Test 02\n@tablet\n1. 3(asz) ziz2 gur\n"
        )
        tablets = parse_cdli_export(text)
        assert set(tablets) == {"P100001", "P100002"}
        assert "1. 5(asz) sze gur" in tablets["P100001"]

    def test_header_line_retained(self):
        tablets = parse_cdli_export("&P100003 = Solo\n1. 1(asz) sze gur\n")
        assert tablets["P100003"][0].startswith("&P100003")

    def test_browser_noise_dropped(self):
        text = (
            "&P100004 = Noisy\n"
            "https://cdli.ucla.edu/P100004\n"
            "1. 2(asz) sze gur\n"
        )
        tablets = parse_cdli_export(text)
        assert all("cdli" not in ln for ln in tablets["P100004"])

    def test_empty_text(self):
        assert parse_cdli_export("") == {}


class TestNormalizer:
    def test_title_mapped(self, normalizer):
        assert normalizer.normalize_name("dub-sar") == "scribe (dub-sar)"

    def test_none_passthrough(self, normalizer):
        assert normalizer.normalize_name(None) is None

    def test_personal_name_is_uniform_atf(self, normalizer):
        # Personal names stay in canonical ATF (not anglicised), so every node
        # shares one representation. {d} determinative is stripped.
        assert normalizer.normalize_name("ur-{d}szara2") == "ur-szara2"
        assert normalizer.normalize_name("lu2-szara2") == "lu2-szara2"

    def test_ergative_suffix_always_merged(self, normalizer):
        # -ke4 / -ke4-ne is never part of a name root → always folded.
        assert normalizer.normalize_name("ur-ba-ba6-ke4") == "ur-ba-ba6"

    def test_native_ra_ending_preserved_without_fit(self, normalizer):
        # Unfitted: ambiguous -ra is NOT stripped (lu2-dingir-ra is a real name).
        assert normalizer.normalize_name("lu2-dingir-ra") == "lu2-dingir-ra"

    def test_evidence_based_suffix_merge(self):
        from atf_pipeline import Normalizer
        n = Normalizer()
        # ur-szul-gi is attested bare → its dative form merges; lu2-dingir is
        # NOT attested bare → lu2-dingir-ra is left intact.
        n.fit(["ur-szul-gi", "ur-szul-gi-ra", "lu2-dingir-ra"])
        assert n.normalize_name("ur-szul-gi-ra") == "ur-szul-gi"
        assert n.normalize_name("lu2-dingir-ra") == "lu2-dingir-ra"
