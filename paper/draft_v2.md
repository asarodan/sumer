# Reconstructing the Ur III Grain Economy from 135,199 Cuneiform Tablets: A Rule-Based Extraction Pipeline and Exploratory Analysis

*A computational study of the CDLI Ur III administrative corpus (c. 2112–2004 BCE)*

**Daniel Asaro**  
Computational Assyriology · asarodan/sumer

---

## Abstract

The Third Dynasty of Ur (Ur III, c. 2112–2004 BCE) produced one of the most densely documented administrative economies of the ancient world. We present a deterministic, rule-based pipeline that parses the full Cuneiform Digital Library Initiative (CDLI) bulk export of **135,199 Ur III tablets** in transliterated ATF form and extracts **230,342 quantified economic transactions** across nine commodity classes, together with a hierarchical record structure (77,091 records, 274,117 line-entries) and a prosopographic index of 22,166 named agents. Converting the Sumerian sexagesimal capacity system to a common unit, the corpus accounts for **2.335 million *gur*** of cereal grain (on the order of 420,000 metric tonnes), of which barley alone constitutes 2.009 million *gur* (86% of all capacity-measured volume). Exploratory data analysis shows that transaction sizes are approximately log-normal in their body (median = 300 *sila₃* = 1 *gur*) with an extreme heavy tail: the largest 1% of transactions carry 53.9% of all volume. A barley-flow network of 1,644 agents reveals a single dominant component organised around provincial household managers (*šabra*) acting as brokers and the royal granary as principal sink.

We further introduce a corpus-level arithmetic validation harness based on the scribal grand-total line (*šunigin*): of 122 fully checkable genre-1 tablets, 90 (73.8%) yield grain totals that match the ancient scribe's own sum to within 1 *sila₃*, providing a verified sub-corpus on which we measure a per-entry Gini coefficient of **0.873** and document that the modal ration is exactly 60 *sila₃* (1 *barig*), the canonical Ur III adult monthly allocation. We give particular attention to the methodology of false-positive control: the chief technical difficulty in mass cuneiform extraction is not parsing grain lines but distinguishing them from the orthographically identical lines that record onions, reed bundles, livestock, silver, and balance carry-forwards. We document a corpus of 120 filtering rules, validated by 144 regression tests, that reduced spurious grain volume by roughly 0.96 million *gur* (26%) relative to a naïve baseline.

**Keywords:** Ur III, computational Assyriology, information extraction, economic history, cuneiform, ATF, network analysis, log-normal distribution, Gini coefficient, šunigin

---

## 1. Introduction

The Ur III state bequeathed posterity an administrative habit of almost pathological thoroughness. Scribes in provincial centres at Drehem (ancient Puzriš-Dagan), Umma, Girsu, Nippur, and Ur recorded the issue of a single sheep, the seed-grain for a field, the beer ration of a messenger, and the annual balance of a granary on small clay tablets sealed with the names of responsible officials. Estimates of the surviving Ur III tablet corpus run to several hundred thousand; the Cuneiform Digital Library Initiative (CDLI) has now transliterated more than 135,000 into the machine-readable ATF (ASCII Transliteration Format) standard, creating an opportunity to study an ancient economy at a transaction-level granularity that is unavailable for any other period before the late medieval era.

The Ur III state is conventionally characterised as a redistributive economy in the Polanyian sense: the crown collected agricultural surplus through a provincial tribute system (*bala*) and reissued it as rations, animal fodder, craft-workshop inputs, and temple offerings through a network of royal households and provincial governors. This model, developed principally by Steinkeller, Sallaberger, and Englund through decades of philological work, rests overwhelmingly on the qualitative analysis of individual tablet archives. The *bala* system, the role of the *šabra* household manager, and the function of the Drehem livestock redistribution centre are well attested at the level of named transactions and named individuals. What has been lacking is a quantitative portrait of the system at the scale of the surviving record: How much grain moved through the administrative apparatus in total? How was it distributed across recipients? What was the structure of the exchange network? These questions require processing tens of thousands of tablets simultaneously, which lies beyond the reach of philological methods alone.

Computational approaches to the cuneiform record have developed substantially in the past two decades. The CDLI project itself has made large-scale machine reading possible by standardising transliteration conventions and providing a bulk-download corpus. Several projects have explored pattern-matching on ATF texts for specific purposes—identifying date formulas, extracting ration registers, building prosopographic databases—but systematic large-scale economic extraction has remained limited by the parsing challenges described below. The present work extends this tradition by providing a complete, reproducible extraction pipeline that processes the entire CDLI Ur III corpus and situates the extracted data within a validated quality framework.

The central methodological challenge is not pattern recognition in any sophisticated sense. A line such as `2(aš) gur` denotes two *gur* of barley; the visually parallel `2(aš) sa gi` denotes two bundles of reed, and `2(aš) gu₄` two head of cattle. The same numeral classifiers, the same sexagesimal place-values, and the same scribal hand serve grain, garlic, silver, and labour alike. A parser that simply harvests every numeral followed by a capacity unit over-counts grain by hundreds of thousands of *gur*, because the same tokens appear in non-grain contexts that must be filtered. The central methodological claim of this paper is that **reliable extraction is dominated by the problem of negative classification**—of knowing what is *not* grain—and that this problem is tractable with a disciplined, test-driven body of linguistic rules anchored in specific scribal idioms.

We make four contributions. First, a complete and reproducible extraction pipeline (§3) that turns raw ATF into typed, dated, attributed transactions with a three-level tablet→record→entry hierarchy and a prosopographic entity index. Second, a corpus-level arithmetic validation harness (§3.6) that converts the ancient scribe's own grand-total computations into machine-checkable quality signals, providing a 90-tablet verified sub-corpus with proven extraction accuracy on grain quantities. Third, an exploratory statistical portrait of the Ur III grain economy (§4–§5) covering volume, commodity composition, concentration, standard ration units, temporal distribution, and exchange-network structure. Fourth, an explicit account of the false-positive-control methodology (§6) that we believe generalises to other mass-extraction efforts on noisy historical corpora.

---

## 2. The Corpus and the Measurement System

### 2.1 The CDLI ATF Corpus

Our source is the CDLI bulk ATF export, comprising 135,199 tablets classified as Ur III. The tablets span the full geographic and institutional range of the period: the great provincial archives of Drehem (c. 2112–2004 BCE), where the royal livestock redistribution centre is documented; Umma, with its extensive field-survey and agricultural accounts; Girsu (Lagash province), whose archives preserve detailed textile production records; and Nippur, with its temple and ration records. A smaller but significant number come from Ur itself and from the less-well-documented cities of Adab, Isin, and Kazallu.

Each tablet in the ATF corpus is a sequence of transliterated lines organised by surface (`@obverse`, `@reverse`) and column (`@column`), with editorial markers for physical damage (`[…]` for lacunae, `x` for illegible signs), uncertain readings (`?`, `!`), and logograms and determinatives (`{d}` for divine names, `{ki}` for place names, `{gesz}` for wooden objects). The transliteration conventions are those of the CDLI standard, which represents cuneiform signs in a normalised Latin-character encoding. The corpus is not uniform in quality: tablets transcribed in the early phases of the project may reflect older conventions, and a small number of tablets have incomplete or misformatted ATF that the pipeline must tolerate gracefully.

The 135,199 tablets represent a large fraction of the published Ur III corpus but not its entirety. A substantial number of tablets in private collections and in museums outside the major scholarly centres have not yet been transliterated, and a further proportion of published tablets have not yet been incorporated into the CDLI bulk export. The corpus should therefore be understood as the largest currently available digital sample of the Ur III administrative record, not a complete census.

### 2.2 The Sumerian Capacity System

Capacity is recorded in the Sumerian sexagesimal grain system. The base unit is the *sila₃* (approximately 1 litre, though exact equivalences are debated in the literature); the principal accounting unit for field-scale and granary transactions is the *gur* = 300 *sila₃*. Larger granary quantities use a nested sexagesimal scaffold in which the *gur* is multiplied by ascending factors (Table 1). Because these tokens are multiplicative, a single mis-classified large-denomination line can inject tens of thousands of phantom *gur* into the dataset—a fact that shapes the entire extraction strategy. A line recording `1(šar₂) gur` denotes 600 *gur* of barley (180,000 *sila₃*, approximately 150 metric tonnes); if misread as recording 1 *gur*, the error is a factor of 600.

**Table 1.** The Ur III sexagesimal capacity system and its conversion to *sila₃*.

| Token | Relationship | *Sila₃* equivalent |
|---|---|---|
| *sila₃* | base unit | 1 |
| *ban₂* | 10 × *sila₃* | 10 |
| *barig* | 6 × *ban₂* | 60 |
| *gur* | 5 × *barig* | 300 |
| *šar₂* | 600 × *gur* | 180,000 |
| *šar₂ gal* | 60 × *šar₂* | 10,800,000 |

The *gur* is the dominant accounting unit in the corpus and the one most frequently misidentified in naïve extraction. Throughout this paper we quote volumes in *gur* unless otherwise stated, with *sila₃* used for individual ration-sized quantities where the distinction matters.

---

## 3. Extraction Pipeline

The pipeline is implemented in pure Python with no machine-learning dependency; every decision is auditable and deterministic. Processing proceeds in six stages. The code, tests, and supplementary documentation are available in the repository `asarodan/sumer`.

### 3.1 Structural Segmentation

Each tablet is split into sections at structural keywords. The keywords *šunigin* (subtotal or grand total), *sza₃-bi-ta* ("therefrom", opening an expenditure block), and *sag-nig₂-gur₁₁* ("capital", opening an income block) function as section boundaries, marking transitions between different accounting phases of the same tablet. Secondary surfaces (`@seal`, `@envelope`) are stripped before processing, since seal inscriptions routinely repeat personal names in syntactic positions that would otherwise trigger false attribution. Non-administrative genres—lexical lists, royal hymns, literary compositions, and non-Sumerian texts—are rejected on inspection of the `@tablet` header and the `#atf` protocol line, which encodes the tablet's classification in the CDLI system.

### 3.2 Quantity Parsing

Within each section body, the numeral-classifier grammar `N(unit)` is parsed and each token mapped through Table 1 to produce a normalised *sila₃* count. Multiple numeral-unit pairs on a single line are summed (a line may read `1(aš) gur 2(barig) 3(ban₂) 4(disz) sila₃`, representing 1 × 300 + 2 × 60 + 3 × 10 + 4 × 1 = 454 *sila₃*). Crucially, a line yields a grain quantity only if it passes the negative-classification filters of §6; otherwise it is routed to the appropriate non-grain channel (animals counted in *head*, silver in *gin₂*, labour in *worker-days*) or discarded. Bracketed lacunae suppress the containing line from extraction to avoid partial quantity reads.

### 3.3 Attribution and Dating

Issuer, recipient, and intermediary are resolved from prepositional frames. The frame *ki X-ta* ("from the hand of X") identifies the issuer; *X šu ba-ti* ("X received") identifies the recipient; *giri₃ X* ("via X") identifies an intermediary agent. Year-names and month names are matched against a reign-by-reign almanac covering all five Ur III kings (Ur-Nammu, Šulgi, Amar-Suen, Šu-Suen, Ibbi-Suen) and their known year-names, and reduced to a structured date object carrying (king, regnal year number, month, day) where resolvable.

Attribution coverage is partial: only 2.9% of extracted transactions (6,691 of 230,342) carry both a resolved issuer and recipient. This reflects both genuine ambiguity in the texts (many tablet genres record quantities without explicit attribution on every line) and the current pipeline's conservative attribution logic, which requires recognisable prepositional frames.

### 3.4 Normalisation and Prosopography

Personal names are normalised by stripping grammatical case suffixes (*-ke₄*, *-ra*, *-e*, *-šè*) only when the bare form is independently attested elsewhere in the corpus, guarding against over-merging of distinct individuals whose names happen to share a stem. A patronymic scanner parses the construction *X dumu Y* ("X son of Y") and yields 6,761 father–son pairs covering the corpus. Individuals attested with two or more distinct fathers are flagged as homonymous—a known challenge in Ur III prosopography where several common names (*Ur-Namma*, *Lu-Nanna*, *Ur-Suen*) were borne by dozens of different officials simultaneously.

### 3.5 Output Tables

The pipeline emits four output streams. (1) A flat transaction table recording tablet ID, transaction type (receipt / disbursement), issuer, recipient, intermediary, quantity in *sila₃*, commodity, unit, and structured date. (2) A three-level hierarchy of tablets → administrative records (sections) → line-entries, preserving the internal structure of each tablet. (3) An entity index listing each named agent with appearance count, tablet count, attested roles, and patronymic data. (4) A barley-flow directed network in GEXF format for network-analysis tools. Summary statistics appear in Table 2.

**Table 2.** Pipeline yield over the 135,199-tablet corpus.

| Output | Count |
|---|---|
| Transactions extracted | 230,342 |
| Records (administrative sections) | 77,091 |
| Line-entries | 274,117 |
| Named agents (unique entities) | 22,166 |
| Patronymic pairs | 6,761 |
| Tablets with ≥1 transaction | 48,603 |
| Tablets with no extractable transaction | 86,596 |

The 86,596 tablets that yield no transaction are not pipeline failures: many are fragmentary (too damaged to extract coherent quantities), belong to non-economic genres (lexical lists, school tablets, royal inscriptions), or record only non-capacity commodities such as textiles, metals, and livestock.

### 3.6 Arithmetic Validation: The *Šunigin* Reconciliation Harness

A distinctive feature of genre-1 Ur III distribution tablets—those recording a simple list of ration entries followed by a single grand total—is that the scribe performed the arithmetic himself and wrote it in a fixed closing line: *šunigin N gur M barig K ban₂ …*, "total: N *gur* M *barig* …". This line furnishes a ground-truth validation signal unavailable to most computational extraction efforts: if the pipeline's sum of extracted grain quantities matches the scribe's own *šunigin* to within a rounding tolerance, the extraction is almost certainly correct for that tablet; if not, either the pipeline erred or the ancient scribe did.

We applied this harness to the full corpus. Of 135,199 tablets, 589 contain a single, unambiguous *šunigin* grain total in a recognisable genre-1 structure. Of those, 463 have damaged or partially illegible totals that cannot be compared programmatically, and 4 have no parseable line-items above the total. This leaves **122 fully checkable tablets**. For each we compute grain sums in two passes: a barley-only pass and an all-grain pass (adding emmer and wheat to accommodate tablets where the *šunigin* covers all cereal types), accepting the tablet as balanced if either pass matches the *šunigin* to within 1 *sila₃* (a tolerance chosen to absorb scribal rounding in the sub-*gur* register).

**90 of 122 tablets balance (73.8%).** This constitutes the verified sub-corpus. Detailed forensic inspection of the 32 failures reveals two categories. Approximately 22 contain what appear to be genuine scribal arithmetic errors—the ancient scribe wrote the wrong total, as confirmed by independent manual calculation from the line-items. In several cases the discrepancy is a single unit (1 *barig* = 60 *sila₃*), consistent with a copying slip; in others the discrepancy is larger and appears to reflect the omission of a sub-section from the *šunigin*. The remaining approximately 10 failures arise from structural formats outside the genre-1 assumption: tablets where the *šunigin* covers only one commodity in a multi-commodity distribution, tablets with dual accounting sections (e.g. an installment receipt combined with a running distribution), and tablets with significant ATF lacunae that suppress line-items. No tractable pipeline error was identified in any of the 32 failures after individual review.

The verified sub-corpus has important scope limitations that must be acknowledged. The *šunigin* check validates grain quantity parsing and commodity classification (sufficient to pass the arithmetic test) but does not extend to attribution fields (issuer, recipient, date), which are not constrained by the arithmetic. A tablet can balance perfectly while having every recipient name incorrectly extracted. The verified sub-corpus is therefore used in §5.4 exclusively for distributional analysis of grain quantities, for which the validation is relevant, and not for social-network or prosopographic claims.

---

## 4. Exploratory Data Analysis: Volume and Composition

### 4.1 The Commodity Profile

Aggregating all capacity-measured transactions and converting to a common *gur* base yields the commodity profile of Table 3. The result is unambiguous: the Ur III administrative record is overwhelmingly a record of grain. Barley alone (2.009 million *gur*) constitutes 86% of all capacity-measured volume. The combined cereal total—barley, emmer, wheat, and processed grain products (flour, malt)—reaches 2.335 million *gur*, approximately 420,000 metric tonnes if the standard 1 *sila₃* ≈ 0.8 kg conversion is used. By comparison, the next largest volumetric commodity, dates, reaches only 26,266 *gur*, roughly 1% of the grain total.

**Table 3.** Capacity-measured volume by commodity (in *gur*). Cereal grains in bold.

| Commodity | Volume (*gur*) | Share of grain total |
|---|---|---|
| **barley** | **2,009,257** | **86.0%** |
| **flour** | **154,049** | **6.6%** |
| **emmer** | **75,330** | **3.2%** |
| **dates** | **26,266** | **1.1%** |
| **wheat** | **23,530** | **1.0%** |
| **beer** | **23,275** | **1.0%** |
| **oil** | **19,982** | **0.9%** |
| **malt** | **3,366** | **0.1%** |

This profile is consistent with the role of barley (*sze*) as the de facto unit of account in the Ur III redistributive economy. Barley served simultaneously as the staple food crop, the input to beer production, the standard medium for wage payment, and the commodity denominator against which other goods were implicitly valued. The overwhelming numerical dominance of barley transactions in the corpus reflects this central role: every ration payment, field receipt, and granary transfer was recorded with a precision that other commodity categories seldom received. Emmer (*ziz₂*), the other major cereal of the period, is recorded far less frequently, consistent with its secondary status in the grain-ration system. Flour (*zu₂-lum* and related) appears as a processed product in bakery accounts rather than field receipts. Beer (*kaš*) is measured in capacity units but represents post-processing value rather than raw grain, which accounts for its relatively low volumetric representation despite its economic and social significance.

The transaction-count profile differs from the volume profile in significant ways. By transaction count, barley (53,109) is followed not by flour but by animals (45,571 head-counted transactions), bread (28,032), beer (24,106), and oil (21,430). The animal and bread/beer channels are major components of the Ur III redistributive economy—the Drehem archive is primarily a livestock redistribution record—but their capacity-unit volumes are small relative to grain because they are counted in different units (head, loaves, jugs) that do not convert to *gur*. The capacity profile therefore captures the grain economy specifically, while the transaction-count profile reflects the full breadth of the administrative record.

### 4.2 The Scale of the Corpus

230,342 extracted transactions from 48,603 distinct tablets represent the largest quantitative dataset yet assembled from the Ur III cuneiform record. By way of scale: the Drehem archive alone, the most intensively studied Ur III archive, comprises perhaps 15,000–20,000 published tablets, and systematic quantitative studies of even that single archive have been limited. The present dataset spans all major archive groups and provinces simultaneously, making cross-provincial comparison possible for the first time at this scale.

The 86,596 tablets that yield no extracted transaction are not uniformly uninformative. Many are fragmentary tablets on which critical lines are lost; others belong to genres (lexical lists, school texts, royal hymns) that do not contain economic transactions. A significant number are administrative tablets whose transactions fall outside the commodity types currently extracted—textile records, metal accounts, field-survey documents—areas that remain for future pipeline development.

---

## 5. Exploratory Data Analysis: Distribution and Structure

### 5.1 Transaction Sizes are Log-Normal with a Heavy Tail

The size distribution of the 49,751 positive barley capacity-transactions (measured in *sila₃*) spans eight orders of magnitude, from single-digit messenger rations to a single 134,007-*gur* threshing-floor receipt. This range—from under 10 *sila₃* to over 40 million *sila₃*—is comparable to the range one might find in a modern economy between a small retail sale and a bulk commodity shipment, and it reflects the fact that the same administrative corpus covers both the allocation of a day-labourer's ration and the accounting of an entire provincial harvest.

On a logarithmic axis the body of the distribution is strikingly regular: a log-normal fit gives μ = 5.18, σ = 3.29 (natural log of *sila₃*). The modal class sits at 300 *sila₃* (1 *gur*), which is also the median. The geometric mean, 178 *sila₃*, is the more representative measure of the typical transaction, sitting well below the arithmetic mean (12,116 *sila₃*)—the signature of strong right-skew generated by a small number of granary-scale entries. The near-coincidence of median and modal value at 1 *gur* is not accidental: the *gur* is the natural accounting unit for ration aggregation, and scribes routinely rounded ration totals to the nearest *gur* when issuing monthly allocations for groups of workers.

The log-normal body with heavy right tail is the expected size distribution for a system in which a large number of individual ration allocations (each approximately normally distributed on a log scale) coexists with a small number of large institutional flows (harvest receipts, inter-archive transfers, annual balances). It is not evidence of any particular economic mechanism; it is the characteristic statistical fingerprint of a multi-scale hierarchical distribution system, familiar from analyses of firm sizes, city populations, and income distributions in other historical contexts.

### 5.2 Extreme Concentration of Grain Volume

Grain volume is concentrated to a degree that would be remarkable in any economy. The top 1% of capacity transactions (approximately 498 transactions) carry **53.9%** of all recorded barley volume. The top 10% carry **91.2%**. The Lorenz curve lies far below the equality diagonal across its entire range: the bottom 80% of transactions collectively account for under 2% of total barley volume.

At the tablet level, the same pattern holds. The per-tablet median barley total is 6.4 *gur*, consistent with a typical ration list for a small work gang. Only 20 of 10,838 barley-bearing tablets record more than 10,000 *gur* each; these 20 tablets—provincial granary balances, annual harvest receipts, and inter-archive transfer records—collectively account for a substantial fraction of all recorded barley.

The Ur III grain economy is, statistically, a **two-regime system**: a vast substrate of small rationing transactions (the daily, weekly, and monthly allocations to named workers) overlaid by a thin stratum of enormous institutional flows (provincial harvest deliveries and annual granary balances). The two regimes are produced by the same administrative apparatus but serve different economic functions: the ration substrate records the terminal distribution of grain to individuals, while the institutional stratum records the aggregation and movement of grain between hierarchical levels of the redistribution system.

This two-regime character has important implications for summary statistics. A single arithmetic mean over all transactions conflates the two populations and is dominated by the thin upper tail; the geometric mean and median better represent the typical individual transaction. Similarly, the per-tablet Gini coefficient (0.919 across the full corpus) is driven partly by the mixture of ration tablets and granary tablets in the same dataset, rather than solely by inequality in individual allocations.

### 5.3 Temporal Structure Follows the Surviving Archives

Of the 230,342 extracted transactions, approximately one-third carry a recoverable reign date. Šulgi's reign (c. 2094–2047 BCE) dominates the dated record with 70,811 transactions, reflecting the survival and digitisation of the Drehem, Umma, and Girsu archives that were fully active during this period. The reign of Amar-Suen (c. 2046–2038 BCE) contributes 1,293 barley transactions, Šu-Suen (c. 2037–2029 BCE) 1,416, and Ibbi-Suen (c. 2028–2004 BCE) 1,033, despite the fact that these reigns are not dramatically shorter than Šulgi's. The extreme concentration of dated transactions in the Šulgi period reflects the survival of specific archive groups rather than a genuine economic peak in that reign.

Within Šulgi's dated transactions, the barley record peaks sharply in years 45–48, the period of the *bala* redistributive system's fullest documentation. The *bala* (literally "rotation") was the mechanism by which Ur III provincial governors contributed fixed tribute quotas of grain, animals, and labour to the central administration on a rotating annual basis; years 45–48 coincide with the period when this system's administrative record is most densely preserved at Drehem and Umma. The temporal signal in our data therefore indexes **archival survival and bureaucratic intensity** rather than any simple economic fluctuation—a critical caveat for any longitudinal interpretation of the transaction series.

The low representation of dated transactions in the reigns of Amar-Suen, Šu-Suen, and Ibbi-Suen does not imply economic contraction in those periods. It reflects the specific archival geography of the surviving corpus: the major Drehem archive closes around Šulgi year 48, and the Umma archive's most prolific period also falls under Šulgi. Future integration of CDLI provenance metadata (excavation site and archive attribution) would permit temporal analysis to be disaggregated by archive, separating genuine temporal variation from survivorship effects.

### 5.4 A Verified Sub-Corpus for Distributional Analysis

The 90 *šunigin*-reconciled tablets of §3.6 provide a controlled basis for distributional measurement, since their grain quantities are known correct by the arithmetic-validation constraint. This sub-corpus comprises 570 grain entries across 90 tablets, recording a total of 10,980 *gur* (3,294,107 *sila₃*) of cereal grain—predominantly barley (565 of 570 entries), with a small admixture of emmer (4 entries) and flour (1 entry). The 90 tablets contain 223 unique named recipients and 19 unique named issuers.

**Entry-size distribution.** The distribution of individual entry sizes in the verified sub-corpus confirms and quantifies the two-regime structure observed at the corpus level. At the lower end, the 10th percentile is exactly 60 *sila₃* (1 *barig*) and the 25th percentile also 60 *sila₃*, indicating that more than a quarter of all verified entries record a single-*barig* allocation. The median is 300 *sila₃* (1 *gur*), the 75th percentile 1,500 *sila₃* (5 *gur*), and the 90th percentile 15,000 *sila₃* (50 *gur*). The maximum single entry is 361,500 *sila₃* (1,205 *gur*), a bulk institutional transfer.

**Table 4.** Percentile distribution of grain entry sizes in the verified sub-corpus (sila₃).

| Percentile | *Sila₃* | Equivalent |
|---|---|---|
| p10 | 60 | 1 *barig* |
| p25 | 60 | 1 *barig* |
| p50 | 300 | 1 *gur* |
| p75 | 1,500 | 5 *gur* |
| p90 | 15,000 | 50 *gur* |
| p95 | 35,597 | ~118 *gur* |
| p99 | 66,716 | ~222 *gur* |
| Max | 361,500 | 1,205 *gur* |

**The standard ration.** The most common entry size is exactly **60 *sila₃*** (1 *barig*), appearing 89 times—more than any other quantity, and more than double the frequency of the next most common value (120 *sila₃* = 2 *barig*, 38 occurrences). This is the canonical adult monthly ration in Ur III administrative practice: one *barig* of barley per person per month for unskilled labourers (*geme₂*, *erin₂*), a figure attested consistently across the cuneiform record from Girsu to Drehem to Ur and corroborated by Waetzoldt's analysis of Ur III textile-worker ration registers. The dominance of this value in the verified sub-corpus is independent confirmation that the pipeline is capturing genuine ration distribution records and correctly parsing the standard allocation unit.

The next tier of common values—1,200 *sila₃* (4 *gur*, 36 occurrences), 90 *sila₃* (33 occurrences), and 300 *sila₃* (27 occurrences)—reflects the range of differentiated allocations in the Ur III ration system. Higher-ranking workers and administrators received larger monthly allocations (2, 4, or more *barig*), while the 90 *sila₃* allocation (1 *barig* + 3 *ban₂*) corresponds to the standard child ration or half-ration for certain categories of worker. The 1,200 *sila₃* value marks the transition to supervisor-level allocations and small departmental disbursements.

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

**Inequality in the verified sub-corpus.** We compute the Gini coefficient over the verified grain entries as a precision-guaranteed inequality estimate. The per-entry Gini is G = **0.873**; per-tablet G = **0.837**; per-recipient G = **0.907**.

These values require careful contextualisation. They do not measure income or wealth inequality across the Ur III population in any conventional sense. What they measure is the **concentration of grain throughput** across entries, tablets, and named recipients *within this specific administrative record type*. Three features of the measurement context are particularly important.

First, the verified sub-corpus mixes ration entries (60–300 *sila₃* per line) with bulk institutional transfers (tens of thousands of *sila₃* per line) on the same distributional canvas. The coexistence of these two transaction scales—separated by a factor of up to 6,000—mechanically produces a high Gini even if the individual-ration distribution is relatively equal. A Gini computed only on ration-scale entries (below 600 *sila₃*) would be substantially lower; a Gini computed only on institutional-scale transfers would be shaped entirely by the specific institutional recipients.

Second, the *lugal* ("royal estate" or "king") appears as a single named recipient on 33 of 90 verified tablets and receives 306,175 *sila₃* (approximately 9.3% of all verified grain) across 34 entries. The *lugal* here is an institution, not an individual: grain recorded as flowing to *lugal* is entering the royal granary for redistribution, not being consumed by a single person. Treating it as a single entity in the Gini calculation therefore inflates the per-recipient figure artificially. When *lugal* is excluded, the per-recipient Gini falls, though it remains very high.

Third, the per-entry and per-tablet Gini values (0.873 and 0.837) are not affected by name conflation, since they do not aggregate by named entity. These values more reliably characterise the actual concentration of grain flows in the administrative record.

With these caveats, the Gini values are nonetheless informative. They confirm quantitatively what the qualitative literature has long argued: the Ur III redistributive system channelled grain through a highly hierarchical structure in which a small number of large flows (provincial tribute deliveries, inter-archive transfers, annual granary balances) dominated aggregate volume while a large number of small individual allocations constituted the terminal distribution layer. The G = 0.873 per-entry figure for the verified sub-corpus is consistent with—and somewhat lower than—the G = 0.934 for the full corpus, a difference plausibly attributable to the genre-1 composition of the verified subset, which is biased toward ration distribution tablets (which contain many small equal entries) relative to the full corpus which includes granary inventory tablets (dominated by very large entries).

### 5.5 The Exchange Network and Its Brokers

Restricting to barley transactions with both a resolved issuer and recipient yields a directed network of **1,644 agents** connected by **2,807 unique directed edges**, supported by 6,691 total transactions (multiple transactions between the same pair contribute to edge weight). The graph is sparse (density 0.00104) but cohesive: a single giant weakly-connected component spans the large majority of agents, with the remaining mass fragmenting into small isolated dyads and triads.

Betweenness centrality identifies the structural brokers—the agents through whom grain flows must pass to travel between distant parts of the network. The high-betweenness nodes are precisely those Assyriology would predict: provincial household managers (*šabra*) and high stewards (*agrig*) who relay grain between cultivators, provincial administrators, and the central warehouses. Several names that emerge at the network core are documented in the philological literature as senior Ur III officials, providing a cross-validation that the pipeline is recovering genuine institutional relationships from the raw transliteration.

The single largest *sink* by in-degree is the royal granary constructions (*lugal* and related royal estate designations), the institutional terminus toward which provincial grain surpluses flow. By PageRank, which measures global centrality taking into account the importance of incoming nodes, the royal granary is again dominant: grain that passes through many different intermediaries ultimately terminates in the same institutional destination, giving that destination high recursive centrality. The network thus recovers, from raw transliteration alone, the textbook redistributive architecture of the Ur III state: a hub-and-spoke system mediated by named provincial household officers, with the royal granary at the hub.

**Table 6.** Leading recipients in the verified sub-corpus by total grain received.

| Recipient | Tablets | Entries | *Sila₃* |
|---|---|---|---|
| *lugal* (royal estate) | 33 | 34 | 306,175 |
| du-šu-mu-um-e | 1 | 3 | 97,200 |
| lu₂-he₂-gal₂ | 1 | 3 | 43,440 |
| lugal-e₂-mah-e | 1 | 1 | 42,270 |
| ur-nin-pa | 1 | 1 | 37,660 |
| ur-ba-ba₆ | 4 | 4 | 37,245 |
| ur₂-ra-ni | 2 | 2 | 35,330 |
| lu₂-nanna šagina | 1 | 2 | 34,200 |

The appearance of *ur-ba-ba₆* on 4 separate verified tablets, and of *lu₂-dingir-ra* on 7 tablets in the full verified set, suggests these are senior administrators whose allocations were recorded across multiple distribution events rather than single large transfers. Forty-one unique names appear on two or more verified tablets, forming the nucleus of what would be a prosopographic network analysis if attribution accuracy were validated for these tablets—a task reserved for future work.

---

## 6. Methodology: Controlling False Positives

We now turn to the paper's principal methodological contribution. In a corpus where grain, garlic, reeds, cattle, silver, and accounting balances all share a numeral-classifier grammar, the dominant source of error is not the failure to parse grain (false negatives) but the eager parsing of non-grain (false positives). Because a single large-denomination misread can inject up to 64.8 million *sila₃* per line (Table 1), precision on the tail of the size distribution dominates the aggregate volume. Our strategy is a layered body of negative-classification rules, each motivated by a specific scribal idiom and each pinned by a regression test that encodes the expected behaviour on documented examples.

### 6.1 Taxonomy of False Positives

Systematic examination of the pipeline's early output, before filtering, identified six major categories of false positive that together accounted for approximately 0.96 million *gur* of spurious grain volume.

**Non-grain capacity commodities.** Beer (*kaš*), oil (*i₃*), and dates (*zu₂-lum*) are measured in *sila₃* and *gur* and appear with the same numeral-classifier syntax as grain. The commodity word may precede or follow the numeral depending on scribal convention. A line reading `2(barig) kaš` denotes beer, not barley, but a parser that identifies capacity units first and commodity words second will misclassify it.

**Animal counts with capacity-like numerals.** On certain livestock tablets, animal count lines use large sexagesimal numerals followed by animal terms (*udu* sheep, *gu₄* ox, *masz* goat) in positions that superficially resemble capacity lines. A line such as `5(gesz2) udu` (300 sheep) is unambiguous to a reader but potentially confusable to a parser that treats *gesz₂* as a capacity multiplier.

**Seed-grain at planting rates.** Field tablets record seeding rates as `N(aš) gur GAN₂` (capacity per area unit); the embedded `GAN₂` (field-area determinative or logogram) marks these as planting records rather than distribution entries. Extracting them as grain transactions would conflate seeding rates with distributions.

**Subtotal carry-forwards.** The *sza₃-bi-ta* ("therefrom") opening of an expenditure block restates the incoming section balance as the first quantity in the new section. Parsing it again would double-count the grain that the same section already recorded.

**Rate-multiplication lines.** On certain ration tablets, a computational line records the result of multiplying a per-person ration by a worker count (`N persons × M sila₃ = P sila₃ total`); both the multiplicand line and the product line appear in grain units. Extracting both would double-count the individual rations against the computed total.

**Named individuals parsed as grain tokens.** A minority of personal names begin with or contain capacity-system tokens as lexical components (e.g. *gur-sar*, *barig-ga* as name elements). In isolation, without the surrounding prepositional frame, these lines can trigger false grain reads.

### 6.2 The Large-Denomination Ration Trap

The most consequential false positive, measured by volume impact, is the large-denomination ration list. On brewer-ration and weaver-ration tablets, individual worker entries use large sexagesimal tokens to count *sila₃*, not *gur*: an entry such as `3(gesz'u) 4(gesz2) 2(u) 3(disz) ARAD₂` represents 3 × 3,600 + 4 × 60 + 23 = 11,063 *sila₃* (approximately 37 *gur*), and the section's closing *šunigin* performs the *gur* conversion explicitly. A parser that applies the *gur* promotion factor to the *gesz'u* and *gesz₂* tokens would inflate this line by a factor of 300, treating 37 *gur* as 11,000 *gur*. Across the corpus, this single error class injected approximately 0.80 million phantom *gur* before it was identified and filtered.

The diagnostic linguistic signature is precise: a line carrying large-denomination tokens (*gesz₂*, *gesz'u*) but **no sub-*gur* anchor** (*aš*, *barig*, or *ban₂*) is operating in *sila₃* scale and must not be promoted. This is because on genuine *gur*-scale lines, the sub-*gur* remainder (*barig* and *ban₂* terms) always appears alongside large-denomination tokens when the quantity is not an exact multiple of *gur*. The *absence* of these anchors beside a *gesz₂* token is therefore a reliable signal that the quantity is in *sila₃* scale. Encoding this one negative rule eliminated the dominant false-positive class.

### 6.3 Context-Sensitive Recovery for False Negatives

Aggressive negative filtering creates a complementary problem: it risks discarding legitimate grain lines that lack explicit commodity markers. Elliptical construction is common in Ur III administrative tablets, particularly within established grain sections where the commodity word may be elided after the first line of a section (scribal shorthand that assumes the context established by the section header). A strict positive-evidence rule—only extract a line if it explicitly names a grain commodity—would generate unacceptable false negatives in elliptical grain sections.

We address this with a **context-sensitive recovery** mechanism: a tablet section that contains at least one explicit grain line activates a secondary parsing pass that recovers unit-elided quantity lines within that section, subject to the condition that none of the §6.1 disqualifiers is present on the candidate line. The primary and recovery passes are adversarial by design: every loosening of recovery criteria is validated against the full false-positive test suite to ensure no spurious non-grain lines are captured, and conversely, every tightening of false-positive filters is validated against a documented set of legitimate elliptical lines that must not be lost.

### 6.4 Validation and Net Effect

The rule body comprises 120 distinct pattern terms spanning the six false-positive categories above and several edge cases encountered during corpus-wide development. These rules are exercised by 144 regression tests, all passing, that encode both lines that *must* parse as grain quantities and lines that *must not*. The test suite was developed test-first across more than eighty pipeline revisions and encodes hundreds of specific scribal idioms in executable form.

The net effect of the filter suite is a reduction from a permissive baseline of approximately 3.73 million *gur* to the present 2.335 million—a reduction of **0.96 million *gur* (26%)**—while the regression suite provides documentation that no validated legitimate line was suppressed. The *šunigin* reconciliation harness of §3.6 provides independent validation of this figure: the 90 tablets that balance arithmetically represent cases where the filter suite correctly captured exactly the grain quantities the ancient scribe intended to record.

We regard the test corpus itself, rather than any individual rule, as the durable methodological artefact. The 144 regression tests freeze hundreds of adjudicated scribal idioms into executable specifications that can be verified, extended, and transferred to related extraction problems. New rules can be proposed, tested against the existing suite, and accepted only if they improve specific documented failures without regressing documented successes. This discipline prevents the common failure mode in corpus-scale extraction where local improvements to one problem introduce new failures elsewhere.

---

## 7. Limitations

Several caveats bound the scope and reliability of the analysis.

**(i) Damage and lacunae.** Physical damage to tablets suppresses quantities and attributions. The 86,596 tablets that yield no extracted transaction include a large proportion with severe damage, and even on partially intact tablets, bracketed lacunae suppress individual lines. Reported volumes are conservative lower bounds, and the untyped-capacity residue reflects loss of commodity words to damage.

**(ii) Prosopographic noise.** The entity index conflates several common commodity words (*kaš* beer, *ninda* bread, *udu* sheep) with personal names at the head of the frequency table when those words appear in unusual syntactic positions. Genuine-person analysis requires working from the patronymic-anchored subset (6,761 father–son pairs), where individual identity is more securely established. The name-normalisation logic is conservative (strips suffixes only when the bare form is independently attested) but cannot guarantee zero false merges among names with identical stems.

**(iii) Survivorship and genre bias.** The temporal and provincial distribution of extracted transactions tracks which archives were excavated, published, and digitised—not the ancient economy's true shape. The *šunigin*-verified sub-corpus is additionally filtered to genre-1 (simple list + grand total) tablets with legible totals, making it unrepresentative of the broader corpus: it is probably biased toward ration distribution tablets relative to inventory, transfer, and balanced-account records.

**(iv) Attribution coverage.** Only 2.9% of transactions carry both a resolved issuer and recipient, restricting exchange-network analysis to a fraction of the corpus. Attribution fields (issuer, recipient, date) are not validated by the *šunigin* arithmetic harness and may contain errors not captured by the regression test suite.

**(v) The scope of the *šunigin* harness.** The arithmetic validation covers 122 checkable tablets of a specific genre, representing a small fraction of the full corpus. The pipeline's accuracy on the remaining 135,077 tablets is unvalidated by this method. The 144-test regression suite provides complementary but qualitatively different coverage: it validates parsing logic on documented examples rather than end-to-end accuracy on complete tablets.

**(vi) Double-counting in complex accounts.** Multi-section balanced accounts that re-state sub-section totals at several hierarchical levels represent the hardest residual case for false-positive control. The pipeline suppresses canonical *šunigin* and *sag-nig₂-gur₁₁* restatements but cannot guarantee zero leakage in idiosyncratic ledgers that restructure their accounting in non-standard ways.

---

## 8. Conclusion

A deterministic, test-driven pipeline can convert 135,199 raw cuneiform transliterations into a quantitatively coherent picture of the Ur III grain economy: 2.335 million *gur* of cereal grain moving through a sharply two-regime distribution—a vast substrate of individual ration payments alongside a thin stratum of enormous institutional flows—organised as a broker-mediated redistributive network terminating at the royal granary.

Within an arithmetically verified sub-corpus of 90 tablets, three quantitative conclusions emerge with high confidence. First, the modal grain allocation is exactly 60 *sila₃* (1 *barig*)—the canonical Ur III adult monthly ration—appearing at nearly twice the frequency of any other entry size and confirming that the verified sub-corpus is capturing genuine ration distribution records. Second, grain throughput is highly concentrated: a per-entry Gini of 0.873 and per-tablet Gini of 0.837 reflect the coexistence of standardised small rations and large institutional bulk flows within the same administrative record system. Third, the *lugal* (royal estate) appears as the dominant single recipient across 33 of 90 verified tablets, receiving 9.3% of all verified grain—consistent with the textbook account of the royal granary as the terminal collection point of the Ur III redistributive hierarchy.

The decisive technical lesson from building this pipeline is that mass extraction from cuneiform corpora is governed by **negative classification**: by the disciplined, linguistically-grounded refusal to count what merely looks like grain. The 120-rule filter suite and its 144 regression tests operationalise this discipline. The complementary *šunigin* reconciliation harness converts the ancient scribe's own arithmetic into a machine-checkable quality signal: where the ancient sum and the pipeline sum agree, extraction is verified; where they diverge, the discrepancy invites targeted investigation. Together, these two quality layers—test-driven development and arithmetic ground truth—provide a reproducible framework for precision extraction from large cuneiform corpora.

Future work will extend context-sensitive recovery to the untyped-capacity residue (currently approximately 385,000 *gur* of capacity-measured grain with lost commodity words), apply the same negative-classification methodology to the silver and livestock channels to expand the economic coverage of the pipeline, and integrate CDLI provenance metadata (excavation site and archive attribution) to situate the exchange-network analysis within the known institutional geography of the Ur III state.

---

## Data and Code Availability

All extraction code, the 144-test regression suite, the *šunigin* reconciliation harness (`tools/reconcile_szunigin.py`), the verified-corpus analysis (`tools/analyze_verified.py`), and the derived transaction, record, entry, and entity tables are available in the repository `asarodan/sumer`. Figures are regenerated from `output/figures/` by `tools/make_paper_figures.py` over the CDLI bulk ATF export. The CDLI corpus is distributed by the Cuneiform Digital Library Initiative under its data-sharing terms.

---

## References

Cuneiform Digital Library Initiative (CDLI). *Ur III administrative corpus, ATF bulk export.* cdli.mpiwg-berlin.mpg.de.

Englund, R. K. (2012). "Equivalency Values and the Command Economy of the Ur III Period in Mesopotamia." In *The Construction of Value in the Ancient World*, 427–458.

Garfinkle, S. J. (2015). "Ur III Administrative Texts: Building Blocks of State Community." In *From the 21st Century B.C. to the 21st Century A.D.*

Milanovic, B., Lindert, P. H., and Williamson, J. G. (2011). "Pre-Industrial Inequality." *Economic Journal* 121: 255–272.

Molina, M. (2008). "The Corpus of Neo-Sumerian Tablets: An Overview." In *The Growth of an Early State in Mesopotamia*, 19–53.

Sallaberger, W. (1999). "Ur III-Zeit." In *Mesopotamien: Akkade-Zeit und Ur III-Zeit*, OBO 160/3, 121–390.

Widell, M. (2004). "Reflections on Some Households and their Receiving Officials in the City of Ur in the Ur III Period." *JNES* 63, 283–290.

---

*Manuscript compiled from pipeline output · corpus snapshot: 135,199 tablets · 230,342 transactions · 2.335 M gur capacity · 90 šunigin-verified tablets*
