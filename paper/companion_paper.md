# The Ur III Grain Ledger: Extracting and Validating an Ancient Economy at Scale

*A companion research paper to the digital exhibition "The Ur III Grain Ledger"*

**Daniel Asaro**

---

## Abstract

This paper documents the data and methodology behind a digital exhibition on the grain economy of the Ur III state (c. 2112–2004 BCE), built from a custom computational pipeline that parses the full Cuneiform Digital Library Initiative (CDLI) export of 135,199 Ur III administrative tablets. The pipeline extracts 254,133 economic transactions from 56,906 tablets. Rather than presenting this extraction as uniformly reliable, this paper is organized around a deliberate two-tier confidence structure: a large-sample layer (the full extraction, useful for aggregate patterns but not independently verified) and a small-sample layer (90 tablets whose extracted grain totals are checked against the ancient scribe's own arithmetic and match to within one unit). We report findings from both layers and are explicit throughout about which tier each claim rests on. The central methodological argument is that in a field with no pre-existing large-scale ground truth, honesty about *where* a number comes from is as important as the number itself.

---

## 1. Introduction

The Ur III state left behind one of the most densely documented bureaucracies of the ancient world: tens of thousands of clay tablets recording grain rations, herd transfers, and institutional accounts, transliterated over decades of Assyriological work and now aggregated by the CDLI into a single machine-readable corpus. This scale creates an opportunity — a corpus-wide quantitative picture of the Ur III grain economy has not previously been assembled — but it also creates a problem that is easy to understate: extracting structured data from tens of thousands of tablets means extracting it from tablets no human has re-checked line by line. Any claim built on that extraction inherits its unverified status unless something independent confirms it.

This paper's organizing principle is to never let that distinction blur. Section 2 describes the corpus and the extraction pipeline. Section 3 describes the one mechanism available for independently verifying extraction accuracy at the level of an individual tablet — matching the pipeline's summed output against the ancient scribe's own recorded total. Section 4 reports findings, split explicitly by which of the two data tiers supports each claim. Section 5 states, plainly, what the numbers in this paper do and do not license someone to conclude.

---

## 2. The Corpus and the Pipeline

The source corpus is the CDLI bulk ATF (ASCII Transliteration Format) export of 135,199 tablets classified as Ur III. Each tablet is a sequence of transliterated lines recording a distinct administrative event — a grain disbursement, a livestock transfer, a sealed receipt — usually including some combination of a quantity, a commodity, an issuing party, a receiving party, and a date tied to a king's regnal year.

The extraction pipeline is rule-based rather than machine-learning-based: quantities are parsed from the Sumerian sexagesimal capacity system (Table 1), commodities are identified from context-sensitive keyword rules, and issuer/recipient/date fields are resolved from a set of recurring grammatical formulas (e.g., *ki X-ta*, "from X"; *X šu ba-ti*, "X received"; a year-name matched against a reign-by-reign almanac of known royal formulas). Every rule is backed by a regression test, and the current suite includes 184 passing tests spanning quantity parsing, commodity classification, recipient/issuer attribution, and date resolution.

**Table 1.** The Ur III sexagesimal capacity system.

| Token | *Sila₃* equivalent |
|---|---|
| *sila₃* | 1 |
| *ban₂* | 10 |
| *barig* | 60 |
| *gur* | 300 |
| *šar₂* | 180,000 |

Run over the full corpus, the pipeline currently extracts:

- 254,133 transactions from 56,906 tablets (42% of the corpus yields at least one transaction; the remainder are too damaged, non-administrative in genre, or record commodities outside the pipeline's current scope)
- 36,851 transactions (14.5%) with both issuer and recipient resolved
- 71,301 transactions (28.1%) with a resolved regnal year

This is the **large-sample layer**. It is large, but "large" here describes coverage of the corpus, not confidence in any individual number. Nothing in this layer has been checked against an outside source — it is simply the pipeline's best current output, subject to whatever systematic errors the regression tests have not yet caught.

---

## 3. An Independent Check: The Scribe's Own Arithmetic

A subset of Ur III distribution tablets follow a simple, recognizable structure: a list of grain entries followed by a single closing line where the scribe wrote the sum — the *šunigin*, "grand total" — by hand. This is the one place in the corpus where an ancient author performed and recorded the same computation the pipeline is trying to reconstruct. If the pipeline's summed extraction matches the scribe's own total, that specific tablet's extraction is verified by a source entirely external to the pipeline itself.

Applying this check across the corpus: of 135,199 tablets, 589 contain a single, legible *šunigin* grain total in this simple structure. Of those, 463 have damaged or illegible totals and 4 have no legible line items, leaving 122 tablets where the check can actually run. **90 of those 122 (73.8%) balance** — the pipeline's sum matches the scribe's total to within one *sila₃*.

Inspecting the 32 that do not balance suggests most are not pipeline errors: roughly 22 appear to be genuine ancient scribal arithmetic mistakes (confirmed by manually re-summing the line items against the tablet's own total), and the remaining cases involve tablet structures (multi-commodity accounts, dual receipt/distribution formats) that fall outside the simple single-total assumption the check requires.

These 90 tablets constitute the **small-sample layer**: 570 individual grain entries, 10,980 *gur* of cereal, 223 named recipients, 19 named issuers. Every quantity in this layer is provably correct in a way nothing in the large-sample layer is. The tradeoff is size — 90 tablets is a narrow base for any claim about "the Ur III economy" as a whole, and this paper does not treat it as one.

---

## 4. Findings, by Tier

### 4.1 Large-sample layer: aggregate structure

Across the full extraction, cereal grain (barley, emmer, wheat, and processed grain products) accounts for the overwhelming majority of capacity-measured volume, with barley alone responsible for roughly 86% of it. Transaction sizes span many orders of magnitude and are approximately log-normal in their body, with a heavy right tail — a small number of very large transfers alongside a much larger number of small, similarly-sized entries. Restricting to transactions with both parties resolved yields a directed exchange network of 1,999 named agents; it exhibits low but non-trivial reciprocity relative to a randomized comparison network, consistent with grain moving mostly in one direction — from producers, through intermediary officials, toward central institutional stores — rather than back and forth between trading partners.

These findings describe *patterns*, and patterns are the kind of claim large samples are good for: an isolated bad extraction on any single tablet does not meaningfully move a shape computed over tens of thousands of transactions. What large sample size does not do is guarantee that the pipeline's underlying field-level extraction (which quantity belongs to which commodity, which name is the issuer versus the recipient) is correct on any given transaction — that would require the same kind of check performed in Section 3, run at this scale, which has not been done.

### 4.2 Small-sample layer: verified quantities

Within the 90 verified tablets, the single most common individual grain entry is exactly 60 *sila₃* (one *barig*) — consistent with the standard adult monthly ration attested in prior Assyriological ration-register scholarship (Waetzoldt 1972). The distribution of entry sizes is markedly unequal: computing the Gini coefficient over the 570 verified entries yields 0.873.

This number requires more qualification than the pattern-level findings above, for reasons specific to what it is measuring, not to sample size alone:

- The 570 entries mix individual rations (as small as 60 *sila₃*) with institutional bulk transfers (as large as 361,500 *sila₃*) in a single distribution. Combining a wage-scale payment and a warehouse-scale transfer into one inequality statistic will produce a high Gini coefficient close to unavoidably, regardless of how equal the *individual worker* ration scale actually was — so 0.873 should be read as "grain-transaction volume in this record type is concentrated across very different transaction scales," not as a direct measure of income or wealth inequality among people.
- The 90 tablets are a specific genre (simple ration lists with a legible closing total), not a random sample of Ur III administrative documents; other document types (multi-commodity ledgers, installment accounts) were excluded from this check by construction and may have different internal distributions.
- 90 tablets and 223 named recipients is a small base for any claim intended to generalize beyond this specific record set.

The honest version of this finding is narrow: *within this verified sample of ration-distribution tablets, recorded grain volume is highly concentrated, and the standard adult ration size matches prior philological scholarship.* It is not: "Ur III society had a Gini coefficient of 0.873."

---

## 5. What These Numbers Do and Do Not License

It is worth stating directly, rather than leaving implicit, what follows from the two-tier structure above.

**Supported claims:** the corpus contains grain-economy data at a scale not previously assembled computationally; the aggregate shape of that data (commodity composition, transaction-size distribution, network structure) is a stable, large-sample pattern; a specific 90-tablet subset has been independently verified against internal ancient arithmetic and its findings (ration scale, entry-level concentration) can be stated with real confidence, scoped to that subset.

**Not supported by this paper alone:** any claim that the pipeline's field-level attribution (who issued to whom, on what date) is reliable outside the 90 verified tablets; any claim that the exhibition or this paper is the first computational treatment of this kind in the field, since no systematic literature review was performed to establish that; any claim that the Gini coefficient measures broad economic inequality across Ur III society rather than concentration within a specific administrative record type.

This is, admittedly, a more conservative set of claims than a first draft of this project made. That draft is being deliberately set aside in favor of this version, on the view that a public-facing project citing quantitative findings from an ancient corpus should make its confidence levels visible rather than let a single polished number stand in for all of them.

---

## Data and Code Availability

The extraction pipeline, its regression test suite, and the scribal-arithmetic validation harness are available in the project repository. The verified 90-tablet dataset and the full transaction extraction are both available as downloadable CSVs alongside the accompanying exhibition.

---

## References

Cuneiform Digital Library Initiative (CDLI). *Ur III administrative corpus, ATF bulk export.* cdli.mpiwg-berlin.mpg.de.

Englund, R. K. (2012). Equivalency Values and the Command Economy of the Ur III Period in Mesopotamia. In *The Construction of Value in the Ancient World*, 427–458.

Sallaberger, W. (1999). Ur III-Zeit. In *Mesopotamien: Akkade-Zeit und Ur III-Zeit*, OBO 160/3, 121–390.

Steinkeller, P. (1987). The Administrative and Economic Organization of the Ur III State: The Core and the Periphery. In *The Organization of Power: Aspects of Bureaucracy in the Ancient Near East*, SAOC 46, 19–41.

Waetzoldt, H. (1972). *Untersuchungen zur neusumerischen Textilindustrie*. Rome: Centro per le Antichità e la Storia dell'Arte del Vicino Oriente.
