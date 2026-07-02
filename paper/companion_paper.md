# The Ur III Grain Ledger: Extracting and Validating an Ancient Economy at Scale

*A companion research paper to the digital exhibition "The Ur III Grain Ledger"*

**Daniel Asaro**

---

## Abstract

This paper documents the data, methodology, and findings behind a digital exhibition on the grain economy of the Ur III state (c. 2112–2004 BCE), built from a custom computational pipeline that parses the full Cuneiform Digital Library Initiative (CDLI) export of 135,199 Ur III administrative tablets. The pipeline extracts 254,133 economic transactions from 56,906 tablets, together with resolved issuers and recipients for 36,851 transactions and resolved regnal-year dates for 71,301. Rather than presenting this extraction as uniformly reliable, the paper is organized around a deliberate two-tier confidence structure: a large-sample layer (the full extraction, useful for aggregate patterns but not independently verified) and a small-sample layer (90 tablets whose extracted grain totals were checked against the ancient scribe's own recorded arithmetic and match to within one unit). Findings are reported from both layers with the supporting tier named explicitly in each case. On the verified layer, the modal grain allocation is exactly 60 *sila₃* — the standard adult monthly ration known from prior philological scholarship — and grain volume is highly concentrated (per-entry Gini coefficient 0.873, with substantial caveats about what that number does and does not measure). On the full-corpus layer, cereal grain dominates recorded volume (roughly 2.4 million *gur*, of which barley alone is 88%), transaction sizes are approximately log-normal with an extreme heavy tail (the largest 1% of transactions carry 54% of recorded volume), and the barley exchange network of 1,999 named agents shows reciprocity significantly above — and global cohesion significantly below — a degree-preserving random null model, consistent with a compartmentalized, largely one-directional redistributive flow structure. Two methodological episodes are documented in detail because they shaped the project's central argument: the discovery and correction of systematic errors in the pipeline's own royal chronology table, and the construction of an arithmetic validation harness from the scribes' own grand-total lines. The central claim of the paper is methodological: in a field with no pre-existing large-scale ground truth, honesty about *where* a number comes from is as important as the number itself.

---

## 1. Introduction

The Third Dynasty of Ur — Ur III, roughly 2112 to 2004 BCE — administered southern Mesopotamia through one of the most densely documented bureaucracies of the ancient world. Provincial centers at Drehem (ancient Puzriš-Dagan), Umma, Girsu, Nippur, and Ur generated clay tablets recording individual grain rations, livestock transfers, field allocations, and annual institutional accounts, each sealed or signed by responsible officials and dated by royal year-name. Tens of thousands of these tablets survive. Over more than a century of Assyriological work, most of the published corpus has been transliterated into standardized Latin-character notation, and the Cuneiform Digital Library Initiative (CDLI) has aggregated those transliterations into a single machine-readable export — 135,199 tablets classified as Ur III at the time of this project's corpus snapshot.

That scale creates an opportunity. Ur III economic history has been written almost entirely through close philological reading of individual archives: Sallaberger's synthesis of the administrative system (1999), Steinkeller's account of the *bala* tribute mechanism connecting the provinces to the crown (1987), Waetzoldt's reconstruction of ration scales from textile-industry registers (1972), and Englund's work on the barley-denominated accounting system (2012), among others. This scholarship established the qualitative architecture of the Ur III economy — a redistributive system in which grain flowed from provincial producers through a hierarchy of accountable officials toward central institutions, and back out as standardized rations. What it could not do, working tablet by tablet, is measure that architecture: how much grain, how concentrated, through how many hands, on what temporal rhythm. A corpus-wide quantitative picture has not previously been assembled, and assembling one is the underlying goal of the digital exhibition this paper accompanies.

But the scale also creates a problem that is easy to understate. Extracting structured data from 135,199 tablets means extracting it from tablets no human has re-checked line by line. Every downstream number — every total, every distribution, every network statistic — inherits the unverified status of the extraction that produced it, unless something independent confirms it. Machine-learning evaluation practice normally answers this with a held-out labeled test set; no such labeled resource exists for Ur III administrative content at any meaningful scale. This paper's response is twofold. First, the extraction pipeline itself is built defensively: deterministic rules rather than statistical inference, each rule pinned by regression tests, with particular attention to *negative* classification — recognizing what is not grain — because in this corpus the dominant extraction error is counting things that merely look like grain. Second, and more importantly, the project exploits the one place in the corpus where an ancient author performed and recorded the same computation the pipeline attempts: the scribal grand-total line. Where the pipeline's sum over a tablet's line items equals the total the scribe himself wrote, that tablet's extraction is verified by a source wholly external to the pipeline. This check yields a small but genuinely validated subset — 90 tablets — that anchors the project's strongest claims.

The paper is organized as follows. Section 2 describes the corpus and the Sumerian metrological system. Section 3 describes the extraction pipeline. Section 4 details the false-positive control methodology. Section 5 documents a cautionary episode: the discovery that the pipeline's own royal chronology table contained systematic errors, and what fixing them changed. Section 6 describes the arithmetic validation harness and defines the two-tier confidence structure used throughout. Sections 7–9 report findings — full-corpus aggregates, verified-subset distributions, and network structure respectively — with each claim tied to its supporting tier. Section 10 states limitations. Section 11 concludes by stating plainly what the numbers in this paper do and do not license a reader to believe.

---

## 2. The Corpus and the Measurement System

### 2.1 The CDLI export

The source corpus is the CDLI bulk export in ATF (ASCII Transliteration Format): 135,199 tablets classified as Ur III, spanning the major provincial archives (Drehem, Umma, Girsu, Nippur, Ur) and smaller groups from other sites. Each tablet is a sequence of transliterated lines organized by physical surface (`@obverse`, `@reverse`, seals, envelopes), with editorial markers for physical damage (`[...]` for lost text, `#` for damaged signs, `?` for uncertain readings) and semantic determinatives (`{d}` before divine names, `{ki}` after place names). The corpus is a living scholarly resource rather than a fixed dataset: transliteration conventions vary across decades of contributors, some tablets are only partially encoded, and coverage reflects the accidents of excavation, publication, and digitization rather than any sampling design. Three consequences follow for everything in this paper: all counts are lower bounds (damage suppresses data), all temporal and geographic distributions reflect archival survival rather than ancient reality, and any pipeline must tolerate inconsistent input without silently producing garbage.

### 2.2 The sexagesimal capacity system

Grain in Ur III accounts is measured in a base-60 capacity system (Table 1). The base unit is the *sila₃*, conventionally taken as roughly one liter; the workhorse accounting unit is the *gur* of 300 *sila₃*. Two features of this system shape the entire extraction problem. First, the same numeral-classifier grammar serves every commodity: `2(aš) gur` is two *gur* of barley, but visually parallel constructions count reed bundles, cattle, and silver. Nothing about the numerals themselves says "grain." Second, the system is multiplicative, with large-denomination tokens reaching 180,000 *sila₃* (*šar₂*) — so a single misclassified large-denomination line can inject phantom volume equivalent to hundreds of real tablets. Precision on the distributional tail therefore dominates aggregate accuracy: a parser can be right on 99% of lines and still be badly wrong on total volume.

**Table 1.** The Ur III sexagesimal capacity system.

| Token | Relationship | *Sila₃* equivalent |
|---|---|---|
| *sila₃* | base unit (≈1 liter) | 1 |
| *ban₂* | 10 × *sila₃* | 10 |
| *barig* | 6 × *ban₂* | 60 |
| *gur* | 5 × *barig* | 300 |
| *šar₂* | 600 × *gur* | 180,000 |

---

## 3. The Extraction Pipeline

The pipeline is written in pure Python with no machine-learning components. This is a deliberate choice, not a limitation: every extraction decision is a readable rule that can be inspected, tested, and argued with, which matters in a project whose central commitment is that readers should be able to see where numbers come from. Processing runs in five stages.

**Structural segmentation.** Each tablet is split into accounting sections at structural keywords — *šunigin* ("total"), *sza₃-bi-ta* ("therefrom," opening an expenditure block), *sag-nig₂-gur₁₁* ("capital," opening an income block). Seal impressions and envelope surfaces are stripped before parsing, because they repeat personal names in positions that would otherwise generate false attributions. Non-administrative genres (lexical lists, royal inscriptions, school exercises, non-Sumerian texts) are rejected on header inspection.

**Quantity parsing.** Within each section, numeral-classifier sequences are parsed and normalized to *sila₃* via Table 1. A line yields a grain quantity only if it survives the negative-classification filters of Section 4; otherwise it is routed to the appropriate non-grain channel (animals counted in head, silver in *gin₂*, labor in worker-days) or discarded. Lines containing damage brackets around the quantity are suppressed rather than half-read.

**Attribution.** Issuer, recipient, and intermediary are resolved from recurring grammatical formulas: *ki X-ta* ("from X") marks the issuer; *X šu ba-ti* ("X received") marks the recipient; *giri₃ X* ("via X") marks a conveying agent; *kiszib₃ X* ("seal of X") on a receipt marks the acknowledging — that is, receiving — official. The last of these deserves a note, because it was mishandled in an earlier version of the pipeline and its correction illustrates the evidentiary style the project aims for. Whether the seal-holder on a receipt is the issuer or the recipient is not obvious from the formula alone. The corpus itself settles it: some tablets survive together with their clay envelopes, and the envelope restates the tablet's transaction in fuller wording. Tablet P133455 reads *ki lu₂-gi-na-ta / kiszib₃ ur-šuš₃-ba-ba₆* ("from Lugina; seal of Ur-Šuš-Baba"), and its own envelope restates the same transaction as *ur-šuš₃-ba-ba₆ / šu ba-ti* ("Ur-Šuš-Baba received"). The ancient scribe himself glossed the seal formula as receipt. The pipeline now attributes accordingly.

**Dating.** Ur III tablets are dated by year-names — each regnal year named after a royal deed ("the year the wall of the land was built") — plus month and day. The pipeline matches year-name strings against an almanac of known formulas per king and reduces matches to a structured (king, regnal year, month, day). Section 5 documents the substantial repair this component required.

**Prosopographic normalization.** Personal names are normalized by stripping Sumerian grammatical case suffixes, but only when the bare form is independently attested elsewhere in the corpus — a conservative rule that avoids merging distinct individuals. A patronymic scanner (*X dumu Y*, "X son of Y") anchors identity more firmly where filiation is recorded, and flags homonyms (identical names with different attested fathers) rather than conflating them.

Every rule in every stage is pinned by a regression test; the suite currently comprises 184 passing tests, each encoding either a line that must parse a particular way or a line that must not. The suite, more than any individual rule, is the pipeline's durable methodological artifact: it freezes several hundred adjudicated scribal idioms into executable form, so that improving one rule cannot silently regress another.

Run over the full corpus, the pipeline yields the totals in Table 2. These constitute the **large-sample layer** referred to throughout this paper: extensive, but verified only by the internal test suite, not by any tablet-level external check.

**Table 2.** Pipeline yield over the 135,199-tablet corpus. All counts are lower bounds.

| Output | Count |
|---|---|
| Transactions extracted | 254,133 |
| Tablets yielding ≥1 transaction | 56,906 (42%) |
| Transactions with issuer *and* recipient resolved | 36,851 (14.5%) |
| Transactions with resolved regnal year | 71,301 (28.1%) |
| Regression tests, all passing | 184 |

The 78,293 tablets yielding no transaction are not all failures: many are too damaged to parse, belong to non-economic genres, or record commodity types (textiles, metals, land) outside the pipeline's current scope.

---

## 4. Controlling False Positives

In a corpus where grain, garlic, reeds, cattle, silver, and accounting balances all share one numeral grammar, the dominant extraction error is not missing grain but eagerly counting non-grain. A naive parser that harvests every numeral-plus-capacity-unit sequence produces roughly 3.7 million *gur* of apparent grain; the filtered pipeline produces roughly 2.4 million. The difference — about a quarter of the naive total — was spurious volume, removed by a body of negative-classification rules organized into six classes.

**Non-grain capacity commodities.** Beer, oil, and dates are measured in *sila₃* and *gur* with syntax identical to grain; only the commodity word distinguishes them, and it may precede or follow the numeral depending on scribal habit.

**Animal counts.** Livestock lines use large sexagesimal numerals in positions resembling capacity lines (`5(gesz2) udu` is 300 sheep, not a grain quantity); animal terms force the line to the head-count channel.

**Seed-grain at planting rates.** Field tablets record sowing rates as capacity-per-area; the field-area logogram `GAN₂` marks these as agronomic parameters, not disbursements.

**Balance carry-forwards.** The *sza₃-bi-ta* opener restates the incoming balance of a new accounting section; re-extracting it double-counts everything above it.

**Rate-times-headcount lines.** Ration tablets sometimes record both a per-worker rate and its multiplied total; only the product is a transaction.

**Capacity tokens inside personal names.** A minority of names embed unit-like syllables; the surrounding grammatical frame, not the token, decides.

The single most consequential trap deserves its own description. On worker-ration lists, scribes counted *sila₃* using the large sexagesimal tokens — an entry like `3(gesz'u) 4(gesz2) 2(u) 3(disz)` means 11,063 *sila₃* (about 37 *gur*), with the closing total performing the *gur* conversion. A parser that applies the *gur* multiplier to those tokens inflates the line three-hundred-fold. The diagnostic is precise: genuine *gur*-scale lines carry sub-*gur* remainder tokens (*barig*, *ban₂*) alongside large denominations; ration-list lines do not. The absence of a sub-*gur* anchor beside a large-denomination token marks *sila₃* scale. This one rule accounted for the majority of the removed phantom volume — roughly 0.8 million *gur*.

Negative filtering pursued alone would discard legitimate grain lines whose commodity word is elided (common inside established grain sections, where the scribe wrote it once and assumed it). A context-sensitive recovery pass therefore re-admits unit-elided quantity lines within sections that already contain an explicit grain line — but only when no disqualifier from the taxonomy above is present. The two mechanisms are tuned adversarially against each other through the regression suite: every loosening of recovery is checked against the false-positive tests, and every new filter is checked against documented elliptical grain lines that must survive.

---

## 5. A Cautionary Episode: The Chronology Table Was Wrong

This section documents an error in the project's own infrastructure, because the way it was found and fixed is a better argument for the paper's methodology than any success story.

Ur III year-names do not contain numbers; they are event formulas ("the year Huhnuri was destroyed"), and converting them to regnal-year integers requires a lookup table assembled from Assyriological chronology scholarship. Diagnostic profiling of the pipeline's output showed a suspicious asymmetry: 39% of transactions had an identified king but only 8.7% had a year number. Investigating the gap exposed two distinct defects.

The first was structural. Most year-names never name the king — the scribe wrote "year: the en-priestess of Eridu was installed" and every reader knew whose reign it was. The pipeline's resolver, however, only consulted the fragment table of a single default king when no king was named, so year-names belonging to the other four reigns were unreachable regardless of how correct the tables were. The fix searches every reign's formulary and accepts a match only when exactly one king's table fits; formulas genuinely attested under two reigns (Šašrum was destroyed under both Šulgi and Amar-Suen; the Karzida priestess installation recurs similarly) are detected as ambiguous and deliberately left unresolved rather than guessed.

The second defect was worse: several of the table's year-number assignments were simply wrong. Cross-checking each high-frequency formula against published chronology (the standard sequence in Sallaberger 1999 and the CDLI year-name lists, verified formula by formula during this project) showed the "wall of the land" filed under Šulgi year 43 when the standard chronology places it at 37; the Martu wall under Šu-Suen 2 instead of 4; the Huhnuri campaign under Amar-Suen 9 instead of 7; Simurrum under Ibbi-Suen 2 instead of 3; and two formulas filed as Ibbi-Suen 3 and 4 that belong to years 15 and 16. Every dated analysis previously produced by the pipeline had inherited these errors silently.

Fixing both defects raised year-name resolution from 19.6% to 64.4% of tablets bearing a dateline, and — the more consequential change — replaced a blanket "default to Šulgi" rule with evidence-only attribution. The old output attributed some 90,000 transactions to Šulgi's reign, mostly as a default-stamp artifact. The corrected distribution (Amar-Suen 25,742 dated transactions; Šu-Suen 24,182; Šulgi 20,528; Ibbi-Suen 3,549) matches what archival history independently predicts, since the great Drehem and Umma archives peak under Amar-Suen and Šu-Suen. The lesson generalizes: the reference data a pipeline consults is part of the pipeline, carries its own error rate, and deserves the same adversarial verification as the parsing rules. A large sample built on a wrong lookup table is a large sample of the wrong thing.

---

## 6. Independent Validation: The Scribe's Own Arithmetic

### 6.1 The šunigin harness

Genre-typical Ur III distribution tablets close with a line the scribe computed by hand: *šunigin N gur M barig...* — "total: N *gur* M *barig*..." This is the one place in the corpus where an ancient author performed and recorded the same computation the pipeline attempts. If the pipeline's summed extraction for a tablet equals the scribe's own total, that tablet's quantity extraction is verified by a source entirely external to the pipeline, its rules, and its author.

Applying the check corpus-wide: 589 tablets carry a single, structurally unambiguous *šunigin* grain total. Of these, 463 have totals too damaged to read and 4 have no legible line items, leaving **122 checkable tablets**. The comparison is run in two passes — barley-only and all-cereal — accepting balance if either matches within one *sila₃* (absorbing scribal rounding in the smallest register). **90 of 122 balance (73.8%).**

The 32 failures were individually inspected. Roughly 22 appear to be genuine ancient arithmetic errors: re-summing the line items by hand confirms the pipeline's sum and contradicts the scribe's total, in several cases by exactly one accounting unit — the signature of a copying slip, not a parser bug. The remainder have structures outside the simple list-plus-total assumption (multi-commodity accounts whose total covers only one commodity; combined receipt-and-distribution documents). After individual review, none of the 32 shows a tractable pipeline error, which is itself evidence about extraction quality on this tablet genre — though evidence bounded by that genre.

### 6.2 What the check does and does not validate

Framed in evaluation terms: for the 90 balanced tablets, quantity extraction has demonstrated perfect precision and — because a missing or extra line item would break the sum — effectively bounded recall. Nothing comparable exists for the corpus at large; the 26% naive-to-filtered volume reduction and the 184-test suite are the only quality evidence for the other 135,109 tablets, and neither is a tablet-level guarantee. Equally important, the arithmetic constrains only quantities and commodity grouping. A tablet can balance perfectly while its issuer, recipient, or date is misread, since those fields never enter the sum. The verified subset therefore licenses distributional claims about grain amounts, and nothing else.

### 6.3 The two-tier structure

Everything reported below is tagged to one of two tiers:

- **Tier 1 (large-sample, unverified):** the full extraction — 254,133 transactions. Good for aggregate *patterns*, which are robust to scattered per-tablet errors; not a guarantee of any individual field.
- **Tier 2 (small-sample, verified):** the 90 balanced tablets — 570 grain entries, 10,980 *gur*, 223 named recipients. Small, genre-specific, and provably correct on quantities.

---

## 7. Findings I: The Full Corpus (Tier 1)

### 7.1 Volume and composition

Aggregating all capacity-measured transactions, cereal grain dominates the recorded economy: roughly 2.43 million *gur* in total, of which barley alone accounts for 2.14 million (88%), followed at a distance by flour (170 thousand), emmer (81 thousand), and wheat (27 thousand). Converting at the conventional figures for the *sila₃*, total recorded cereal is on the order of 400,000–450,000 metric tonnes — the exact tonnage depends on the contested liter-to-kilogram conversion, and nothing below depends on it. Beer, oil, and dates are each below 30,000 *gur*: culturally central commodities, but volumetrically marginal beside the grain they were made from or exchanged against. This composition is consistent with barley's documented role as the Ur III economy's staple, wage medium, and de facto unit of account (Englund 2012). By transaction *count* rather than volume, animals (47,653 head-counted transactions) and bread and beer rations rank high — a reminder that the corpus mixes archives with different institutional purposes, the Drehem livestock center prominent among them.

### 7.2 The shape of the transaction-size distribution

The 54,205 positive barley capacity transactions span nearly six orders of magnitude, from single-*sila₃* allocations to one threshing-floor receipt of 40.2 million *sila₃* (134,007 *gur*). On a logarithmic axis the body of the distribution is approximately normal — a log-normal fit gives μ = 5.17, σ = 3.29 in natural-log *sila₃* — with median 180 *sila₃* (three *barig*) and geometric mean 175, while the arithmetic mean of 11,867 *sila₃* sits nearly two orders of magnitude above the median. That gap is the signature of an extreme right tail: **the largest 1% of transactions carry 54.0% of all recorded barley volume, and the largest 10% carry 91.2%.** At tablet level the same two-regime structure appears — the median barley tablet totals 6.1 *gur* (a work-gang ration list), while just 22 of 12,087 barley-bearing tablets exceed 10,000 *gur* each (provincial granary and harvest accounts).

The honest reading of this shape is institutional, not social: the administrative record superimposes two different kinds of document — many small terminal disbursements and few enormous institutional aggregates. The concentration statistics describe *recorded flows in a mixed document population*. They are patterns of the archive, robust as patterns (no plausible per-tablet error rate reshapes a distribution built from fifty thousand observations), but they are not yet statements about the welfare of persons.

### 7.3 Temporal structure

Dated transactions distribute across reigns as: Amar-Suen 25,742, Šu-Suen 24,182, Šulgi 20,528, Ibbi-Suen 3,549. As Section 5 explained, this profile is newly credible — the previous pipeline's Šulgi-heavy profile was a default-stamp artifact — and it matches the known archival history of Drehem and Umma. It must still be read as a map of *archival survival*, not economic activity: the state did not produce half its documents in two reigns; those reigns' documents survived, were excavated, and were published at higher rates.

---

## 8. Findings II: The Verified Subset (Tier 2)

### 8.1 The standard ration, recovered from the data

Within the 90 arithmetically verified tablets (570 grain entries), the single most common entry is exactly **60 *sila₃*** — one *barig* — occurring 89 times, more than twice as often as the next value. The runners-up are 120 *sila₃* (38 occurrences), 90 *sila₃* (33), and 300 *sila₃* (27). This tiering reproduces, from arithmetic-verified data alone, the ration scale Waetzoldt (1972) reconstructed philologically from textile-industry registers: 60 *sila₃* per month for an adult worker at the base of the scale, with 90- and 120-*sila₃* grades above it. The convergence runs in both directions: it corroborates the philology with independent quantitative evidence, and it corroborates the pipeline — a systematic quantity-extraction error would not conjure the historically attested ration ladder by accident.

**Table 3.** Entry-size distribution, verified subset (570 entries).

| Percentile | *Sila₃* | Equivalent |
|---|---|---|
| 10th | 60 | 1 *barig* |
| 25th | 60 | 1 *barig* |
| 50th | 300 | 1 *gur* |
| 75th | 1,500 | 5 *gur* |
| 90th | 15,000 | 50 *gur* |
| Maximum | 361,500 | 1,205 *gur* |

### 8.2 Concentration, and what the Gini coefficient here actually measures

The Gini coefficient over the 570 verified entries is **0.873** (per tablet, 0.837; per named recipient, 0.907). The arithmetic behind these numbers is as solid as anything in this project — the quantities are scribe-verified and the computation is elementary. The *interpretation* requires three explicit constraints.

First, the distribution mixes scales. The same 570 entries contain individual monthly rations of 60 *sila₃* and institutional transfers of up to 361,500 *sila₃* — a ratio of six thousand to one within one distribution. Pooling wage-scale and warehouse-scale observations mechanically produces a high Gini almost regardless of how equal either stratum is internally. Second, the recipient-level figure is inflated by an institution: the entry *lugal* ("the king" — in context, the royal estate) appears on 33 of the 90 tablets and absorbs 306,175 *sila₃*, about 9.3% of verified volume; it is a destination, not a person. Third, the 90 tablets are a genre (simple ration lists with legible totals), not a sample of the economy.

The claim this paper actually makes is therefore narrow: *within verified ration-distribution records, grain volume is highly concentrated, because standardized small rations coexist with bulk institutional transfers in the same documentary form.* The claim it does not make — and that a reader should refuse if offered — is "Ur III society had a Gini of 0.87." For calibration, pre-industrial *income* inequality estimates compiled by Milanovic, Lindert, and Williamson (2011) run roughly 0.40–0.60; our figure is not comparable to those, because it measures transaction concentration in a mixed-scale administrative record, not personal income.

---

## 9. Findings III: The Exchange Network (Tier 1)

Restricting to barley transactions with both parties resolved yields 10,170 transactions among **1,999 named agents** connected by 4,051 distinct directed edges. Because this "attributed" subset is only a fraction of all barley transactions — attribution requires formulaic phrases that many genres omit — the network describes the documented relational skeleton, not the full flow field. With that caveat, three structural results are stable and interpretable, each tested against a degree-preserving null model (the directed configuration model, 100 randomizations), which asks: would a random network with exactly these agents and exactly these connection counts show the same feature?

**Table 4.** Network statistics versus degree-preserving null (mean ± s.d. over 100 randomizations).

| Statistic | Observed | Null model | z-score |
|---|---|---|---|
| Reciprocity | 0.066 | 0.034 ± 0.004 | +9.3 |
| Giant-component share | 84.8% | 90.4% ± 0.9% | −6.1 |
| Communities (modularity) | 57 | — | — |

**Reciprocity is low, but higher than chance.** Only 6.6% of directed ties are reciprocated — grain overwhelmingly moves one way along any given relationship, as a redistributive hierarchy predicts and a marketplace of bilateral traders does not. Yet that figure is nearly double the null expectation (z = +9.3): mutual ties are rare but systematically present, consistent with the documented role of senior officials who both receive allocations into their household accounts and disburse from them.

**The network is less globally connected than chance predicts.** The largest weakly-connected component spans 84.8% of agents, significantly *below* the null model's 90.4% (z = −6.1). Degree structure alone would knit this network tighter than it actually is; the shortfall indicates compartmentalization — clusters that keep their connections internal. Modularity detection finds 57 communities, the two largest containing 489 and 444 agents, a granularity consistent with the corpus's known archive structure (Drehem, Umma, Girsu as separate administrative worlds with sparse cross-links).

**The hubs are the philologically expected officials.** The maximum in-degree belongs to ur-Baba (grain from 68 distinct issuers) and the maximum out-degree to ba-zi (disbursements to 168 distinct recipients) — the latter consistent with the high-volume Drehem disbursement official of that name known from published texts — while over half of all agents (1,040 of 1,999) have exactly one incoming source, the signature of ordinary workers drawing from a single office. The network recovers, from raw transliteration alone, the hub-and-spoke architecture with accountable intermediary officials that Sallaberger and Steinkeller described from the texts themselves. Given Tier-1 attribution is unverified, the right reading is convergence: two independent methods — close reading and bulk extraction — arrive at the same institutional picture.

---

## 10. Limitations

Stated compactly, in roughly descending order of importance.

1. **Attribution and dating are unverified everywhere.** The šunigin harness validates quantities on 90 tablets; no comparable check exists for issuer, recipient, or date fields anywhere in the corpus. The network and temporal findings rest on rule quality and the regression suite alone.
2. **The verified subset is small and genre-bound.** 90 tablets and 570 entries, all from one documentary form. Its findings should not be generalized beyond that form without independent support.
3. **Coverage is partial and non-random.** 42% of tablets yield transactions; 14.5% of transactions have both parties; 28.1% have a year. Every filtered view shrinks the effective sample and potentially skews it toward formula-rich genres.
4. **Large samples do not cure systematic error.** Section 5 is the proof: 90,000 transactions carried a wrong king label because one lookup table and one default rule were wrong. Scale amplifies correlated errors; it does not average them away.
5. **The archive is not the economy.** Survival, excavation, and publication are all biased processes; informal and non-institutional exchange is invisible; even the recorded state economy is seen only through documents that happened to survive.
6. **No systematic literature review was performed.** Related work is cited where known, but this paper makes no priority claim ("first to...") of any kind.
7. **Residual extraction risk.** Idiosyncratic multi-level accounts may still leak double-counted totals past the balance filters; the conversion of *sila₃* to modern mass is contested and all tonnage figures are indicative only.

---

## 11. Conclusion: What These Numbers License

The two-tier structure exists so that this section can be short and unambiguous.

**A reader may take from this paper:** that the CDLI Ur III corpus supports transaction-level extraction at a scale of hundreds of thousands of records; that on an arithmetically verified subset, the modal grain allocation is exactly the 60-*sila₃* monthly ration known from prior scholarship, and recorded grain volume within that record type is highly concentrated across mixed transaction scales (Gini 0.873, with the constraints of Section 8.2); that at corpus scale, recorded cereal volume is on the order of 2.4 million *gur*, distributed log-normally with an extreme tail in which 1% of transactions carry 54% of volume; and that the attributed exchange network shows above-chance reciprocity and below-chance global cohesion — a compartmentalized, largely one-directional flow structure convergent with the redistributive model of the philological literature.

**A reader may not take from this paper:** that any individual unverified transaction is correct; that the Gini coefficient measures Ur III income or wealth inequality; that the temporal profile tracks economic activity rather than archival survival; or that any component of this work is unprecedented, since no claim of priority was checked.

The broader methodological point stands independent of any particular number. Corpus-scale computation is coming to ancient studies, and its findings will be only as trustworthy as their weakest unexamined dependency — a lookup table, a default value, an unchecked attribution rule. This project's two best decisions were defensive: pinning every parsing rule to an executable test, and finding a place where the ancient scribes themselves could audit the machine. Four thousand years later, ninety of their totals still balance. That is a small foundation, but it is bedrock, and the discipline of building on bedrock — and saying plainly which parts of the structure stand on it — is the practice this project most hopes to model.

---

## Data and Code Availability

The extraction pipeline, its 184-test regression suite, the šunigin reconciliation harness, and the analysis scripts are available in the project repository (`asarodan/sumer`). The verified 90-tablet dataset and the full transaction extraction accompany the digital exhibition as downloadable CSVs. The CDLI corpus is distributed by the Cuneiform Digital Library Initiative under its data-sharing terms.

## References

Cuneiform Digital Library Initiative (CDLI). *Ur III administrative corpus, ATF bulk export.* cdli.mpiwg-berlin.mpg.de.

Englund, R. K. (2012). "Equivalency Values and the Command Economy of the Ur III Period in Mesopotamia." In *The Construction of Value in the Ancient World*, 427–458.

Garfinkle, S. J. (2015). "Ur III Administrative Texts: Building Blocks of State Community." In *From the 21st Century B.C. to the 21st Century A.D.*

Milanovic, B., P. H. Lindert, and J. G. Williamson (2011). "Pre-Industrial Inequality." *Economic Journal* 121: 255–272.

Molina, M. (2008). "The Corpus of Neo-Sumerian Tablets: An Overview." In *The Growth of an Early State in Mesopotamia*, 19–53.

Sallaberger, W. (1999). "Ur III-Zeit." In *Mesopotamien: Akkade-Zeit und Ur III-Zeit*, OBO 160/3, 121–390.

Steinkeller, P. (1987). "The Administrative and Economic Organization of the Ur III State: The Core and the Periphery." In *The Organization of Power: Aspects of Bureaucracy in the Ancient Near East*, SAOC 46, 19–41.

Waetzoldt, H. (1972). *Untersuchungen zur neusumerischen Textilindustrie*. Rome: Centro per le Antichità e la Storia dell'Arte del Vicino Oriente.

Widell, M. (2004). "Reflections on Some Households and their Receiving Officials in the City of Ur in the Ur III Period." *Journal of Near Eastern Studies* 63: 283–290.
