"""The composed :class:`ATFExtractor` -- a thin assembly of concern mixins."""

from typing import Optional

from atf_pipeline.extract_dates import DateMixin
from atf_pipeline.extract_entities import EntityMixin
from atf_pipeline.extract_quantity import QuantityMixin
from atf_pipeline.extract_structure import StructureMixin
from atf_pipeline.patterns import ExtractorBase
from atf_pipeline.text import TextMixin


class ATFExtractor(
    ExtractorBase,
    TextMixin,
    QuantityMixin,
    EntityMixin,
    DateMixin,
    StructureMixin,
):
    """
    Extract transaction records from Ur III administrative ATF tablets.

    Supported extraction patterns (in priority order):

    ISSUERS
      A. ki NAME-ta        Line starts with "ki NAME-ta" (ablative postposition)
      B. ki NAME           Line starts with "ki NAME" (abbreviated ablative)
      C. NAME ki / NAME ki2  Line ends with "ki" (older corpus convention)
      D. INST-ta           Institution name + ablative -ta (e2-X-ta, guru7-ta)
      E. kiszib3 NAME      Seal authority — used as fallback issuer

    RECIPIENTS
      F. NAME szu ba-ti    Inline receipt formula
      G. szu ba-ti alone   Standalone receipt → previous name line is recipient
      H. NAME i3-dab5      Alternative receipt formula
      I. N(u) sze NAME     Inline distribution (quantity + barley + name)
      J. ba-an-szum2       Dative "was given" with preceding -ra name

    FIELD ALLOCATIONS (whole-tablet scan)
      K. qty / NAME engar  Grain allocation to farmer; szabra is issuer
         repeated pairs with deferred or leading szabra labels

    AGENTS
      L. giri3 NAME        Responsible official

    DATES
      - iti [month]        Month line
      - mu [year-name]     Year name (king identification via fragment matching)
      - u4 N(-kam)         Day line

    Quantity system (all normalised to sila3):
      szargal=64,800,000  szar'u=10,800,000  szar2=1,080,000
      gesz'u=180,000  gesz2=18,000  asz/gur=300
      barig=60  ban2=10  disz/sila3=1
      Fractional coefficients (1/2(disz) etc.) are handled.
    """

    def __init__(self, default_king: Optional[str] = None) -> None:
        self._default_king = default_king
