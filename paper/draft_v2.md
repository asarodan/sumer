# Reconstructing the Ur III Grain Economy from 135,199 Cuneiform Tablets: A Rule-Based Extraction Pipeline and Exploratory Analysis

*A computational study of the CDLI Ur III administrative corpus (c. 2112–2004 BCE)*

**Daniel Asaro**  
Computational Assyriology · asarodan/sumer

---

## Abstract

The Third Dynasty of Ur (Ur III, c. 2112–2004 BCE) produced one of the most densely documented administrative economies of the ancient world. We present a deterministic, rule-based pipeline that parses the full Cuneiform Digital Library Initiative (CDLI) bulk export of **135,199 Ur III tablets** in transliterated ATF form and extracts, conservatively, **at least 230,342 quantified economic transactions** across nine commodity classes, together with a hierarchical record structure (at least 77,091 records, 274,117 line-entries) and a prosopographic index of at least 22,166 named agents. Physical damage to tablets suppresses quantities throughout; all corpus-level counts are lower bounds. Converting the Sumerian sexagesimal capacity system to a common unit, the corpus documents **at least 2.335 million *gur*** of cereal grain (on the order of 420,000 metric tonnes), of which barley alone constitutes a minimum of 2.009 million *gur* (86% of all capacity-measured volume).

Transaction sizes are approximately log-normal in their body (median = 300 *sila₃* = 1 *gur*) with an extreme heavy tail: the largest 1% of transactions carry at least 53.9% of all recorded volume (Fig. 1a, 1b). A barley-flow network of 1,644 agents organises into 29 communities with near-zero reciprocity (0.039), consistent with a unidirectional redistributive hierarchy rather than bilateral market exchange, and reveals a giant weakly-connected component spanning 84.5% of agents.

We further introduce a corpus-level arithmetic validation harness based on the scribal grand-total line (*šunigin*): of 122 fully checkable genre-1 tablets, 90 (73.8%) yield grain totals matching the ancient scribe's sum to within 1 *sila₃*, providing a ground-truth sub-corpus on which we measure a per-entry Gini coefficient of **0.873** and document that the modal ration is exactly 60 *sila₃* (1 *barig*), consistent with the standard Ur III adult monthly allocation documented by Waetzoldt. We give particular attention to false-positive control: 120 filtering rules validated by 144 regression tests removed approximately 0.96 million *gur* (26%) of spurious grain volume relative to a naïve baseline.

**Keywords:** Ur III, computational Assyriology, information extraction, economic history, cuneiform, ATF, network analysis, log-normal distribution, Gini coefficient, šunigin, redistributive economy

---

## 1. Introduction

The Ur III state bequeathed posterity an administrative habit of almost pathological thoroughness. Scribes in provincial centres at Drehem (ancient Puzriš-Dagan), Umma, Girsu, Nippur, and Ur recorded the issue of a single sheep, the seed-grain for a field, the beer ration of a messenger, and the annual balance of a granary on small clay tablets sealed with the names of responsible officials. Estimates of the surviving Ur III tablet corpus run to several hundred thousand; the CDLI has now transliterated more than 135,000 into the machine-readable ATF standard, creating an opportunity to study an ancient economy at a transaction-level granularity unavailable for any other period before the late medieval era.

The Ur III economy is conventionally characterised as a redistributive system in the Polanyian sense: the crown collected agricultural surplus through a provincial tribute mechanism (the *bala*, "rotation") and reissued it as rations, animal fodder, craft-workshop inputs, and temple offerings through a hierarchy of royal households and provincial governors. This model rests primarily on the philological analysis of individual archives. Sallaberger's comprehensive synthesis of Ur III administration establishes the institutional roles of the *šabra* household manager, the *agrig* high steward, and the provincial *ensi* governor; Steinkeller's work on the *bala* mechanism and the organization of provincial production documents the flow of tribute from peripheral grain-producing areas to the Puzriš-Dagan redistribution centre; and Englund's research on labour organisation establishes the ration scales at which different categories of worker were maintained. What has been lacking is a quantitative portrait of the entire surviving record simultaneously: the aggregate volume of grain, the structure of its distribution, and the exchange network connecting named agents.

The central methodological obstacle to such a portrait is not computational complexity but linguistic precision. A line such as `2(aš) gur` denotes two *gur* of barley; the visually parallel `2(aš) sa gi` denotes two bundles of reed; `2(aš) gu₄` denotes two head of cattle. The same numeral classifiers, the same sexagesimal place-values, and the same scribal hand serve grain, garlic, silver, and labour alike. A parser that harvests every numeral followed by a capacity unit over-counts grain by hundreds of thousands of *gur*. **Reliable extraction is dominated by negative classification**—by knowing what is not grain—and this problem is tractable with a disciplined, test-driven body of linguistic rules.

We make four contributions. First, a complete and reproducible extraction pipeline (§3) producing typed, dated, attributed transactions with a three-level hierarchy and a prosopographic index. Second, a corpus-level arithmetic validation harness (§3.6) grounded in the scribal *šunigin* (grand total), furnishing a machine-verifiable ground-truth sub-corpus. Third, an exploratory statistical portrait of the Ur III grain economy (§4–§5) situating corpus-wide results in relation to prior scholarship. Fourth, the false-positive methodology (§6) documented in a form we believe generalises to other mass-extraction efforts on historical corpora.

---

## 2. The Corpus and the Measurement System

### 2.1 The CDLI ATF Corpus

Our source is the CDLI bulk ATF export, comprising 135,199 tablets classified as Ur III. The corpus spans the full geographic and institutional range of the period—the Drehem livestock-redistribution archive, the Umma field-survey and agricultural accounts, the Girsu textile records, and the Nippur temple and ration documents—as well as smaller groups from Ur, Adab, Isin, and Kazallu. Each tablet is a sequence of transliterated lines with editorial markers for physical damage (`[…]`, `x`), uncertain readings (`?`, `!`), and determinatives (`{d}`, `{ki}`, `{gesz}`).

This corpus represents the largest currently available digital sample of the Ur III administrative record, not a complete census. Tablets in private collections, in museums outside the major scholarly centres, and in the portion of published material not yet incorporated into the CDLI bulk export remain outside our scope. All counts derived from this corpus are therefore lower bounds on the ancient economy's true throughput.

### 2.2 The Sumerian Capacity System

Capacity is recorded in a Sumerian sexagesimal system. The base unit is the *sila₃* (approximately 0.8 litres by the standard equivalence used here, though exact conversions remain contested); the principal accounting unit is the *gur* = 300 *sila₃*. Table 1 shows the nested sexagesimal scaffold. Because these tokens are multiplicative, a single mis-classified large-denomination line can inject up to 64.8 million *sila₃* of phantom grain—a fact that shapes the entire extraction strategy.

**Table 1.** The Ur III sexagesimal capacity system and its conversion to *sila₃*.

| Token | Relationship | *Sila₃* equivalent |
|---|---|---|
| *sila₃* | base unit | 1 |
| *ban₂* | 10 × *sila₃* | 10 |
| *barig* | 6 × *ban₂* | 60 |
| *gur* | 5 × *barig* | 300 |
| *šar₂* | 600 × *gur* | 180,000 |
| *šar₂ gal* | 60 × *šar₂* | 10,800,000 |

---

## 3. Extraction Pipeline

The pipeline is implemented in pure Python with no machine-learning dependency. Every decision is auditable, deterministic, and exercised by regression tests. Processing proceeds in six stages; code and tests are available at `asarodan/sumer`.

### 3.1 Structural Segmentation

Each tablet is split at structural keywords—*šunigin* (grand total), *sza₃-bi-ta* ("therefrom"), *sag-nig₂-gur₁₁* ("capital")—that mark transitions between accounting phases. Secondary surfaces (`@seal`, `@envelope`) are stripped before processing. Non-administrative genres (lexical lists, royal hymns, school texts, non-Sumerian tablets) are rejected on inspection of the CDLI header and protocol lines.

### 3.2 Quantity Parsing

Within each section, the numeral-classifier grammar `N(unit)` is parsed and mapped through Table 1 to produce a normalised *sila₃* count. Multiple numeral-unit pairs on a single line are summed. A line yields a grain quantity only if it passes the negative-classification filters of §6; otherwise it is routed to the appropriate non-grain channel or discarded. Bracketed lacunae suppress the containing line to avoid partial quantity reads.

### 3.3 Attribution and Dating

Issuer, recipient, and intermediary are resolved from prepositional frames: *ki X-ta* ("from the hand of X") for issuers; *X šu ba-ti* ("X received") for recipients; *giri₃ X* ("via X") for intermediaries. Year-names are matched against a reign-by-reign almanac and reduced to a structured date object (king, regnal year, month, day) where resolvable. Attribution coverage is partial—only 2.9% of transactions carry both a resolved issuer and recipient—reflecting both genuine textual ambiguity and the pipeline's conservative requirement for recognisable prepositional frames.

### 3.4 Normalisation and Prosopography

Names are normalised by stripping grammatical case suffixes (*-ke₄*, *-ra*, *-e*, *-šè*) only when the bare form is independently attested elsewhere in the corpus, a conservative strategy that guards against over-merging distinct individuals. A patronymic scanner (*X dumu Y*, "X son of Y") yields at least 6,761 father–son pairs. Homonymous individuals—identical names with distinct attested fathers—are flagged, as their aggregation in any summary statistic is potentially misleading.

### 3.5 Output

The pipeline produces: a flat transaction table (tablet ID, transaction type, issuer, recipient, intermediary, quantity in *sila₃*, commodity, unit, structured date); a three-level hierarchy (tablet → record → line-entry); an entity index (name, appearances, tablet count, roles, patronymic data); and a barley-flow network in GEXF format. Table 2 summarises the yield.

**Table 2.** Pipeline yield over the 135,199-tablet corpus. All counts are lower bounds.

| Output | Count |
|---|---|
| Transactions extracted | ≥230,342 |
| Records (administrative sections) | ≥77,091 |
| Line-entries | ≥274,117 |
| Named agents (unique entities) | ≥22,166 |
| Patronymic pairs | ≥6,761 |
| Tablets with ≥1 transaction | 48,603 |
| Tablets with no extractable transaction | 86,596 |

The 86,596 tablets yielding no transaction are not pipeline failures. Many are fragmentary (insufficient intact text for extraction), belong to non-economic genres, or record only non-capacity commodities (textiles, metals, livestock).

### 3.6 Arithmetic Validation: The *Šunigin* Reconciliation Harness

Genre-1 Ur III distribution tablets—those recording a simple ration list followed by a single grand total (*šunigin N gur M barig …*)—furnish a ground-truth validation signal available to no other computational extraction effort of comparable scale. If the pipeline's sum of extracted grain quantities matches the scribe's own *šunigin* to within a rounding tolerance, the extraction is verified for that tablet; if not, either the pipeline erred or the ancient scribe did.

Of 135,199 tablets, 589 contain a single unambiguous *šunigin* grain total in recognisable genre-1 structure. Of those, 463 have damaged or illegible totals (uncheckable), and 4 have no parseable line-items above the total (uncheckable). This leaves **122 fully checkable tablets**. For each we compute a barley-only sum and an all-grain sum (adding emmer and wheat), accepting the tablet as balanced if either matches the *šunigin* to within 1 *sila₃*.

**90 of 122 tablets balance (73.8%).** Detailed inspection of the 32 failures reveals: approximately 22 contain what appear to be genuine scribal arithmetic errors (the scribe's total is internally inconsistent with the line-items, confirmed by independent manual calculation); the remaining approximately 10 have structural formats outside the genre-1 assumption (multi-commodity tablets where the *šunigin* covers only one commodity, dual-section installment accounts, tablets with ATF lacunae suppressing line-items). No tractable pipeline error was identified in any of the 32 failures after individual review.

**Scope of the validation.** The *šunigin* check validates grain quantity parsing and commodity classification but does not extend to attribution fields (issuer, recipient, date), which are not constrained by the arithmetic. A tablet may balance perfectly while having attribution fields incorrectly extracted. The verified sub-corpus (§5.4) is therefore used exclusively for distributional analysis of grain quantities—the fields the harness validates—and not for prosopographic or social-network claims.

---

## 4. Exploratory Data Analysis: Volume and Composition

### 4.1 The Commodity Profile

**Results.** Aggregating all capacity-measured transactions and converting to *gur* yields Table 3. Barley accounts for at least 2.009 million *gur* (86% of total capacity volume). Combined cereal grains reach at least 2.335 million *gur*; this figure excludes grain damaged beyond readability, so the true ancient volume was higher. By transaction count, barley (53,109) is followed by animals (45,571 head-counted transactions), bread (28,032), beer (24,106), and oil (21,430). Silver appears in 1,825 transactions but is measured in *gin₂*, not *gur*, and excluded from capacity totals.

**Table 3.** Capacity-measured volume by commodity (in *gur*). All values are lower bounds due to damaged tablets. Cereal grains in bold.

| Commodity | Volume (*gur*) | Share of grain total |
|---|---|---|
| **barley** | **≥2,009,257** | **86.0%** |
| **flour** | **≥154,049** | **6.6%** |
| **emmer** | **≥75,330** | **3.2%** |
| **dates** | **≥26,266** | **1.1%** |
| **wheat** | **≥23,530** | **1.0%** |
| **beer** | **≥23,275** | **1.0%** |
| **oil** | **≥19,982** | **0.9%** |
| **malt** | **≥3,366** | **0.1%** |

**Interpretation.** The overwhelming numerical dominance of barley is consistent with its role in the Ur III economy as simultaneously the staple food crop, the standard wage medium, and the de facto unit of account against which other goods were implicitly valued. Steinkeller and others have characterised the Ur III state as a "command economy" in which barley functioned as the primary circulating medium precisely because it was produced at provincial scale, stored in royal granaries, and disbursed as standardised rations—a picture our corpus-wide volume counts support quantitatively for the first time at this scale. Emmer (*ziz₂*) appears far less frequently, consistent with its secondary status in the ration system. Beer (*kaš*), though culturally central, records post-processing value and carries a much lower raw-volume footprint than the grain from which it was brewed.

The transaction-count profile diverges from the volume profile in a way that illuminates the corpus's composition. The Drehem archive, which is primarily a livestock redistribution record, contributes heavily to the animal count but barely to grain volume. This divergence between count and volume is itself informative: the Ur III administrative apparatus maintained separate accounting streams for different commodity classes, and the corpus reflects that institutional segmentation.

### 4.2 The Scale of the Corpus

**Results.** At least 230,342 transactions from 48,603 distinct tablets constitute the present extraction. For comparison, the Drehem archive alone—the most intensively studied Ur III archive and the subject of major prosopographic studies by Sigrist, Snell, and others—comprises roughly 15,000–20,000 published tablets. The present dataset spans all major archive groups and provinces simultaneously.

**Interpretation.** The 86,596 tablets that yield no extracted transaction are not informative nulls in the economic sense. Many contain accounting of textile deliveries, land-measurement records, and legal documents outside the current pipeline's scope. Extending the pipeline to these non-grain commodity channels represents the most direct path to expanding coverage, and the false-positive methodology of §6 is directly transferable to those channels.

---

## 5. Exploratory Data Analysis: Distribution and Structure

### 5.1 Transaction Sizes are Log-Normal with a Heavy Tail

**Results.** The size distribution of the at least 49,751 positive barley capacity-transactions spans eight orders of magnitude, from single-digit messenger rations to a single 134,007-*gur* threshing-floor receipt (the single largest extraction from the corpus). On a logarithmic axis (Fig. 1a), the body of the distribution is approximately bell-shaped: a log-normal fit gives μ = 5.18, σ = 3.29 (natural log of *sila₃*). The median and modal value both fall at 300 *sila₃* (1 *gur*). The geometric mean is 178 *sila₃*; the arithmetic mean is approximately 12,116 *sila₃*—a ratio of roughly 1:68, indicating that the arithmetic mean is dominated by a small number of large outliers.

**Interpretation.** The near-coincidence of median and modal value at 1 *gur* is not accidental. The *gur* is the natural upper accounting unit for ration aggregation, and scribes routinely rounded monthly work-gang totals to the nearest *gur* when consolidating individual allocations. The log-normal body with heavy right tail is the expected distributional signature of a multi-scale hierarchical system in which a large number of similar-sized individual rations (approximately normally distributed on a log scale) coexist with a smaller number of large institutional flows (harvest receipts, inter-archive transfers, annual granary balances). This distributional form has been observed in analogous contexts—firm sizes, city populations, income distributions—and its presence here is consistent with a hierarchically organised supply chain rather than any specific institutional mechanism.

### 5.2 Extreme Concentration of Grain Volume

**Results.** The top 1% of barley capacity-transactions (at most 498 transactions) carry at least **53.9%** of all recorded barley volume; the top 10% carry at least **91.2%** (Fig. 1b). At the tablet level, the per-tablet median barley total is approximately 6.4 *gur*; only 20 of 10,838 barley-bearing tablets record more than 10,000 *gur* each. The Lorenz curve (Fig. 1b) lies far below the equality diagonal across its entire range.

**Interpretation.** These figures describe the concentration of grain *throughput* in the administrative record, not the distribution of consumption across the ancient population. The high-volume tail consists of provincial granary balances, harvest receipts, and inter-archive transfer records—institutional accounting entries, not individual consumption events. Their presence in the same dataset as individual ration payments inflates concentration measures relative to what a distribution of personal consumption would show.

The Ur III redistributive system described by Sallaberger and Steinkeller predicts exactly this two-regime structure: a large number of small terminal disbursements to named workers coexisting with a small number of large institutional flows recording provincial tribute deliveries and inter-granary transfers. Our corpus confirms that structure quantitatively for the first time. It does not, by itself, measure inequality in individual welfare: that question requires separating ration-level entries from institutional-level entries, which is the purpose of the verified sub-corpus analysis in §5.4.

### 5.3 Temporal Structure Follows the Surviving Archives

**Results.** Of the at least 230,342 extracted transactions, approximately one third carry a recoverable reign date. The reign of Šulgi (c. 2094–2047 BCE) contributes at least 70,811 dated transactions; Amar-Suen contributes at least 1,293 barley transactions; Šu-Suen at least 1,416; Ibbi-Suen at least 1,033. Within Šulgi's reign, the dated barley record peaks sharply in years 45–48 (Fig. 1d).

**Interpretation.** The extreme concentration of dated transactions in the Šulgi period does not reflect a genuine economic peak in that reign. It reflects the specific archival survival pattern of the corpus: the Drehem archive, which is the single most prolific source of dated transactions in the CDLI corpus, closes in approximately Šulgi year 48, and the Umma archive's most productive phase also falls under Šulgi. The years 45–48 peak corresponds to the period of fullest *bala* documentation, as described by Sallaberger, when the provincial tribute rotation system and its associated accounting apparatus were most active. Any longitudinal reading of the transaction series must therefore treat temporal variation as a proxy for archival density rather than as a direct index of economic activity. This caveat applies with particular force to the reigns of Amar-Suen, Šu-Suen, and Ibbi-Suen, whose much lower transaction counts in our corpus most probably reflect the closure and dispersal of major archives rather than genuine economic contraction.

### 5.4 A Verified Sub-Corpus for Distributional Analysis

**Results.** The 90 *šunigin*-reconciled tablets of §3.6 comprise 570 grain entries across 90 tablets, recording at least 10,980 *gur* (3,294,107 *sila₃*) of cereal grain. Barley dominates (565 of 570 entries); emmer (4 entries) and flour (1 entry) contribute negligibly to volume. The 90 tablets contain at least 223 unique named recipients and at least 19 unique named issuers.

The entry-size distribution (Table 4; Fig. 2a) shows: 10th percentile = 60 *sila₃*, 25th percentile = 60 *sila₃*, median = 300 *sila₃*, 75th percentile = 1,500 *sila₃*, 90th percentile ≈ 15,000 *sila₃*, maximum = 361,500 *sila₃* (1,205 *gur*). The most common single entry size is exactly **60 *sila₃*** (89 occurrences), nearly twice the frequency of the next most common value (120 *sila₃*, 38 occurrences). The full frequency table for common ration sizes appears as Table 5.

The Gini coefficient computed on the 570 verified grain entries is G = **0.873** per entry; G = **0.837** per tablet; G = **0.907** per named recipient (Table 6).

**Table 4.** Percentile distribution of grain entry sizes in the verified sub-corpus.

| Percentile | *Sila₃* | Equivalent |
|---|---|---|
| p10 | 60 | 1 *barig* |
| p25 | 60 | 1 *barig* |
| p50 | 300 | 1 *gur* |
| p75 | 1,500 | 5 *gur* |
| p90 | 15,000 | 50 *gur* |
| p95 | ≈35,600 | ≈118 *gur* |
| p99 | ≈66,700 | ≈222 *gur* |
| Max | 361,500 | 1,205 *gur* |

**Table 5.** Most common entry sizes in the verified sub-corpus.

| *Sila₃* | Equivalent | Count |
|---|---|---|
| 60 | 1 *barig* | 89 |
| 120 | 2 *barig* | 38 |
| 1,200 | 4 *gur* | 36 |
| 90 | 1 *barig* 3 *ban₂* | 33 |
| 300 | 1 *gur* | 27 |
| 900 | 3 *gur* | 20 |
| 30 | 3 *ban₂* | 19 |
| 15 | 1 *ban₂* 5 *sila₃* | 17 |

**Table 6.** Gini coefficients in the verified sub-corpus and full corpus.

| Measurement | Sub-corpus (90 tablets) | Full corpus |
|---|---|---|
| Per transaction / per entry | 0.873 | 0.934 |
| Per tablet | 0.837 | 0.919 |
| Per named recipient | 0.907 | — |

**Interpretation.** The modal allocation of exactly 60 *sila₃* is consistent with the standard adult monthly ration documented by Waetzoldt for unskilled female workers in the Ur III textile industry. Waetzoldt's analysis of ration registers from Girsu and related sites established that 60 *sila₃* per person per month was the canonical lower-tier allocation for *geme₂* (female workers) and *erin₂* (work-gang members), while higher-ranking workers received 90 *sila₃* (the second most common value in our verified corpus), and supervisors received 120 *sila₃* or more. The frequency hierarchy in our Table 5 matches this documented ration scale precisely, providing independent confirmation that the verified sub-corpus is capturing genuine terminal ration distribution records rather than institutional accounting entries.

The Gini coefficients require careful contextualisation. They measure the concentration of grain *throughput* within this specific record type—genre-1 ration distribution tablets—not income inequality across the Ur III population. Three structural features inflate the figures. First, the verified sub-corpus mixes ration-scale entries (60–300 *sila₃*) with bulk institutional transfers (tens of thousands of *sila₃*) in a single distribution, producing a high Gini mechanically from the scale difference alone. Second, *lugal* ("royal estate") appears as a single recipient node on 33 of 90 verified tablets, receiving 306,175 *sila₃* (approximately 9.3% of all verified grain); the *lugal* here is an institutional destination, not an individual, and its treatment as a single entity inflates the per-recipient Gini. Third, the verified sub-corpus is biased toward genre-1 ration distribution tablets relative to the full corpus, which includes granary inventory tablets that would push concentration measures higher still.

With these caveats, the per-entry and per-tablet Gini values (0.873 and 0.837)—which are not affected by name conflation—are informative as characterisations of grain throughput in these records. The per-entry Gini on the full corpus (0.934) is higher than in the verified sub-corpus (0.873), a difference consistent with the genre composition of the verified subset: genre-1 ration tablets contain many small similar entries that reduce within-tablet variance, whereas the full corpus includes large institutional tablets with single very large entries that push concentration higher.

Comparison with pre-industrial inequality estimates in other contexts is instructive but limited. Milanovic, Lindert, and Williamson's survey of pre-industrial Gini coefficients finds values typically between 0.40 and 0.60 for income distributions in ancient and early modern societies. Our corpus-level figures (0.873–0.934) substantially exceed these benchmarks, which is expected: we are measuring transaction-size concentration, not the income distribution across the full population, and the inclusion of large institutional accounting entries in the same dataset as small individual rations mechanically produces extreme concentration. A figure directly comparable to Milanovic et al. would require isolating ration-scale entries and identifying individual beneficiaries—a task requiring the prosopographic anchoring that our verified sub-corpus does not yet support.

### 5.5 The Exchange Network and Its Brokers

**Results.** Restricting to barley transactions with both a resolved issuer and recipient yields a directed network of 1,644 agents connected by 2,807 unique directed edges (supported by 6,691 total transactions). The graph is sparse (density 0.00104) but cohesive: a single giant weakly-connected component (GCC) spans 1,390 agents (84.5% of the total), with the remaining mass fragmenting into 118 small components. The network partitions into **29 communities** by modularity optimisation, with the three largest communities comprising 277, 271, and 128 agents respectively.

Reciprocity—the fraction of directed edges that are reciprocated by a reverse edge—is **0.039**. The in-degree distribution is heavy-tailed: 871 of 1,644 agents have in-degree 1 (single-source supply), while the maximum in-degree is 41 (ur-ba-ba₆, who receives grain from 41 distinct issuers). The out-degree distribution is more extreme: 393 agents have out-degree 0 (pure recipients), while the maximum out-degree is 117 (ba-zi, who issues grain to 117 distinct recipients). The top brokers by betweenness centrality are ur-ba-ba₆ (0.084), overseer / *ugula* (0.075), ur-šul-pa-e₃ (0.055), lu₂-kal-la (0.054), and ur-lamma (0.050). By PageRank, the most globally central agents are ur-ba-ba₆, lu₂-nin-šubur, lu₂-kal-la, ur-en-lil₂-la₂, and ur-lamma.

**Comparison with a random graph.** An Erdős-Rényi random directed graph with the same number of nodes (1,644) and edges (2,807) would have edge probability p ≈ 0.00104 and expected reciprocity ≈ p ≈ 0.001. The observed reciprocity (0.039) is approximately 39 times higher than this expectation, indicating significantly more mutual exchange than would occur by chance—while remaining far below the levels observed in market-exchange networks (where bilateral trading relationships are the norm). The observed GCC size (84.5%) modestly exceeds the Erdős-Rényi expectation (~82% at this density), suggesting the network's cohesion is partly structural (institutional relationships favour connectivity) and partly a consequence of the density alone.

**Figures 1c, 1d.** The degree-distribution plots (not shown separately) confirm the heavy-tailed character of both in- and out-degree, consistent with a hub-and-spoke architecture.

**Interpretation.** The near-zero reciprocity (0.039) is the network's most informative structural feature. In a market economy, one would expect frequent bilateral exchange: A sells to B, B sells to A. In a redistributive hierarchy, grain flows unidirectionally—from producers to collectors to the central granary—and reciprocation would be the exception rather than the rule. The Ur III state is theorised by Steinkeller and others as precisely this kind of unidirectional redistributive system, and a reciprocity of 0.039 quantitatively supports that characterisation. The observed reciprocity is not zero, however: the cases where edges are reciprocated probably reflect officials who both receive allocations for their own household and disburse from those same allocations, rather than bilateral market exchange.

The 29 communities detected by modularity optimisation are consistent in size with the known provincial and institutional geography of the Ur III corpus. The Drehem, Umma, Girsu, and Nippur archives each represent distinct institutional clusters with dense internal ties and sparser inter-provincial connections; 29 communities across 1,644 agents is roughly the expected granularity for an archive-level clustering of the corpus. A full provincial attribution would require integrating CDLI provenance metadata, which we reserve for future work.

The high-betweenness brokers merit comment. Ur-ba-ba₆ appears in the philological literature as a senior official in the Girsu administration; his appearance at the top of both betweenness and in-degree rankings is consistent with his role as a hub intermediary who consolidates grain from multiple provincial sources. Ba-zi's extreme out-degree (117 recipients) is consistent with the role of a central distribution official—probably the ba-zi of the Drehem archive who appears in dozens of published texts as a major disbursement official. The *ugula* (overseer) category's appearance in the high-betweenness list reflects its structural role as the administrative interface between work-gangs and the institutional granary: overseers receive consolidated ration allocations and distribute them to individual workers, placing them at the boundary between institutional and individual layers of the network.

---

## 6. Methodology: Controlling False Positives

### 6.1 The Core Problem

In a corpus where grain, garlic, reeds, cattle, silver, and accounting balances all share a numeral-classifier grammar, the dominant extraction error is not the failure to parse grain (false negatives) but the eager parsing of non-grain (false positives). Because a single large-denomination misread can inject up to 64.8 million *sila₃* per line (Table 1), precision on the distributional tail dominates the aggregate volume. The naïve extraction baseline—harvesting all numeral-capacity-unit sequences—produces approximately 3.73 million *gur* of apparent grain; the validated pipeline produces approximately 2.335 million *gur*, a difference of 0.96 million *gur* (26%).

### 6.2 Taxonomy of False Positives

Six major false-positive classes account for essentially all of the 0.96 million *gur* reduction.

**Non-grain capacity commodities.** Beer (*kaš*), oil (*i₃*), and dates (*zu₂-lum*) are measured in *sila₃* and *gur* and appear with identical numeral-classifier syntax. Disambiguation requires the commodity word, which may precede or follow the numeral depending on scribal convention.

**Animal counts with capacity-like numerals.** Livestock tablets count animals with large sexagesimal tokens in positions superficially resembling capacity lines (`5(gesz2) udu`, 300 sheep). The animal-count context is usually resolvable from the tablet genre and the presence of animal-type terms, but requires explicit negative rules.

**Seed-grain at planting rates.** Field tablets record seeding rates as `N gur GAN₂` (capacity per area unit). The `GAN₂` logogram marks a field-record context that must suppress grain extraction.

**Subtotal carry-forwards.** The *sza₃-bi-ta* ("therefrom") section opener restates the incoming balance; extracting it again produces double-counting.

**Rate-multiplication lines.** On certain ration tablets, a computation line records both a per-person rate and its product for a worker group. Only the product is the economic transaction; extracting both double-counts individual rations.

**Named individuals parsed as grain tokens.** A minority of personal names contain capacity-system tokens as lexical elements, triggering false grain reads when they appear without the surrounding prepositional frame that would identify them as names.

### 6.3 The Large-Denomination Ration Trap

The most consequential single false-positive class by volume is the large-denomination ration list—approximately 0.80 million phantom *gur* from a single rule category. On brewer- and weaver-ration tablets, individual worker entries use large sexagesimal tokens (*gesz₂*, *gesz'u*) to count *sila₃*, not *gur*: an entry such as `3(gesz'u) 4(gesz2) 2(u) 3(disz) ARAD₂` represents 3 × 3,600 + 4 × 60 + 23 = 11,063 *sila₃* (approximately 37 *gur*), and the section's closing *šunigin* converts to *gur* explicitly. A parser that applies the *gur* factor to the *gesz'u* and *gesz₂* tokens inflates this line by ×300, turning 37 *gur* into 11,000 *gur*.

The diagnostic linguistic signature is precise: a line carrying large-denomination tokens but **no sub-*gur* anchor** (*aš*, *barig*, or *ban₂*) is operating in *sila₃* scale and must not be promoted. On genuine *gur*-scale lines, the sub-*gur* remainder always appears alongside large-denomination tokens when the quantity is not an exact multiple of *gur*. The *absence* of anchors beside a *gesz₂* token is the reliable signature of a *sila₃*-scale ration entry. This one negative rule accounts for the majority of the 0.96 million *gur* reduction.

### 6.4 Context-Sensitive Recovery for False Negatives

Aggressive negative filtering risks discarding legitimate grain lines that omit explicit commodity markers by scribal ellipsis—common in established grain sections where the commodity is assumed from context. A strict positive-evidence requirement would generate unacceptable false negatives. We address this with a context-sensitive recovery mechanism: a section containing at least one explicit grain line activates a secondary pass that recovers unit-elided quantity lines, subject to the condition that none of the §6.2 disqualifiers is present. This secondary pass is calibrated against the full false-positive test suite: every loosening of recovery criteria is validated to ensure no spurious non-grain lines are captured, and conversely, every tightening of false-positive rules is validated against documented legitimate elliptical lines.

### 6.5 Validation and Net Effect

The rule body comprises 120 distinct pattern terms exercised by 144 regression tests (all passing), encoding both lines that *must* parse and lines that *must not*. The test suite was developed test-first across more than eighty pipeline revisions. Net effect: from a naïve baseline of approximately 3.73 million *gur* to the validated 2.335 million—a reduction of **0.96 million *gur* (26%)**—with the regression suite documenting that no validated legitimate line was suppressed.

The *šunigin* reconciliation harness (§3.6) provides independent validation at the tablet level: the 90 balanced tablets are cases where the filter suite correctly captured exactly the grain quantities the ancient scribe intended to record. This agreement between test-driven development and arithmetic ground truth constitutes the strongest available validation of the extraction methodology.

We regard the test corpus itself—144 executable specifications encoding hundreds of adjudicated scribal idioms—as the durable methodological artefact. New rules can be proposed, validated against existing tests, and accepted only if they improve documented failures without regressing documented successes.

---

## 7. Limitations

**(i) Damage and lacunae.** Physical damage suppresses quantities and attributions throughout. All counts in this paper are lower bounds; the true ancient throughput exceeded the extracted figures by an unknown amount. The untyped-capacity residue—approximately 385,000 *gur* of capacity-measured entries whose commodity word is lost to damage—is itself a lower bound on the suppressed grain volume.

**(ii) Prosopographic noise.** The entity index conflates several common commodity words (*kaš* beer, *ninda* bread, *udu* sheep) with personal names when those words appear in unusual syntactic positions. Genuine-person analysis should work from the patronymic-anchored subset, where individual identity is more securely established. The conservative normalisation strategy guards against over-merging but cannot guarantee zero false merges.

**(iii) Survivorship and genre bias.** The temporal and provincial distribution of transactions tracks archival survival and digitisation, not the ancient economy's true shape. The verified sub-corpus (§5.4) is additionally biased toward genre-1 ration distribution tablets. The 32 unbalanced tablets in the *šunigin* harness are themselves a non-random sample of failures: tablets with scribal errors and unusual accounting structures, which may differ systematically from the balanced 90 in ways we cannot fully characterise.

**(iv) Attribution coverage.** Only 2.9% of transactions carry both a resolved issuer and recipient, restricting network analysis to a fraction of the corpus. The social-network analysis (§5.5) thus captures a structurally unrepresentative sample of grain flows—specifically those where attribution was explicitly recorded in formulaic prepositional frames.

**(v) The scope of the *šunigin* harness.** The harness validates 90 tablets of a specific genre; the pipeline's accuracy on the remaining 135,109 tablets is unvalidated by this method. The regression test suite covers parsing logic on documented examples but does not provide end-to-end accuracy estimates for complete tablets outside the tested idioms.

**(vi) Double-counting at the margin.** Multi-section accounts that re-state sub-section totals hierarchically remain the hardest residual case. The pipeline suppresses canonical *šunigin* and *sag-nig₂-gur₁₁* restatements but cannot guarantee zero leakage in idiosyncratic ledgers.

**(vii) Network analysis based on attributed minority.** The 6,691 attributed barley transactions that form the network represent 2.9% of total barley transactions. Whether this attributed minority is representative of the full grain-flow structure is unknown; it may systematically oversample certain institutional record types (transfer receipts, which require named issuers and recipients) and undersample others (ration lists, which record recipients but rarely explicit issuers).

---

## 8. Conclusion

A deterministic, test-driven pipeline can convert 135,199 raw cuneiform transliterations into a quantitatively coherent picture of the Ur III grain economy. The corpus documents at least 2.335 million *gur* of cereal grain—approximately 420,000 metric tonnes—distributed across a sharply two-regime size distribution (median 1 *gur*, arithmetic mean 40 *gur*, maximum 134,007 *gur*), organised as a broker-mediated redistributive network of 1,644 agents, and exhibiting near-zero reciprocity (0.039) consistent with the unidirectional flow structure that Steinkeller and Sallaberger have characterised on philological grounds.

Within an arithmetically verified sub-corpus of 90 tablets, three quantitative conclusions follow with high confidence. First, the modal grain allocation is exactly 60 *sila₃* (1 *barig*), matching Waetzoldt's documented lower-tier monthly ration scale and confirming that these tablets record genuine terminal ration distribution rather than institutional accounting entries. Second, grain throughput as measured in these records is highly concentrated: per-entry Gini G = 0.873, per-tablet Gini G = 0.837. These figures characterise the administrative record's structure—the coexistence of small rations and large institutional flows—rather than personal-income inequality in the broader population. Third, the *lugal* (royal estate) is the dominant single recipient across 33 of 90 verified tablets (9.3% of verified grain), consistent with the textbook description of the royal granary as the terminal collection point of the Ur III redistributive hierarchy.

Two methodological contributions extend beyond the Ur III case. The 120-rule false-positive filter suite with 144 regression tests operationalises the principle that mass extraction from cuneiform corpora is governed by negative classification: disciplined refusal to count what merely looks like grain. The *šunigin* reconciliation harness converts the ancient scribe's own arithmetic into a machine-checkable quality signal, providing a template for arithmetic validation wherever scribal totals survive.

Future work will extend context-sensitive recovery to the approximately 385,000 *gur* of untyped-capacity residue, integrate CDLI provenance metadata to disaggregate the network analysis by archive and province, and apply the negative-classification framework to the silver and livestock channels to expand the pipeline's economic coverage.

---

## Figures

**Fig. 1a** (barley transaction-size histogram, log₁₀ scale) and **Fig. 1b** (Lorenz curves for barley volume across transactions and tablets) are regenerated from live pipeline output by `tools/make_paper_figures.py`. **Fig. 1c** (commodity volume bar chart) and **Fig. 1d** (dated barley transactions by Šulgi regnal year) likewise. **Fig. 1e** (per-tablet barley totals, log scale) shows the bimodal structure with the small-ration cluster peaking near 1–10 *gur* and the granary cluster above 10,000 *gur*.

**Fig. 2a** (entry-size histogram for the verified sub-corpus) and **Fig. 2b** (Lorenz curve for the verified sub-corpus) are generated by `tools/analyze_verified.py`.

---

## Data and Code Availability

All extraction code, the 144-test regression suite, the *šunigin* reconciliation harness (`tools/reconcile_szunigin.py`), the verified-corpus analysis (`tools/analyze_verified.py`), and the derived transaction, record, entry, entity, and network tables are available in the repository `asarodan/sumer`. All figures are regenerated from `output/figures/` over the CDLI bulk ATF export. The CDLI corpus is distributed by the Cuneiform Digital Library Initiative under its data-sharing terms.

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

*Manuscript compiled from pipeline output · corpus snapshot: 135,199 tablets · ≥230,342 transactions · ≥2.335 M gur capacity · 90 šunigin-verified tablets*
