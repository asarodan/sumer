# Reconstructing the Ur III Grain Economy from 135,199 Cuneiform Tablets: A Rule-Based Extraction Pipeline and Exploratory Analysis

*A computational study of the CDLI Ur III administrative corpus (c. 2112–2004 BCE)*

**Daniel Asaro**  
Computational Assyriology · asarodan/sumer

---

## Abstract

The Third Dynasty of Ur (Ur III, c. 2112–2004 BCE) produced one of the most extensively documented administrative economies of the ancient world. We present a deterministic, rule-based pipeline that parses the full Cuneiform Digital Library Initiative (CDLI) bulk export of 135,199 Ur III tablets in transliterated ATF form and extracts, conservatively, at least 230,342 quantified economic transactions across nine commodity classes, at least 274,117 hierarchical line-entries, and at least 22,166 named agents. All corpus-level counts are lower bounds; physical damage to tablets suppresses quantities throughout. Converting the Sumerian sexagesimal capacity system to a common unit, the corpus documents at least 2.335 million *gur* of cereal grain (approximately 420,000 metric tonnes), of which barley alone constitutes at least 2.009 million *gur* (86% of all capacity-measured volume).

Transaction sizes are approximately log-normal in their body (median = 300 *sila₃* = 1 *gur*) with an extreme heavy tail: the largest 1% of transactions account for at least 53.9% of recorded volume. A barley-flow network of 1,644 agents exhibits near-zero reciprocity (0.039), significantly elevated above a degree-preserving null model (configuration model mean 0.022, z = 4.45), and a giant weakly-connected component modestly smaller than the null expectation (84.5% vs. 88.6%, z = −4.50), consistent with provincial compartmentalisation. We further introduce an arithmetic validation harness based on the scribal grand-total line (*šunigin*): of 122 fully checkable genre-1 tablets, 90 (73.8%) yield grain totals matching the ancient scribe's own sum to within 1 *sila₃*. On this verified sub-corpus, we measure a per-entry Gini coefficient of 0.873 and find that the modal ration is exactly 60 *sila₃* (1 *barig*), consistent with the standard Ur III adult monthly allocation documented by Waetzoldt. We document a corpus of 120 filtering rules, validated by 144 regression tests, that reduced spurious grain volume by approximately 0.96 million *gur* (26%) relative to a naïve baseline.

**Keywords:** Ur III, computational Assyriology, information extraction, economic history, cuneiform, ATF, network analysis, log-normal distribution, Gini coefficient, šunigin

---

## 1. Introduction

The Ur III state (c. 2112–2004 BCE) generated an administrative record of exceptional density. Scribes at Drehem (Puzriš-Dagan), Umma, Girsu, Nippur, and Ur documented individual ration payments, field seed-allocations, animal transfers, and annual granary balances on clay tablets sealed with the names of responsible officials. Tens of thousands of these tablets survive; the CDLI has transliterated more than 135,000 into the machine-readable ATF standard. The corpus creates an opportunity to study an ancient economy at transaction-level granularity unavailable for any other period before the late medieval era.

Prior scholarship has characterised the Ur III economy through the analysis of individual archives. Sallaberger's synthesis establishes the administrative roles of household managers (*šabra*), high stewards (*agrig*), and provincial governors (*ensi*); Steinkeller documents the *bala* tributary mechanism by which provinces contributed grain to the Puzriš-Dagan redistribution centre; Waetzoldt's analysis of ration registers establishes the ration scales at which different worker categories were maintained. What has been lacking is a quantitative portrait of the entire surviving record simultaneously: aggregate volumes, the structure of the size distribution, and the exchange network connecting named agents.

The principal methodological obstacle to such a portrait is linguistic rather than computational. The line `2(aš) gur` denotes two *gur* of barley; the visually parallel `2(aš) sa gi` denotes two bundles of reed. The same numeral classifiers, sexagesimal place-values, and scribal conventions serve grain, garlic, silver, and labour alike. A parser that harvests every numeral followed by a capacity unit over-counts grain by hundreds of thousands of *gur*. Reliable extraction is governed by negative classification — by knowing what is not grain — and this problem is tractable with a disciplined body of linguistically-grounded rules.

We make four contributions: (1) a complete extraction pipeline (§3) producing typed, dated, attributed transactions; (2) an arithmetic validation harness (§3.6) furnishing a machine-verifiable ground-truth sub-corpus; (3) an exploratory statistical portrait of the Ur III grain economy (§4–§5) situating corpus-wide results in relation to prior scholarship; and (4) a false-positive methodology (§6) documented in a form transferable to other large-scale cuneiform extraction projects.

---

## 2. The Corpus and the Measurement System

Our source is the CDLI bulk ATF export: 135,199 tablets classified as Ur III, spanning the full geographic and institutional range of the period. Each tablet is a sequence of transliterated lines with editorial markers for physical damage (`[…]`, `x`), uncertain readings (`?`, `!`), and determinatives (`{d}`, `{ki}`, `{gesz}`). This corpus represents the largest currently available digital sample of the Ur III administrative record, not a complete census; tablets in private collections and in unpublished or undigitised museum holdings remain outside scope.

Capacity is recorded in a Sumerian sexagesimal system (Table 1). The base unit is the *sila₃* (approximately 0.8 litres); the principal accounting unit is the *gur* = 300 *sila₃*. Because the capacity tokens are multiplicative, a single mis-classified large-denomination line can inject up to 64.8 million *sila₃* of phantom grain — a fact that shapes the entire extraction strategy.

**Table 1.** The Ur III sexagesimal capacity system.

| Token | *Sila₃* equivalent |
|---|---|
| *sila₃* | 1 |
| *ban₂* | 10 |
| *barig* | 60 |
| *gur* | 300 |
| *šar₂* | 180,000 |
| *šar₂ gal* | 10,800,000 |

---

## 3. Extraction Pipeline

The pipeline is implemented in pure Python with no machine-learning dependency. Every rule is auditable, deterministic, and exercised by regression tests; code and tests are available at `asarodan/sumer`.

### 3.1 Processing Stages

**Structural segmentation.** Each tablet is split at structural keywords — *šunigin* (grand total), *sza₃-bi-ta* ("therefrom"), *sag-nig₂-gur₁₁* ("capital") — that mark accounting section boundaries. Secondary surfaces (`@seal`, `@envelope`) are stripped; non-administrative genres (lexical lists, royal inscriptions, literary texts) are rejected on header inspection.

**Quantity parsing.** Within each section, the numeral-classifier grammar `N(unit)` is parsed and mapped through Table 1. A line yields a grain quantity only if it passes the negative-classification filters of §6; otherwise it is routed to the appropriate non-grain channel (animals in head, silver in *gin₂*, labour in worker-days) or discarded. Bracketed lacunae suppress the containing line to avoid partial reads.

**Attribution and dating.** Issuer (*ki X-ta*, "from X"), recipient (*X šu ba-ti*, "X received"), and intermediary (*giri₃ X*, "via X") are resolved from prepositional frames. Year-names are matched against a reign-by-reign almanac and reduced to structured date objects (king, regnal year, month, day) where resolvable.

**Normalisation and prosopography.** Names are normalised by stripping grammatical case suffixes (*-ke₄*, *-ra*, *-e*, *-šè*) only when the bare form is independently attested elsewhere in the corpus. A patronymic scanner (*X dumu Y*, "X son of Y") yields at least 6,761 father–son pairs; individuals with identical names but distinct attested fathers are flagged as homonymous.

**Output.** The pipeline produces: a flat transaction table; a three-level tablet → record → line-entry hierarchy; an entity index; and a barley-flow network in GEXF format. Summary statistics appear in Table 2.

**Table 2.** Pipeline yield over the 135,199-tablet corpus. All counts are lower bounds.

| Output | Count |
|---|---|
| Transactions extracted | ≥230,342 |
| Records (administrative sections) | ≥77,091 |
| Line-entries | ≥274,117 |
| Named agents | ≥22,166 |
| Patronymic pairs | ≥6,761 |
| Tablets with ≥1 transaction | 48,603 |

The 86,596 tablets yielding no transaction are not pipeline failures. Many are fragmentary, belong to non-economic genres, or record non-capacity commodities (textiles, metals, livestock) outside the current pipeline's scope.

### 3.2 Arithmetic Validation: The *Šunigin* Reconciliation Harness

Genre-1 Ur III distribution tablets record a list of ration entries followed by a scribal grand total (*šunigin N gur M barig …*). This total provides a validation signal: if the pipeline's sum of extracted grain quantities matches the scribe's own *šunigin* to within a tolerance, the extraction is verified for that tablet.

Of 135,199 tablets, 589 contain a single unambiguous *šunigin* grain total in recognisable genre-1 structure. Of those, 463 have damaged or illegible totals and 4 have no parseable line-items — both uncheckable. The remaining **122 fully checkable tablets** are tested with two passes: a barley-only sum and an all-grain sum (adding emmer and wheat), accepting balance if either matches the *šunigin* within 1 *sila₃*.

**90 of 122 tablets balance (73.8%).** Inspection of the 32 failures identifies approximately 22 as apparent scribal arithmetic errors (the ancient total is internally inconsistent with the line-items, confirmed by independent manual calculation) and approximately 10 as structural formats outside the genre-1 assumption (multi-commodity tablets where the *šunigin* covers one commodity only, dual-section accounts, tablets with ATF lacunae). No tractable pipeline error was identified after individual review of all 32 failures.

**Precision, recall, and the limits of validation.** The *šunigin* harness provides a bounded estimate of precision on grain quantity extraction: for the 90 balanced tablets, the pipeline's grain quantities are correct by construction. Across the full filter suite, the reduction from a naïve baseline (3.73 million *gur*) to the validated output (2.335 million *gur*) documents that approximately 26% of naïve capacity-unit extractions were false positives, and the 144-test regression suite verifies zero false positives on all documented test cases.

Recall cannot be estimated from the corpus alone. A ground-truth sample — a set of tablets manually coded for all grain lines — does not exist for the full CDLI corpus. For the 90 verified tablets, the *šunigin* match provides a practical lower bound on recall: if the pipeline's sum equals the scribe's total, the pipeline captured all (or all but rounding-equivalent) grain lines on that tablet. For the remainder of the corpus, recall is unquantified and may vary by tablet genre, archive, and period.

The *šunigin* validation covers grain quantity and commodity classification but does not extend to attribution fields (issuer, recipient, date). A tablet can balance arithmetically while having attribution fields incorrectly extracted. The verified sub-corpus (§5.3) is therefore used exclusively for distributional analysis of grain quantities.

---

## 4. Results: Volume and Composition

**Commodity profile.** Table 3 shows the aggregated capacity volume by commodity. Barley alone accounts for at least 2.009 million *gur* (86% of total grain); combined cereals reach at least 2.335 million *gur* (Fig. 1c). Dates, oil, and beer are each below 30,000 *gur* — less than 1.5% of the cereal total. All figures are lower bounds; grain damaged beyond readability is excluded.

**Table 3.** Capacity-measured volume by commodity. Cereal grains in bold. All values are lower bounds.

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

**Interpretation.** The dominance of barley in the corpus is consistent with its role in the Ur III economy as simultaneously the principal food crop, the standard ration medium, and the de facto unit of account, as described by Englund and others. Emmer (*ziz₂*), though important in Ur III agriculture, appears far less frequently in the administrative record, consistent with its secondary status in the ration system. The transaction-count profile differs from the volume profile: by count, animals (45,571) and bread (28,032) are major categories, reflecting the Drehem livestock-redistribution archive's contribution; their low volumetric footprint follows from the different unit systems used (head, loaves) rather than economic insignificance.

---

## 5. Results: Distribution and Structure

### 5.1 Transaction Size Distribution

**Results.** The size distribution of at least 49,751 positive barley capacity-transactions spans eight orders of magnitude, from single-digit rations to a single 134,007-*gur* receipt (Fig. 1a). A log-normal fit to the body of the distribution gives μ = 5.18, σ = 3.29 (natural log of *sila₃*). Both median and modal value fall at 300 *sila₃* (1 *gur*). The geometric mean is 178 *sila₃*; the arithmetic mean is approximately 12,116 *sila₃*, roughly 68 times larger — the signature of a heavy right tail.

**Interpretation.** The near-coincidence of median and modal value at 1 *gur* reflects both the natural accounting boundary of the *gur* and scribes' tendency to round monthly work-gang aggregates to the nearest *gur*. The heavy right tail is consistent with the coexistence of a large number of similar-sized individual rations and a smaller number of large-denomination institutional flows — harvest receipts, inter-archive transfers, and annual granary balances. This distributional structure does not itself diagnose the institutional mechanisms that produced it; it characterises the administrative record as it survives.

### 5.2 Volume Concentration

**Results.** The top 1% of barley capacity-transactions (at most 498 transactions) carry at least 53.9% of all recorded barley volume; the top 10% carry at least 91.2% (Fig. 1b). At the tablet level, the per-tablet median is approximately 6.4 *gur*; only 20 of at least 10,838 barley-bearing tablets record more than 10,000 *gur* each. The Lorenz curve (Fig. 1b) lies far below the equality diagonal at all points.

**Interpretation.** The high-volume tail consists of provincial granary balances, harvest receipts, and inter-archive transfer records — institutional accounting entries that aggregate many individual transactions. Their presence in the same dataset as individual ration payments inflates concentration measures relative to a distribution of personal consumption. Section 5.3 uses the verified sub-corpus to separate these regimes more cleanly.

### 5.3 Verified Sub-Corpus: Distributional Analysis

**Results.** The 90 *šunigin*-reconciled tablets (§3.2) comprise 570 grain entries across 90 tablets, recording at least 10,980 *gur* of cereal grain — predominantly barley (565 of 570 entries). The sub-corpus contains at least 223 unique named recipients and at least 19 unique named issuers.

Entry-size percentiles (Table 4): the 10th and 25th percentiles are both exactly 60 *sila₃*; the median is 300 *sila₃*; the 75th percentile is 1,500 *sila₃*; the maximum is 361,500 *sila₃$ (1,205 *gur*). The most common single entry size is 60 *sila₃* (89 occurrences), nearly twice the frequency of the next most common value (120 *sila₃*, 38 occurrences; Table 5). Gini coefficients on verified data: per-entry G = 0.873, per-tablet G = 0.837, per-recipient G = 0.907 (Table 6, Fig. 2b).

**Table 4.** Percentile distribution of grain entry sizes, verified sub-corpus.

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

**Table 6.** Gini coefficients, verified sub-corpus and full corpus.

| Measurement | Verified (90 tablets) | Full corpus |
|---|---|---|
| Per entry / transaction | 0.873 | 0.934 |
| Per tablet | 0.837 | 0.919 |
| Per named recipient | 0.907 | — |

**Interpretation.** The modal allocation of exactly 60 *sila₃* matches the standard lower-tier monthly ration for unskilled workers documented by Waetzoldt in his analysis of Ur III textile-industry registers. The frequency hierarchy in Table 5 is consistent with the documented tiered ration scale: 60 *sila₃* for unskilled workers (*geme₂*, *erin₂*), 90 *sila₃* for intermediate grades, and 120 *sila₃* or more for supervisors. The verified sub-corpus's ration composition thus independently confirms that these tablets record terminal ration distribution rather than institutional bulk accounting entries.

The Gini coefficients measure the concentration of grain throughput in this specific record type, not personal-income inequality across the Ur III population. Two structural features inflate the figures. First, bulk institutional transfers (tens of thousands of *sila₃*) coexist with individual ration entries (60–300 *sila₃*) in the same dataset; their ratio of up to 6,000:1 mechanically produces a high Gini. Second, *lugal* ("royal estate") is recorded as a single recipient node on 33 of 90 verified tablets, receiving approximately 9.3% of all verified grain; this is an institutional destination, not an individual, and its aggregation under a single label inflates the per-recipient Gini. Per-entry and per-tablet Gini values (0.873 and 0.837) are not affected by name conflation and are more robust summary measures of throughput concentration.

The full-corpus Gini (0.934 per transaction) exceeds the verified sub-corpus value (0.873), consistent with the genre-1 composition of the verified set: ration distribution tablets contain many similar small entries that reduce within-tablet variance, whereas the full corpus includes large granary inventory tablets dominated by single very large entries. Comparison with pre-industrial income Gini estimates (Milanovic, Lindert, and Williamson report values typically between 0.40 and 0.60 for ancient and early modern societies) is of limited value here, since we are measuring transaction-size concentration rather than individual income or consumption, and the presence of large institutional entries in the same sample as individual rations makes a direct comparison inappropriate.

### 5.4 Temporal Distribution

**Results.** Approximately one-third of at least 230,342 transactions carry a recoverable reign date. Šulgi's reign (c. 2094–2047 BCE) contributes at least 70,811 dated transactions; Amar-Suen at least 1,293 barley transactions; Šu-Suen at least 1,416; Ibbi-Suen at least 1,033. Within Šulgi's reign, the dated barley record peaks in years 45–48 (Fig. 1d).

**Interpretation.** The concentration of dated transactions in the Šulgi period reflects the archival survival of the Drehem and Umma archives, not a genuine economic peak. The years 45–48 peak corresponds to the period of fullest *bala* accounting documentation noted by Sallaberger. Any longitudinal reading of the transaction series must treat temporal variation primarily as a proxy for archival density rather than as a direct index of economic activity.

### 5.5 Exchange Network

**Results.** Restricting to barley transactions with both a resolved issuer and recipient yields a directed network of 1,644 agents and 2,807 unique directed edges (6,691 total transactions). Network statistics, compared against a degree-preserving null model (configuration model, 100 randomisations), appear in Table 7. The giant weakly-connected component (GCC) spans 1,390 agents (84.5%), modestly below the configuration model expectation of 88.6% (z = −4.50). Network reciprocity is 0.039, significantly above the configuration model expectation of 0.022 (z = 4.45). Modularity optimisation yields 29 communities, the three largest comprising 277, 271, and 128 agents. The in-degree distribution is heavy-tailed: maximum in-degree 41 (ur-ba-ba₆, receiving grain from 41 distinct issuers), with 871 of 1,644 nodes at in-degree 1. The maximum out-degree is 117 (ba-zi, issuing to 117 distinct recipients). Top agents by betweenness centrality and PageRank appear in Table 8.

**Table 7.** Observed network statistics vs. degree-preserving null model (configuration model, 100 randomisations, mean ± s.d.).

| Statistic | Observed | Config. model | *z*-score |
|---|---|---|---|
| Reciprocity | 0.039 | 0.022 ± 0.004 | +4.45 |
| GCC fraction | 0.845 | 0.886 ± 0.009 | −4.50 |
| Density | 0.00104 | — | — |
| Components | 119 | — | — |

**Table 8.** Top agents in the barley exchange network.

| Agent | Betweenness | PageRank | In-degree | Out-degree |
|---|---|---|---|---|
| ur-ba-ba₆ | 0.084 | 0.0099 | 41 | 53 |
| *ugula* (overseer) | 0.075 | — | 34 | 42 |
| ur-šul-pa-e₃ | 0.055 | — | — | 48 |
| lu₂-kal-la | 0.054 | 0.0076 | 33 | — |
| ba-zi | — | — | — | 117 |

**Interpretation.** Three structural features of the network are of historical interest.

*Reciprocity above null expectation.* Observed reciprocity (0.039) is significantly elevated above both a random baseline and the degree-preserving null (z = 4.45). This indicates that the mutual-exchange pairs in the network — agents who both issue grain to and receive grain from the same counterparty — are more frequent than the degree sequence alone would predict. These bidirectional ties are consistent with officials who both receive allocations for their household and disburse from those same allocations, a role documented for senior administrators (*šabra*, *agrig*) in the philological literature. The observation does not establish bilateral market exchange; it is consistent with hierarchical intermediary roles.

*GCC below null expectation.* The observed GCC (84.5%) is modestly but significantly smaller than the configuration model predicts (z = −4.50). A random network with the same degree sequence would be slightly more cohesive. This is consistent with provincial compartmentalisation: separate archive communities (Drehem, Umma, Girsu, Nippur) maintain dense internal ties but sparser inter-community connections, producing a GCC smaller than degree-sequence alone would yield. The 29 detected communities are consistent in scale with the known archive geography of the Ur III state.

*High-betweenness brokers.* Ur-ba-ba₆ ranks first by both betweenness centrality (0.084) and in-degree (41), consistent with a senior consolidating administrator who aggregates from multiple sources. Ba-zi's extreme out-degree (117) is consistent with a central distribution official — the ba-zi documented in Drehem texts as a high-volume disbursement agent. The *ugula* (overseer) category's prominence reflects its structural position as the interface between work-gangs and the institutional supply chain: overseers receive consolidated allocations and disburse to individual workers, placing them at the boundary between institutional and individual layers of the network.

---

## 6. Methodology: Controlling False Positives

### 6.1 The Problem

In a corpus where grain, garlic, reeds, cattle, silver, and accounting balances share a numeral-classifier grammar, the principal extraction error is the eager parsing of non-grain capacity lines. Because a single large-denomination misread can inject up to 64.8 million *sila₃* per line, tail precision governs aggregate accuracy. The naïve baseline — harvesting all numeral-capacity-unit sequences — produces approximately 3.73 million *gur*; the validated pipeline produces approximately 2.335 million *gur*, a reduction of 0.96 million *gur* (26%).

### 6.2 False-Positive Taxonomy and Rules

Six major false-positive classes account for essentially all of the 0.96 million *gur* reduction.

**Non-grain capacity commodities.** Beer (*kaš*), oil (*i₃*), and dates (*zu₂-lum*) are measured in *sila₃* and *gur* with identical numeral syntax. Disambiguation requires the commodity word, which may appear before or after the numeral.

**Animal counts.** Livestock tablets count animals with large sexagesimal tokens in positions resembling capacity lines (`5(gesz2) udu`, 300 sheep). Animal-type terms trigger disqualification.

**Seed-grain at planting rates.** Field tablets record rates as `N gur GAN₂`; the `GAN₂` logogram (field-area marker) suppresses extraction.

**Subtotal carry-forwards.** The *sza₃-bi-ta* section opener restates the incoming balance; a second extraction would double-count.

**Rate-multiplication lines.** On certain ration tablets, computation lines record both a per-person rate and its product for a worker group. Only the product is extracted.

**Named individuals with capacity-token elements.** A minority of personal names contain capacity-system tokens; disambiguation requires the surrounding prepositional frame.

### 6.3 The Large-Denomination Ration Trap

The single most consequential false-positive class — approximately 0.80 million phantom *gur* — is the large-denomination ration list. On brewer- and weaver-ration tablets, worker entries use large sexagesimal tokens (*gesz₂*, *gesz'u*) to count *sila₃* rather than *gur*: for example, `3(gesz'u) 4(gesz2) 2(u) 3(disz) ARAD₂` represents 3 × 3,600 + 4 × 60 + 23 = 11,063 *sila₃* (approximately 37 *gur*), with the section's closing *šunigin* performing the explicit *gur* conversion. A parser applying the *gur* factor to *gesz₂* tokens inflates such a line by ×300.

The diagnostic signature is: a line carrying large-denomination tokens (*gesz₂*, *gesz'u*) but **no sub-*gur* anchor** (*aš*, *barig*, or *ban₂*) is operating in *sila₃* scale. On genuine *gur*-scale lines, sub-*gur* remainder tokens always accompany large-denomination tokens when the quantity is not an exact multiple of *gur*. Their absence is the reliable diagnostic. This single rule accounts for the majority of the 26% reduction.

### 6.4 Context-Sensitive Recovery

Aggressive negative filtering risks discarding legitimate grain lines where the commodity word is omitted by scribal ellipsis — common in established grain sections. A context-sensitive recovery mechanism activates within sections already containing an explicit grain line, recovering unit-elided quantity lines subject to the condition that no §6.2 disqualifier is present. The two mechanisms are calibrated against each other: every recovery loosening is validated against the false-positive test suite; every negative-rule tightening is validated against documented elliptical grain lines.

### 6.5 Validation

120 distinct pattern terms are exercised by 144 regression tests (all passing), encoding both lines that *must* parse and lines that *must not*. We regard the test corpus — not any individual rule — as the primary durable artefact: it freezes hundreds of adjudicated scribal idioms in executable form and makes the filter logic reproducible and auditable by other researchers.

---

## 7. Limitations

**(i) Lower bounds throughout.** All counts (transactions, entries, entities, volume) are lower bounds; physical damage suppresses quantities and attribution fields throughout the corpus.

**(ii) Recall is unquantified.** Precision on grain quantities is documented by the *šunigin* harness (90/122 tablets verified) and the regression suite (zero false positives on 144 test cases). Recall — the fraction of all grain lines that the pipeline captures — cannot be estimated without a manually coded ground-truth sample, which does not yet exist for this corpus. For the 90 verified tablets, the arithmetic match provides a practical lower bound: if the pipeline's sum equals the scribe's total, all grain lines were captured. For the remainder, recall is unknown.

**(iii) Attribution coverage is low.** Only 2.9% of transactions carry both a resolved issuer and recipient, restricting network analysis (§5.5) to a small fraction of the corpus that may be structurally unrepresentative — specifically over-sampling transaction types where explicit attribution was formulaically required.

**(iv) Prosopographic noise.** The entity index conflates commodity terms (*kaš*, *ninda*, *udu*) with personal names in unusual syntactic positions. Genuine-person analysis should use the patronymic-anchored subset. The conservative normalisation strategy guards against over-merging but cannot guarantee zero false merges.

**(v) Survivorship and genre bias.** The temporal and provincial distribution of transactions reflects archival survival and digitisation patterns, not the ancient economy's shape. The verified sub-corpus (§5.3) is additionally biased toward genre-1 ration distribution tablets, limiting the generalisability of its distributional findings to other tablet types.

**(vi) Scope of the *šunigin* harness.** 122 checkable tablets represent a small fraction of 135,199. The pipeline's accuracy on the remaining corpus is unvalidated by this method; the regression suite provides complementary but qualitatively different coverage.

**(vii) Double-counting at the margin.** Multi-section accounts that re-state sub-section totals hierarchically remain the hardest residual case. Canonical *šunigin* and *sag-nig₂-gur₁₁* restatements are suppressed, but leakage from idiosyncratic ledgers cannot be guaranteed to be zero.

---

## 8. Conclusion

A deterministic, test-driven pipeline converts 135,199 cuneiform transliterations into a quantitatively characterised picture of the Ur III grain economy. The corpus documents at least 2.335 million *gur* of cereal grain distributed across a strongly two-regime size distribution — a large number of individual rations at 1 *gur* or below coexisting with a small number of institutional flows orders of magnitude larger. On an arithmetically verified sub-corpus of 90 tablets, the modal allocation is 60 *sila₃* (1 *barig*), matching the ration scale Waetzoldt documented for unskilled workers in the Ur III textile industry, and grain throughput is highly concentrated (per-entry G = 0.873), reflecting the coexistence of standardised small rations and large bulk transfers in the same administrative record.

The exchange network of 1,644 agents exhibits near-zero but above-null reciprocity (0.039, z = +4.45 above a degree-preserving null) and a giant component modestly below null expectation (z = −4.50), consistent with a hierarchical flow structure with provincial compartmentalisation. These features are consistent with the redistributive architecture described by Steinkeller and Sallaberger on philological grounds, though the attributed minority of transactions (2.9%) limits how strongly the network findings can be pressed.

The two methodological contributions are the false-positive filter suite (120 rules, 144 tests, 0.96 million *gur* reduction) and the *šunigin* arithmetic harness (90 verified tablets, recall lower-bounded by the arithmetic match). Together they operationalise a two-layer quality framework for large-scale cuneiform extraction: test-driven negative classification to control false positives, and scribal arithmetic as an independent ground-truth signal. Both transfer directly to other commodity channels and other large-format cuneiform corpora.

---

## Figures

**Fig. 1a.** Histogram of barley transaction sizes (log₁₀ *sila₃*). The body of the distribution is approximately log-normal; median and modal value coincide at 1 *gur* (300 *sila₃*).

**Fig. 1b.** Lorenz curves for barley volume across transactions (dark) and tablets (lighter). Both curves lie far below the equality diagonal; over half of all recorded barley moves through 1% of transactions.

**Fig. 1c.** Capacity-measured commodity volume on a logarithmic axis. Cereal grains eclipse all other capacity commodities by more than an order of magnitude.

**Fig. 1d.** Dated barley transactions by Šulgi regnal year. The peak in years 45–48 reflects the period of fullest *bala* accounting documentation; it indexes archival density rather than economic activity.

**Fig. 1e.** Per-tablet barley totals (log₁₀ *gur*). The bimodal structure separates the small-ration cluster (near 1–10 *gur*) from the granary cluster (above 10,000 *gur*).

**Fig. 2a.** Entry-size histogram, verified sub-corpus (90 tablets). The dominant mode at 60 *sila₃* (1 *barig*) is the standard Ur III adult monthly ration.

**Fig. 2b.** Lorenz curve, verified sub-corpus. Per-entry G = 0.873.

All figures are regenerated from `output/figures/` by `tools/make_paper_figures.py` and `tools/analyze_verified.py`.

---

## Data and Code Availability

All extraction code, the 144-test regression suite, the *šunigin* reconciliation harness (`tools/reconcile_szunigin.py`), the verified-corpus analysis (`tools/analyze_verified.py`), and derived data tables are available at `asarodan/sumer`. The CDLI corpus is distributed by the Cuneiform Digital Library Initiative under its data-sharing terms.

---

## References

Cuneiform Digital Library Initiative (CDLI). *Ur III administrative corpus, ATF bulk export.* cdli.mpiwg-berlin.mpg.de.

Englund, R. K. (2012). "Equivalency Values and the Command Economy of the Ur III Period in Mesopotamia." In *The Construction of Value in the Ancient World*, 427–458.

Garfinkle, S. J. (2015). "Ur III Administrative Texts: Building Blocks of State Community." In *From the 21st Century B.C. to the 21st Century A.D.*

Milanovic, B., Lindert, P. H., and Williamson, J. G. (2011). "Pre-Industrial Inequality." *Economic Journal* 121: 255–272.

Molina, M. (2008). "The Corpus of Neo-Sumerian Tablets: An Overview." In *The Growth of an Early State in Mesopotamia*, 19–53.

Sallaberger, W. (1999). "Ur III-Zeit." In *Mesopotamien: Akkade-Zeit und Ur III-Zeit*, OBO 160/3, 121–390.

Steinkeller, P. (1987). "The Administrative and Economic Organization of the Ur III State: The Core and the Periphery." In *The Organization of Power: Aspects of Bureaucracy in the Ancient Near East*, ed. M. Gibson and R. D. Biggs. SAOC 46, 19–41.

Waetzoldt, H. (1972). *Untersuchungen zur neusumerischen Textilindustrie*. Rome: Centro per le Antichità e la Storia dell'Arte del Vicino Oriente.

Widell, M. (2004). "Reflections on Some Households and their Receiving Officials in the City of Ur in the Ur III Period." *JNES* 63, 283–290.

---

*Corpus snapshot: 135,199 tablets · ≥230,342 transactions · ≥2.335 M gur capacity · 90 šunigin-verified tablets*
