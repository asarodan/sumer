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

    def test_unknown_name_cleaned_not_dropped(self, normalizer):
        out = normalizer.normalize_name("ur-{d}szara2")
        assert out and "ur" in out.lower()

    def test_none_passthrough(self, normalizer):
        assert normalizer.normalize_name(None) is None
