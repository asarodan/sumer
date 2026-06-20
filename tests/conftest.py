"""Shared fixtures for the atf_pipeline test suite.

The tests are pure unit tests over synthetic ATF snippets — they do NOT require
the ~87 MB CDLI corpus dump, so the suite runs anywhere in well under a second.
"""
import pytest

from atf_pipeline import ATFExtractor, Normalizer


@pytest.fixture(scope="session")
def ext() -> ATFExtractor:
    """A Šulgi-defaulted extractor (matches the pipeline's CLI default)."""
    return ATFExtractor(default_king="Šulgi")


@pytest.fixture(scope="session")
def normalizer() -> Normalizer:
    return Normalizer()
