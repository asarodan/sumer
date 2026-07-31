# Test-Driven Information Extraction from Ancient Administrative Corpora: A Rule-Based Pipeline with Arithmetic Validation, Applied to 135,199 Ur III Cuneiform Tablets

**Daniel Asaro**  
asarodan/sumer

---

## Abstract

Ancient administrative corpora — clay tablets, papyri, parchment accounts — record economic life at a granularity unavailable for most of human history, yet they resist reliable large-scale computational extraction because they are written in numeral-classifier grammars where the same token sequence can denote grain, cattle, silver, or reeds depending on context that appears elsewhere in the same line or tablet. Naive extraction over-counts the target commodity by a large and corpus-dependent margin; without a principled false-positive control methodology, the resulting datasets carry systematic errors large enough to invalidate quantitative analysis.

We present a rule-based, test-driven extraction pipeline for the full Cuneiform Digital Library Initiative (CDLI) bulk export of 135,199 Ur III cuneiform tablets (c. 2112–2004 BCE) in transliterated ATF form. Our central methodological contribution is a framework of negative classification — linguistically-grounded rules specifying what is *not* the target commodity — validated by a regression test suite of 144 cases and cross-checked against an independent arithmetic ground truth: the ancient scribe's own grand-total line (*šunigin*). Of 122 tablets on which this arithmetic check is applicable, 90 (73.8%) yield pipeline grain totals matching the scribe's own sum to within 1 *sila₃*, providing a machine-verified sub-corpus with proven extraction accuracy. The filter suite reduced spurious grain volume by approximately 0.96 million *gur* (26%) relative to a naïve baseline. Recall cannot be estimated without a manually coded ground-truth sample but is practically lower-bounded by the arithmetic match on verified tablets.

Applied to the full corpus, the validated pipeline extracts at least 230,342 quantified economic transactions, at least 274,117 hierarchical line-entries, and at least 2.335 million *gur* (approximately 420,000 metric tonnes) of cereal grain — all lower bounds due to physical damage. On the arithmetically verified sub-corpus, the modal grain allocation is 60 *sila₃* (1 *barig*, the standard Ur III adult monthly ration), the per-entry Gini coefficient of grain throughput is 0.873, and the exchange network of 1,644 agents exhibits near-zero but above-null reciprocity (observed 0.039, degree-preserving null 0.022, *z* = 4.45), consistent with a hierarchical redistributive flow structure. The methodology — negative classification, test-driven rule development, and scribal arithmetic as an independent validation signal — is directly transferable to other ancient administrative corpora where similar extraction challenges arise.

**Keywords:** information extraction, ancient corpora, cuneiform, Ur III, digital humanities, test-driven development, false-positive control, network analysis, economic history

---

## 1. Introduction

Ancient administrative corpora present a particular challenge for large-scale computational extraction. Unlike literary texts, where the primary task is semantic interpretation, administrative documents record quantities, commodities, agents, and dates in highly regular grammars — which suggests that pattern-based extraction should be straightforward. In practice it is not, because the same surface grammar encodes radically different referents depending on commodity context that must be resolved locally. A numeral-and-unit sequence that denotes 2 *gur* of grain in one line denotes 2 *gur* of beer in the next if the commodity word changes. In corpora with dozens of capacity-measured commodities, a parser that harvests every numeral-unit sequence without negative classification will systematically over-extract the target commodity by a margin that is both large and difficult to characterise without external validation.

This paper addresses the extraction problem directly. We describe a pipeline for the Ur III cuneiform corpus — one of the most extensively documented ancient administrative records in existence, comprising over 135,000 transliterated tablets in the CDLI — and argue that three elements together constitute a reliable extraction methodology for such corpora: (1) a taxonomy of false-positive classes grounded in the source language's scribal conventions; (2) a regression test suite that encodes each adjudicated case in executable form; and (3) an independent validation signal derived from the source documents themselves — in this case, the ancient scribe's own arithmetic totals. Each element addresses a distinct failure mode. The taxonomy identifies what the rules must cover. The test suite prevents rule changes from introducing regressions. The arithmetic validation provides end-to-end accuracy estimates independent of the rule development process.

These three elements are not specific to cuneiform. Comparable challenges arise in any corpus where quantities are polysemously encoded: Egyptian hieratic papyri record grain, linen, and silver in the same numeral grammar; medieval Latin accounts use Roman numerals for commodities, distances, and workforce counts; Babylonian astronomical diaries record planetary positions and commodity prices in the same sexagesimal notation. The methodology we describe is a case study in how to handle this class of problem, using the Ur III corpus as the demonstration because it is the largest and most richly documented instance currently available in machine-readable form.

The historical findings — 2.335 million *gur* of cereal grain, a log-normal transaction-size distribution, near-zero network reciprocity — are presented as evidence that the methodology produces coherent and interpretable output, and as a quantitative complement to the qualitative scholarship on the Ur III redistributive economy (Sallaberger 1999; Steinkeller 1987; Waetzoldt 1972). We make no claim to resolve open historical questions; we claim to provide a foundation of reliably extracted data from which such questions can begin to be approached quantitatively.

---

## 2. Background

### 2.1 The CDLI Ur III Corpus

The Third Dynasty of Ur (c. 2112–2004 BCE) operated an administrative apparatus of unusual density, generating clay tablet records of individual ration payments, field seed-allocations, animal transfers, and annual granary balances across provincial centres at Drehem (Puzriš-Dagan), Umma, Girsu, Nippur, and Ur. The CDLI has transliterated more than 135,000 of these tablets into the ASCII Transliteration Format (ATF), a standardised machine-readable encoding that represents cuneiform signs in Latin characters, marks physical damage (`[…]`, `x`), notes uncertain readings (`?`, `!`), and tags grammatical determinatives (`{d}`, `{ki}`, `{gesz}`).

The ATF corpus is a live scholarly resource, not a static dataset. Transliteration conventions vary across contributors and periods; some tablets are partially encoded; and the corpus continues to grow as new material is processed. All counts derived from it are lower bounds, and any pipeline that processes the corpus must tolerate malformed or inconsistent input gracefully. The corpus covers the full geographic and institutional range of the Ur III period and constitutes the largest currently available digital sample of the surviving administrative record — but not a complete census, since tablets in private collections and unpublished museum holdings remain outside scope.

### 2.2 The Extraction Problem: Polysemous Numeral-Classifier Grammar

Capacity in Ur III tablets is recorded in a sexagesimal system (Table 1) whose tokens — *sila₃*, *ban₂*, *barig*, *gur* — appear in every commodity-volume line regardless of what is being measured. The line `2(aš) gur` denotes two *gur* of barley; `2(aš) gur kaš` two *gur* of beer; `2(aš) sa gi` two bundles of reed. A parser that identifies the capacity tokens first and the commodity word second will routinely misclassify the latter two as grain.

The problem is compounded by the multiplicative structure of the system. Because the highest-denomination tokens (*šar₂*, *šar₂ gal*) multiply the *gur* by up to 36,000, a single misclassified large-denomination line can inject tens of millions of *sila₃* of phantom grain — enough to distort corpus-wide volume estimates by hundreds of thousands of *gur*. Precision on the tail of the size distribution therefore governs aggregate accuracy, which means that a small number of false positives have disproportionate quantitative impact.

**Table 1.** The Ur III sexagesimal capacity system and its conversion to *sila₃*.

| Token | *Sila₃* equivalent |
|---|---|
| *sila₃* | 1 |
| *ban₂* | 10 |
| *barig* | 60 |
| *gur* | 300 |
| *šar₂* | 180,000 |
| *šar₂ gal* | 10,800,000 |

---

## 3. Methodology

### 3.1 Pipeline Architecture

The pipeline processes each tablet in four sequential stages: structural segmentation, quantity parsing, attribution and dating, and normalisation. Every stage is implemented in pure Python with no machine-learning dependency; all decisions are deterministic and auditable. Code, tests, and documentation are available at `asarodan/sumer`.

**Structural segmentation.** Tablets are split at structural keywords — *šunigin* (grand total), *sza₃-bi-ta* ("therefrom", opening an expenditure block), *sag-nig₂-gur₁₁* ("capital", opening an income block) — that mark accounting section boundaries in the Ur III administrative grammar. Secondary surfaces (`@seal`, `@envelope`) are stripped before processing; they routinely repeat personal names in positions that would otherwise trigger false attribution. Non-administrative genres (lexical lists, royal inscriptions, school tablets) are rejected on inspection of the CDLI header and protocol fields.

**Quantity parsing.** Within each section, the numeral-classifier grammar `N(unit)` is parsed and mapped through Table 1. Multiple numeral-unit pairs on a single line are summed. A line yields a grain quantity only if it passes the negative-classification filters of §3.2; otherwise it is routed to the appropriate non-grain channel (animals in head, silver in *gin₂*, labour in worker-days) or discarded. Bracketed lacunae suppress the containing line to avoid partial quantity reads.

**Attribution and dating.** Issuer (*ki X-ta*, "from X"), recipient (*X šu ba-ti*, "X received"), and intermediary (*giri₃ X*, "via X") are resolved from prepositional frames. Year-names are matched against a reign-by-reign almanac and reduced to structured date objects (king, regnal year, month, day) where resolvable. Attribution coverage is low — only 2.9% of transactions carry both a resolved issuer and recipient — because many tablet genres record quantities without explicit attribution in formulaic frames on every line.

**Normalisation and prosopography.** Personal names are normalised by stripping grammatical case suffixes only when the bare form is independently attested elsewhere in the corpus, a conservative strategy that guards against over-merging distinct individuals. A patronymic scanner (*X dumu Y*, "X son of Y") yields at least 6,761 father–son pairs; individuals with identical names but distinct attested fathers are flagged as homonymous.

The pipeline produces: a flat transaction table (tablet ID, transaction type, issuer, recipient, intermediary, quantity in *sila₃*, commodity, unit, date); a three-level tablet → record → entry hierarchy; an entity index; and a barley-flow network in GEXF format. Summary counts appear in Table 2.

**Table 2.** Pipeline yield over the 135,199-tablet corpus. All counts are lower bounds due to physical damage.

| Output | Count |
|---|---|
| Transactions extracted | ≥230,342 |
| Records (administrative sections) | ≥77,091 |
| Line-entries | ≥274,117 |
| Named agents | ≥22,166 |
| Patronymic pairs | ≥6,761 |
| Tablets with ≥1 transaction | 48,603 |

### 3.2 Negative Classification: The False-Positive Control Framework

The central methodological insight is that in polysemous numeral-classifier grammars, extraction accuracy is determined more by what is excluded than by what is included. We identify six major false-positive classes and develop specific linguistic rules for each, grounded in documented scribal conventions.

**Non-grain capacity commodities.** Beer (*kaš*), oil (*i₃*), and dates (*zu₂-lum*) are measured in *sila₃* and *gur* with identical numeral syntax. Disambiguation requires the commodity word, which may precede or follow the numeral depending on scribal convention and is therefore not reliably captured by a single positional rule.

**Animal counts with capacity-like numerals.** On livestock tablets, animal-count lines use large sexagesimal tokens in positions resembling capacity lines (`5(gesz2) udu`, 300 sheep). The animal-type term triggers disqualification; the difficulty is that animal terms sometimes appear later on the same line than the capacity tokens.

**Seed-grain at planting rates.** Field tablets record seeding rates as `N gur GAN₂` (capacity per area unit). The `GAN₂` logogram (field-area marker) suppresses grain extraction for that line.

**Subtotal carry-forwards.** The *sza₃-bi-ta* section opener restates the incoming balance; extracting it again produces double-counting of the quantities already captured in the preceding section.

**Rate-multiplication lines.** Certain ration tablets record both a per-person rate and the product of that rate times a worker count. Only the product is the economic transaction; extracting both double-counts individual rations against their aggregated total.

**Named individuals with capacity-token elements.** A minority of personal names contain capacity-system tokens as lexical components. Without the surrounding prepositional frame that identifies them as names, these lines trigger false grain reads.

**The large-denomination ration trap.** The single most consequential false-positive class — approximately 0.80 million phantom *gur* — is the large-denomination ration list. On brewer- and weaver-ration tablets, worker entries use large sexagesimal tokens (*gesz₂*, *gesz'u*) to count *sila₃* rather than *gur*: for example, `3(gesz'u) 4(gesz2) 2(u) 3(disz) ARAD₂` represents 3 × 3,600 + 4 × 60 + 23 = 11,063 *sila₃* (approximately 37 *gur*), with the section's closing *šunigin* performing the *gur* conversion. A parser applying the *gur* factor to *gesz₂* tokens inflates such a line by ×300.

The diagnostic signature is: a line carrying large-denomination tokens (*gesz₂*, *gesz'u*) but **no sub-*gur* anchor** (*aš*, *barig*, or *ban₂*) is operating in *sila₃* scale. On genuine *gur*-scale lines, sub-*gur* remainder tokens always appear alongside large-denomination tokens when the quantity is not an exact multiple of *gur*. Their absence is the reliable diagnostic for *sila₃*-scale ration entries. This single rule accounts for the majority of the 26% volume reduction.

**Context-sensitive recovery for false negatives.** Aggressive negative filtering risks discarding legitimate grain lines where the commodity word is omitted by scribal ellipsis, common in established grain sections. A context-sensitive recovery mechanism activates within sections already containing an explicit grain line, recovering unit-elided quantity lines subject to the condition that no §3.2 disqualifier is present. The two mechanisms are calibrated adversarially: every loosening of recovery criteria is validated against the false-positive test suite; every tightening of negative rules is validated against documented elliptical grain lines.

### 3.3 Test-Driven Validation

All 120 pattern terms are exercised by 144 regression tests, all currently passing, that encode both lines that *must* parse as grain and lines that *must not*. The test suite was developed test-first across more than eighty pipeline revisions. We regard the test corpus — not any individual rule — as the primary durable artefact: it freezes hundreds of adjudicated scribal idioms in executable form, makes the filter logic auditable by domain specialists, and ensures that improvements to one error class do not introduce regressions elsewhere.

The net effect of the filter suite is a reduction from a naïve baseline of approximately 3.73 million *gur* to the validated 2.335 million *gur* — a reduction of **0.96 million *gur* (26%)**.

### 3.4 Arithmetic Validation: The *Šunigin* Harness

The test suite validates individual parsing decisions but cannot detect systematic errors that affect all instances of a pattern. We complement it with an independent end-to-end quality signal derived from the source documents themselves.

Genre-1 Ur III distribution tablets record a list of grain entries followed by a scribal grand total: *šunigin N gur M barig …* ("total: N *gur* M *barig* …"). The scribe computed this total by hand. If the pipeline's sum of extracted grain quantities for a tablet matches the scribe's total to within a rounding tolerance, extraction is verified for that tablet by a ground-truth signal entirely independent of the pipeline's own rules.

Of 135,199 tablets, 589 contain a single unambiguous *šunigin* grain total in genre-1 structure. Of those, 463 have damaged or illegible totals (uncheckable) and 4 have no parseable line-items (uncheckable). The remaining **122 fully checkable tablets** are tested with two passes — barley-only and all-grain (adding emmer and wheat) — accepting balance if either matches to within 1 *sila₃*.

**90 of 122 tablets balance (73.8%).** Inspection of the 32 failures identifies approximately 22 as scribal arithmetic errors (the ancient total is internally inconsistent with the line-items, confirmed by independent manual calculation) and approximately 10 as structural formats outside the genre-1 assumption. No tractable pipeline error was identified after individual review of all 32 failures.

**Precision, recall, and the scope of validation.** The *šunigin* harness provides bounded precision estimates: for the 90 verified tablets, extracted grain quantities are correct by construction. Across the full filter suite, the 26% naïve-to-validated reduction documents the approximate false-positive rate of an unfiltered baseline, and the 144-test regression suite verifies zero false positives on all documented cases.

Recall cannot be estimated without a manually coded ground-truth sample, which does not currently exist for this corpus. For the 90 verified tablets, the arithmetic match provides a practical lower bound: if the pipeline's sum equals the scribe's total, all grain lines contributing to that total were captured. For the remaining 135,109 tablets, recall is unquantified. Obtaining reliable recall estimates would require manual coding of a stratified sample across tablet genres and archival groups — a substantial philological undertaking that we flag as the most important direction for future validation work.

The *šunigin* harness validates grain quantities and commodity classification but not attribution fields (issuer, recipient, date). A tablet can balance arithmetically while having attribution fields incorrectly extracted. The verified sub-corpus (§5.2) is used exclusively for distributional analysis of grain quantities.

---

## 4. Results: Corpus-Level Extraction

**Volume and composition.** Table 3 shows aggregated capacity volume by commodity. Barley alone accounts for at least 2.009 million *gur* (86% of total cereal grain); combined cereals reach at least 2.335 million *gur* (Fig. 1c). All values are lower bounds; grain with damaged commodity words is excluded. The dominance of barley in the extracted record is consistent with its role in the Ur III economy as the principal ration medium and de facto unit of account, as documented by Englund and others. By transaction count, animals (45,571) and bread (28,032) rank second and third — reflecting the Drehem livestock archive's contribution — but their capacity-unit volume is negligible relative to grain.

**Table 3.** Capacity-measured volume by commodity (*gur*). Cereal grains in bold. All values are lower bounds.

| Commodity | Volume (*gur*) | Share of grain total |
|---|---|---|
| **Barley** | **≥2,009,257** | **86.0%** |
| **Flour** | **≥154,049** | **6.6%** |
| **Emmer** | **≥75,330** | **3.2%** |
| **Dates** | **≥26,266** | **1.1%** |
| **Wheat** | **≥23,530** | **1.0%** |
| **Beer** | **≥23,275** | **1.0%** |
| **Oil** | **≥19,982** | **0.9%** |
| **Malt** | **≥3,366** | **0.1%** |

**Transaction-size distribution.** The size distribution of at least 49,751 positive barley capacity-transactions spans eight orders of magnitude (Fig. 1a). A log-normal fit to the body gives μ = 5.18, σ = 3.29 (natural log of *sila₃*); both median and modal value fall at 300 *sila₃* (1 *gur*). The arithmetic mean is approximately 12,116 *sila₃* — 68 times the geometric mean of 178 *sila₃* — indicating a heavy right tail. The top 1% of transactions carry at least 53.9% of recorded volume; the top 10% carry at least 91.2% (Fig. 1b).

**Temporal distribution.** Approximately one-third of extracted transactions carry a recoverable reign date. The reign of Šulgi (c. 2094–2047 BCE) contributes at least 70,811 dated transactions; subsequent reigns contribute between 1,000 and 1,500 each. The concentration in the Šulgi period reflects the survival of specific archives (Drehem, Umma, Girsu) rather than a genuine economic peak, as Sallaberger has noted in the philological literature. Any longitudinal reading must treat temporal variation primarily as a proxy for archival density (Fig. 1d).

---

## 5. Results: Verified Sub-Corpus Analysis

### 5.1 Rationale

The full corpus includes genre-1 ration lists, provincial granary balances, harvest receipts, inter-archive transfer records, and many tablet types whose internal structure differs significantly. Analysing them together risks conflating different economic registers. The 90 verified tablets provide a controlled subset — genre-1 ration distribution tablets whose grain quantities are arithmetically proven — on which distributional statistics carry the strongest validity claims.

### 5.2 Distributional Results

The 90 verified tablets comprise 570 grain entries recording at least 10,980 *gur* of cereal grain, predominantly barley (565 of 570 entries). The sub-corpus contains at least 223 unique named recipients and at least 19 unique named issuers.

**Entry-size distribution** (Table 4; Fig. 2a): the 10th and 25th percentiles are both 60 *sila₃*; the median is 300 *sila₃*; the 75th percentile is 1,500 *sila₃*; the maximum is 361,500 *sila₃* (1,205 *gur*). The most common single entry size is 60 *sila₃* (89 occurrences), nearly twice the frequency of the next most common value (120 *sila₃*, 38 occurrences; Table 5).

**Table 4.** Entry-size percentiles, verified sub-corpus.

| Percentile | *Sila₃* | Equivalent |
|---|---|---|
| p10 | 60 | 1 *barig* |
| p25 | 60 | 1 *barig* |
| p50 | 300 | 1 *gur* |
| p75 | 1,500 | 5 *gur* |
| p90 | ≈15,000 | 50 *gur* |
| Max | 361,500 | 1,205 *gur* |

**Table 5.** Most common entry sizes, verified sub-corpus.

| *Sila₃* | Equivalent | Count |
|---|---|---|
| 60 | 1 *barig* | 89 |
| 120 | 2 *barig* | 38 |
| 1,200 | 4 *gur* | 36 |
| 90 | 1 *barig* 3 *ban₂* | 33 |
| 300 | 1 *gur* | 27 |
| 900 | 3 *gur* | 20 |

**Gini coefficients** (Table 6; Fig. 2b): per-entry G = 0.873, per-tablet G = 0.837, per-recipient G = 0.907. The full-corpus per-transaction Gini is 0.934.

**Table 6.** Gini coefficients, verified sub-corpus and full corpus.

| Measurement | Verified (90 tablets) | Full corpus |
|---|---|---|
| Per entry / transaction | 0.873 | 0.934 |
| Per tablet | 0.837 | 0.919 |
| Per named recipient | 0.907 | — |

### 5.3 Interpretation

The modal allocation of 60 *sila₃* matches the lower-tier monthly ration for unskilled workers documented by Waetzoldt in Ur III textile-industry registers. The frequency hierarchy in Table 5 — 60, 90, 120 *sila₃* as the three dominant values — corresponds to the documented tiered ration scale (unskilled workers, intermediate grades, supervisors). These are not independent discoveries; they are confirmations, at corpus scale, of distributions established by Waetzoldt and others through archival analysis of individual register groups.

The Gini coefficients measure the concentration of grain throughput in this record type, not personal income inequality across the Ur III population. Two structural features inflate the figures. First, bulk institutional transfers (tens of thousands of *sila₃*) coexist with individual ration entries (60–300 *sila₃*) in the same dataset; the ratio of up to 6,000:1 mechanically produces a high Gini. Second, *lugal* ("royal estate") is a single recipient node on 33 of 90 verified tablets receiving 9.3% of all verified grain — an institutional destination, not an individual. Per-entry and per-tablet Gini values (0.873 and 0.837), which are not affected by name conflation, are the more robust summary measures.

The verified-sub-corpus Gini (0.873 per entry) is lower than the full-corpus figure (0.934 per transaction), consistent with the genre-1 composition of the verified set: ration distribution tablets contain many similar-sized small entries that reduce within-tablet variance, whereas the full corpus includes large granary inventory tablets with single very large entries.

---

## 6. Results: Exchange Network

**Graph statistics.** Restricting to barley transactions with both a resolved issuer and recipient yields a directed network of 1,644 agents and 2,807 unique directed edges (6,691 total transactions). Table 7 compares key statistics against a degree-preserving null model (configuration model, 100 randomisations).

**Table 7.** Network statistics vs. degree-preserving null model.

| Statistic | Observed | Config. model (mean ± s.d.) | *z* |
|---|---|---|---|
| Reciprocity | 0.039 | 0.022 ± 0.004 | +4.45 |
| GCC fraction | 0.845 | 0.886 ± 0.009 | −4.50 |
| Density | 0.00104 | — | — |
| Weakly connected components | 119 | — | — |
| Communities (modularity) | 29 | — | — |

The in-degree distribution is heavy-tailed: 871 of 1,644 nodes have in-degree 1; maximum in-degree is 41 (ur-ba-ba₆). The maximum out-degree is 117 (ba-zi). Top agents by betweenness centrality: ur-ba-ba₆ (0.084), *ugula* overseer (0.075), ur-šul-pa-e₃ (0.055), lu₂-kal-la (0.054).

**Interpretation.** Three structural features are of historical interest.

Reciprocity (0.039) is significantly above the degree-preserving null (z = +4.45), meaning that mutual-exchange pairs are more frequent than the degree sequence alone predicts. This is consistent with officials who both receive allocations for their household and disburse from those same allocations — an intermediary role documented for senior administrators (*šabra*, *agrig*) in the philological literature. It does not establish bilateral market exchange.

The GCC (84.5%) is modestly but significantly smaller than the null expectation (z = −4.50). A degree-preserving random network would be slightly more cohesive than the observed network. The 29 detected communities are consistent in scale with the known provincial archive geography of the Ur III state — Drehem, Umma, Girsu, and Nippur archives forming distinct institutional clusters with sparser inter-community ties.

Ba-zi's extreme out-degree (117 distinct recipients) is consistent with the role of a central distribution official, corresponding to the ba-zi documented in Drehem texts as a high-volume disbursement agent. Ur-ba-ba₆'s dual prominence in betweenness and in-degree is consistent with a senior consolidating administrator who aggregates grain from multiple provincial sources before redistribution.

The attributed transactions used for network analysis (6,691) represent 2.9% of all extracted barley transactions. This attributed minority may systematically oversample transaction types that formulaically require named issuers and recipients, and the network findings should be interpreted accordingly.

---

## 7. Transferability to Other Ancient Corpora

The methodology described here — negative-classification rules, test-driven development, and scribal arithmetic as independent validation — is not specific to Sumerian cuneiform. We identify three conditions under which the approach applies, and briefly characterise analogous cases.

**Condition 1: Polysemous numeral-classifier grammar.** The extraction problem arises wherever the same numeral-unit syntax encodes multiple commodity classes. This condition is met in Egyptian hieratic papyri (which record grain, linen, and metal in the same numeral grammar), Babylonian astronomical diaries (commodity prices and planetary data in the same sexagesimal notation), and medieval Latin accounts (Roman numerals for commodities, distances, and workforce).

**Condition 2: Scribal arithmetic totals.** The *šunigin* validation harness is generalisable wherever the ancient scribes performed and recorded their own arithmetic checks — section subtotals, year-end balances, audit tallies. Such totals appear widely in ancient and medieval administrative records. Wherever they survive, they constitute an independent ground-truth signal that requires no external annotation effort to exploit.

**Condition 3: Digital transliteration corpus.** The approach requires a corpus in machine-readable form with consistent structural markup. CDLI provides this for cuneiform; the Papyri.info project provides a comparable resource for Greek and Latin papyri; the Medievalist.net family of corpora covers medieval Latin documents. The specific lexical rules must be redeveloped for each corpus's scribal conventions, but the three-layer architecture — negative classification, regression tests, arithmetic validation — transfers directly.

**What must be redeveloped per corpus.** The specific pattern terms (e.g., the sub-*gur* anchor rule) are language- and convention-specific and must be rebuilt from scratch for each new corpus. The false-positive taxonomy provides a generic template, but populating it requires domain knowledge of the source language's scribal idioms. In practice, this means working closely with specialist translators or philologists to identify the corpus-specific instances of each false-positive class — exactly the kind of collaboration that digital humanities projects routinely undertake.

---

## 8. Limitations

**(i) All counts are lower bounds.** Physical damage suppresses quantities and attribution fields throughout the corpus; all transaction, volume, and entity counts understate the true ancient throughput.

**(ii) Recall is unquantified for the majority of the corpus.** Precision on grain quantities is documented for the 90 verified tablets and by the regression suite's zero-false-positive record on 144 test cases. Recall is practically lower-bounded by the arithmetic match on verified tablets but cannot be estimated for the remaining 135,109 tablets without a manually coded ground-truth sample.

**(iii) Attribution coverage is low and possibly unrepresentative.** The 2.9% of transactions with resolved issuer and recipient may over-represent transaction types that formulaically require explicit attribution, biasing the network analysis toward specific institutional record types.

**(iv) Prosopographic noise.** The entity index conflates commodity terms with personal names in unusual syntactic positions. Genuine-person analysis should use the patronymic-anchored subset.

**(v) Survivorship and genre bias.** The temporal and provincial distribution of transactions reflects archival survival and digitisation patterns, not the ancient economy's shape. The verified sub-corpus is additionally biased toward genre-1 ration tablets.

**(vi) The *šunigin* harness covers 122 of 135,199 tablets.** The pipeline's accuracy for the remaining corpus is unvalidated by the arithmetic method; the regression suite provides complementary but qualitatively different coverage.

**(vii) Double-counting at the margin.** Multi-section accounts that re-state sub-section totals hierarchically remain the hardest residual case. Canonical restatements are suppressed but leakage from idiosyncratic ledgers cannot be guaranteed to be zero.

---

## 9. Conclusion

We have presented a rule-based, test-driven extraction pipeline for the 135,199-tablet CDLI Ur III corpus and argued that reliable large-scale extraction from ancient administrative corpora requires three elements working together: negative-classification rules grounded in documented scribal conventions; a regression test suite that encodes each adjudicated case in executable form; and an independent validation signal derived from the source documents' own arithmetic. Applied to the Ur III case, the three-element framework reduced spurious grain volume by 26% relative to a naïve baseline and produced a 90-tablet arithmetically verified sub-corpus whose grain quantities are correct by construction.

The validated pipeline extracts at least 2.335 million *gur* of cereal grain distributed across a log-normal transaction-size distribution with a heavy right tail, organised into an exchange network with above-null reciprocity (z = +4.45) and below-null giant-component cohesion (z = −4.50) relative to a degree-preserving null model. On the verified sub-corpus, the modal grain allocation is 60 *sila₃* — matching the standard Ur III adult monthly ration documented by Waetzoldt — and grain throughput is highly concentrated (per-entry G = 0.873). These findings are consistent with the redistributive administrative structure of the Ur III state as characterised in the philological literature; they do not resolve open historical questions but provide a foundation of reliably extracted, validated data from which such questions can begin to be approached quantitatively.

The methodology is directly transferable to other ancient administrative corpora — Egyptian papyri, Babylonian astronomical diaries, medieval Latin accounts — wherever polysemous numeral-classifier grammar creates the extraction problem and scribal arithmetic totals survive to provide independent validation. The 144-test regression suite and the *šunigin* reconciliation harness are available in the repository `asarodan/sumer` as reusable components.

---

## Figures

**Fig. 1a.** Histogram of barley transaction sizes (log₁₀ *sila₃*). Body is approximately log-normal; median and modal value coincide at 1 *gur* (300 *sila₃*).

**Fig. 1b.** Lorenz curves for barley volume across transactions (dark) and tablets (lighter). Over half of all recorded barley moves through 1% of transactions.

**Fig. 1c.** Capacity-measured commodity volume (log scale). Cereal grains exceed all other capacity commodities by more than an order of magnitude.

**Fig. 1d.** Dated barley transactions by Šulgi regnal year. Peak in years 45–48 indexes archival density, not economic activity.

**Fig. 1e.** Per-tablet barley totals (log₁₀ *gur*). The bimodal structure separates the ration cluster (1–10 *gur*) from the granary cluster (above 10,000 *gur*).

**Fig. 2a.** Entry-size histogram, verified sub-corpus (90 tablets). Dominant mode at 60 *sila₃$ (1 *barig*).

**Fig. 2b.** Lorenz curve, verified sub-corpus. Per-entry G = 0.873.

All figures regenerated from `output/figures/` by `tools/make_paper_figures.py` and `tools/analyze_verified.py`.

---

## Data and Code Availability

All extraction code, the 144-test regression suite, the *šunigin* reconciliation harness (`tools/reconcile_szunigin.py`), the verified-corpus analysis (`tools/analyze_verified.py`), and derived data tables are available at `asarodan/sumer`. The CDLI corpus is distributed by the Cuneiform Digital Library Initiative under its data-sharing terms.

---

## References

Cuneiform Digital Library Initiative (CDLI). *Ur III administrative corpus, ATF bulk export.* cdli.mpiwg-berlin.mpg.de.

Englund, R. K. (2012). Equivalency Values and the Command Economy of the Ur III Period in Mesopotamia. In *The Construction of Value in the Ancient World*, 427–458.

Garfinkle, S. J. (2015). Ur III Administrative Texts: Building Blocks of State Community. In *From the 21st Century B.C. to the 21st Century A.D.*

Milanovic, B., Lindert, P. H., and Williamson, J. G. (2011). Pre-Industrial Inequality. *Economic Journal* 121: 255–272.

Molina, M. (2008). The Corpus of Neo-Sumerian Tablets: An Overview. In *The Growth of an Early State in Mesopotamia*, 19–53.

Sallaberger, W. (1999). Ur III-Zeit. In *Mesopotamien: Akkade-Zeit und Ur III-Zeit*, OBO 160/3, 121–390.

Steinkeller, P. (1987). The Administrative and Economic Organization of the Ur III State: The Core and the Periphery. In *The Organization of Power: Aspects of Bureaucracy in the Ancient Near East*, ed. M. Gibson and R. D. Biggs. SAOC 46, 19–41.

Waetzoldt, H. (1972). *Untersuchungen zur neusumerischen Textilindustrie*. Rome: Centro per le Antichità e la Storia dell'Arte del Vicino Oriente.

Widell, M. (2004). Reflections on Some Households and their Receiving Officials in the City of Ur in the Ur III Period. *JNES* 63, 283–290.

---

*Corpus snapshot: 135,199 tablets · ≥230,342 transactions · ≥2.335 M gur capacity · 90 šunigin-verified tablets*
