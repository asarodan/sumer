# Sumer Parser — System Design Sheet

**Status:** Living design document
**Scope:** The complete logical design of the Ur III ATF parser — what it must do, what it must never do, and how its architecture follows from the nature of the data.
**Audience:** Maintainers, computational historians, and anyone who needs to trust (or challenge) a number this pipeline produces.

---

## 0. How to read this document

This is not a feature list. It is a *derivation*. It starts from the nature of
the source material (§2), states the epistemic stance that material forces on us
(§3), and then shows that the architecture (§6), the verification mechanisms
(§7), and the output contracts (§9) are **consequences** of that stance, not
arbitrary choices.

Wherever a rule is binding it is labelled as an **Invariant** (`I1`, `I2`, …).
Invariants are the non-negotiable contract of the system; everything else is
implementation that may change as long as the invariants hold.

---

## 1. Purpose

Transform the CDLI bulk ATF export of Ur III (~2112–2004 BCE) administrative
tablets into **structured economic data whose every datum carries a known and
queryable degree of certainty**, such that:

1. A high-confidence subset can be used for quantitative history with defensible
   error bounds.
2. A lower-confidence periphery remains available, clearly marked, for
   exploratory and qualitative work.
3. No analysis can *accidentally* mix the two.

The product is **not** the transactions. The product is **the transactions plus
their warrant.** A transaction without its warrant is a liability.

---

## 2. The substrate — what the data actually is

We are parsing a **scholarly transcription of an administrative bureaucracy's
internal records**, not natural-language prose. Three facts about the substrate
drive every design decision.

### 2.1 It is formulaic, not free text
Ur III administrative tablets are written in a near-fixed grammar of
closed-class function words. The structure of a transaction is anchored to
morphology that does not vary:

| Marker | ATF | Function | Reliability |
|--------|-----|----------|-------------|
| ablative source | `ki NAME -ta` | issuer (goods *from*) | high |
| receipt | `szu ba-ti` / `szu ba-an-ti` | recipient received | high |
| expenditure | `ba-zi` | goods drawn out / debited | high |
| conveyor | `giri3 NAME` | transport/responsible agent | high |
| seal authority | `kiszib3 NAME` | sealed (authorised) by | high |
| filiation | `NAME dumu FATHER` | son of | high (but see §2.3) |
| total | `szunigin …` | scribe's own grand total | **decisive — see §7.1** |

This formality is *why* the corpus is machine-parseable at all. It is the
foundation of every high-confidence claim.

### 2.2 It carries a closed date vocabulary
Ur III years are named after royal events (`mu … ba-hul` = "year X was
destroyed"). The set of year-names per king is **finite and reconstructed by
modern Assyriology** — a controlled vocabulary. `chronology.py` already encodes
a fragment of it (`KING_YEAR_MAP`), currently 3–9 years per king out of a full
reign (Šulgi alone ruled ~48 years). Completing this vocabulary is a force
multiplier (§7.2): it turns date lines from fuzzy strings into validated,
orderable positions in time.

### 2.3 It carries its own checksums
A large fraction of tablets state a `szunigin` (grand total) that should equal
the sum of their line items. The scribe did our QA for us, 4,000 years ago.
This is the single most powerful and most under-used signal in the corpus.
Current code *skips* `szunigin` to avoid double-counting; the target design
*reconciles* against it (§7.1).

### 2.4 The hard truths
- **It is an archive, not a census.** The tablets are the surviving output of
  particular institutions (Drehem's livestock centre, the Umma and Girsu
  provincial bureaus). They describe *institutional flows*, never a population.
- **Damage is irreducible.** `[...]`, `x`, `n`, `#`, `?` mark places the *clay*
  failed. No inference recovers a broken sign.
- **Cross-tablet identity is inference.** Two strings `ur-lamma` are the same
  person only by argument, never by observation. The corpus proves this is hard:
  675 names already carry ≥2 distinct fathers; `lugal` (5,027 attestations)
  fuses a title with a personal name.

---

## 3. Epistemic stance (the axioms)

Everything below follows from four axioms.

- **A1 — Faithfulness.** The parser represents the transcription; it never
  silently alters it. Damage and uncertainty are data to be carried, not noise
  to be cleaned away.
- **A2 — No invention.** When the source is ambiguous or broken, the parser
  records *ambiguity*, never a guess dressed as a fact.
- **A3 — Stratified certainty.** Not all extracted facts are equal. Each datum
  belongs to a certainty tier (§4), and that tier is part of the datum.
- **A4 — Non-contamination.** A lower-certainty inference may never overwrite,
  or be silently merged into, a higher-certainty fact.

From these:

> **I1.** Every emitted datum carries (a) its raw source span, (b) the rule that
> produced it, and (c) a certainty tier. A datum lacking any of the three is a
> defect.

> **I2.** Normalisation, linkage, and aggregation are **views** over the facts,
> never destructive edits of them. Any derived form must link back to the raw
> form and be recomputable from it.

---

## 4. The certainty model (the logical core)

This is the spine of the system. Every other section refers back to it.

| Tier | Name | Definition | Example | Trust |
|------|------|------------|---------|-------|
| **T0** | Transcription | The ATF as published by CDLI, including damage marks | `4(asz) sze gur` | inherited from CDLI |
| **T1** | Lexically anchored | Resolved against a closed vocabulary with an intact anchor | `4(asz) gur` → 1,200 sila3; `szu ba-ti` → receipt | near-certain |
| **T2** | Intra-tablet structure | A role/relation read from an intact formula *within one tablet* | "issuer = ur-lamma" from `ki ur-lamma-ta` | high |
| **T3** | Cross-tablet identity | Two attestations judged to be the same individual | "this is the Ur-lamma son of X" | probabilistic |
| **T4** | Aggregate / derived | Statistics computed over T1–T3 | a Gini coefficient, a centrality score | inherits the weakest input |

Logical rules over the tiers:

> **I3.** A T4 result inherits the *minimum* tier of every input that feeds it,
> and must publish the coverage fraction of inputs at each tier.

> **I4.** T3 (identity) lives in a **separate store** from T1/T2 facts. The
> transaction record references a *raw name string + tablet*; identity is an
> overlay keyed to those references and is swappable without re-parsing.

> **I5.** The arithmetic check (§7.1) can *promote* a record's structural
> confidence within T2 from "asserted" to "self-verified", but can never lift a
> datum across a tier boundary.

The strategic consequence: **be maximally ambitious in what you extract (push
into T3/T4), and maximally conservative in what you certify (keep T1/T2 pure).**
The two postures coexist only because the tiers keep them physically apart.

---

## 5. Domain ontology (the vocabulary the parser resolves into)

The parser's job in T1 is to map raw tokens onto these controlled vocabularies.
Each is a closed (or closeable) set; tokens that fail to resolve are **flagged,
not guessed** (A2).

### 5.1 Quantities — the metrological system
Resolved to **sila3** (≈0.84 L) as the single base unit (no rounding drift on
aggregation). Capacity tiers: `sila3`(1) · `ban2`(10) · `barig`(60) ·
`gur`(300) · `gesz2`(18 000) · `gesz'u`(180 000) · `szar2`(1 080 000) ·
`szar'u`(10 800 000) · `szargal`(64 800 000). Sexagesimal positional notation
within each tier; `la2` denotes subtraction. Discrete goods counted in **head**;
weights/areas in their own units (`gin2`, etc.).

> **I6.** A quantity containing any damage mark in its numeric span is tagged
> `damaged` and is **excluded from sums** (it may still be reported as a lower
> bound). It is never coerced to a number.

### 5.2 Commodities
Closed class with determinative cues (`{gesz}`, `{uruda}`, `{u2}`, …):
animal, barley, bread, beer, oil, flour, dates, emmer, wheat, malt, silver,
gold, copper, labor, plus an explicit `unresolved` bucket. Quality grades
(`niga` = fattened, `saga` = fine) are *attributes*, never entities.

### 5.3 Roles (transaction grammar)
`issuer` (ablative source) · `recipient` (receipt/dative) · `agent`
(giri3/ugula conveyor) · `seal_authority` (kiszib3). Each is bound to a fixed
marker (§2.1).

### 5.4 Dates
`(king, year_number, year_name, month, day)` per `UrIIIDate`. The `(king,
year)` pair is validated against the year-name controlled vocabulary (§7.2).

### 5.5 Entities and filiation
A raw name string; optional father (`dumu`) edge; optional title/profession from
a closed lexicon; optional provenance. Note: status descriptors after `dumu`
(`dumu lugal` = prince, `dumu dab5-ba` = conscripted dependent) are **not**
fathers — `_PATRONYM_STOP` enumerates them.

### 5.6 Provenance
Find-site / archive where known (Umma, Girsu/Lagash, Nippur, Drehem/Puzriš-Dagan,
Ur). A T3 disambiguator, not a T2 fact unless stated on-tablet.

---

## 6. Architecture — six layers

Each layer has a single responsibility, declared inputs/outputs, and invariants.
Data flows down; certainty tiers are assigned as early as the evidence allows and
never silently upgraded.

```
 ATF text
   │
   ▼
 L1  Lossless tokenisation        ──►  token stream (T0, damage-preserving)
   │
   ▼
 L2  Lexical resolution           ──►  typed values (T1) + unresolved flags
   │
   ▼
 L3  Intra-tablet structure        ──►  Tablet→Record→Entry tree (T2)
   │    + arithmetic self-check          + balanced/unbalanced/no-total tag
   ▼
 L4  Reversible normalisation      ──►  canonical view (links back to raw)
   │
   ▼
 L5  Prosopographic linkage        ──►  identity clusters (T3, separate store)
   │
   ▼
 L6  Analytics + provenance        ──►  scoped aggregates (T4, with coverage)
```

### L1 — Faithful tokenisation
**In:** raw ATF lines. **Out:** a stream of typed **grapheme tokens** conforming
to a fixed schema pinned to a stated version of the CDLI ATF specification. Each
token is `{sign, determinative?, damage_state, modifiers, position}` where
`damage_state ∈ {intact, damaged(#), uncertain(?), missing([…]), collated(!)}`,
`modifiers` capture sign-form (`@…`) and variant (`x(|…|)`) notation, and
`position` is `(surface, column, line)`.
*(today: `loaders.py` + `text.py` stripping discards several of these marks;
target is preserve-then-annotate against the schema.)*

"Lossless" is defined **narrowly so it is testable** — not byte-exact
reconstruction, but **semantic round-trip over a closed, enumerated set of ATF
markup classes**: graphemes, determinatives, damage/uncertainty marks, sign-form
and variant modifiers, and surface/column/line position. Whitespace, editorial
comments, and layout *may* be normalised away **if catalogued** in the token's
provenance. A markup construct outside the enumerated set is a **schema gap** —
logged and surfaced, never silently dropped.
> **I7.** L1 guarantees *semantic* round-trip: re-serialising the token stream
> reproduces every token in the enumerated ATF markup classes with identical
> semantics. The enumerated class set and the pinned ATF-spec version are part of
> the contract; adding a class is a versioned schema change, not an ad-hoc fix.

### L2 — Lexical resolution
**In:** tokens. **Out:** typed values against §5 vocabularies, each tagged T1 or
`unresolved`. *(today: `extract_quantity.py`, `extract_dates.py`,
commodity/role regexes in `patterns.py`.)*
> **I8.** A token that does not resolve against its controlled vocabulary is
> emitted as `unresolved`, never as a nearest-guess.

### L3 — Intra-tablet structure + self-check
**In:** resolved tokens for one tablet. **Out:** the `TabletSummary` tree
(`models.py`) with roles assigned by formula, **plus a reconciliation tag** per
record. *(today: `extract_structure.py` builds the tree but **skips** szunigin;
target adds §7.1 reconciliation.)*
> **I9.** Every record is tagged `balanced` | `unbalanced` | `no-total`. This tag
> is a required output column.

### L4 — Reversible normalisation
**In:** raw names/spellings. **Out:** canonical forms with a back-link and the
firing rule. *(today: `normalize.py`, the `entities.EntityScanner._add` filter
chain, sign-variant handling.)*
> **I10.** Every normalisation (merge, strip, block) is logged as
> `(raw, canonical, rule_id)` and is reversible. The two-pass design
> (collect-then-normalise) stays: a bare form is merged only if independently
> attested.

### L5 — Prosopographic linkage
**In:** raw name references + patronymics + titles + provenance + date-windows.
**Out:** scored identity clusters in a **separate store** keyed to raw
references. *(today: partial — `entities.csv` + `patronymics.csv` provide the
evidence; clustering/scoring is not yet a distinct layer.)*
> **I11.** L5 never writes into L1–L4 outputs. The `lugal` title/name ambiguity
> is represented as an ambiguity with alternatives, not forced to one reading.

### L6 — Analytics + provenance
**In:** T1/T2 facts and (optionally) T3 clusters. **Out:** aggregates that ship
with their filter, coverage fraction, and confidence band. *(today:
`network.py`, the EDA/paper HTML; coverage/provenance fields are the gap.)*
> **I12.** No aggregate is emitted as a bare number. Each carries an explicit
> **frame** and a **coverage vector** (§9.0), plus a confidence band.

> **I15 (graceful degradation — no perfection traps).** The pipeline emits valid
> T0–T2 output with an *empty* chronology vocabulary and an *empty* identity
> store. Any subsystem whose value is monotonic in its own completeness —
> chronology (§7.2) and identity (§7.3) — is an **enrichment overlay**, never a
> blocking dependency. Partial completeness yields partial T3/T4 value; it never
> gates T1/T2. This forbids "boil-the-ocean" dependencies *by construction*.

---

## 7. Verification mechanisms (what makes "rock solid" real)

### 7.1 Arithmetic self-check — the corpus's own checksums
For every record with a `szunigin` total, sum the parsed line items and compare.

- **match** → tag `balanced`. The record is *self-verified*: the ancient
  accountant and our parser independently agree. This is the **gold set**.
- **mismatch** → tag `unbalanced`. Either we mis-parsed or the clay is damaged;
  quarantine from quantitative use and surface for inspection.
- **no total** → tag `no-total`. Usable but uncheckable; lower structural trust.

The gold set is dual-purpose: it is both the **high-trust analytical subset**
and a **ground-truth regression corpus** against which every future parser change
is scored. For the first time, "how accurate is the parser?" has a numeric
answer: the balance rate, and the delta in balance rate per change.

> **Design flip:** stop discarding `szunigin`; parse it as the stated total and
> reconcile. This converts the most-skipped line type into a verifiable signal.

**Measured (first pass — `tools/reconcile_szunigin.py`, grain totals only; full
findings in `RECONCILIATION_FINDINGS.md`).** The check works, but the gold set is
**narrower than this section originally implied** — it is a *precision
instrument, not a universal backbone*:

- Of 585 single, direct grain-total Ur III tablets, **351 (60%) are excluded by
  damage** before arithmetic is possible (I6); 214 are checkable.
- Of the checkable, **43% balance** (≈92 self-verified "gold" tablets). The
  remaining 57% are dominated by *small* differences — the signature of one
  missed line-item, i.e. a prioritised parser-bug queue, not structural noise.
- **Genre is the hidden variable.** "Sum of grain lines = total" holds only for
  *genre 1* (simple list + grand total). Barley-equivalent ledgers (`sze-bi`
  totals), field-area accounts (`sza3-bi-ta` × rate), header-totals, and
  multi-section accounts each need their own reconciliation equation.

> **Revised claim:** the arithmetic check yields a high-purity gold *subset* and
> a regression seed *per genre*, and doubles as a parser-error detector. It does
> not — and was wrong to claim it would — underwrite trust across the whole
> corpus. **Genre classification is therefore a prerequisite** for reconciliation,
> not an afterthought (roadmap step 2a).

### 7.2 Year-name oracle — *probabilistic and partial by design*
Complete `chronology.py` toward full reigns, but the resolver is **scoring, not
binary**, and is correct *while the vocabulary is still incomplete*. This is the
explicit defence against the brittleness of all-or-nothing validation.

For a date line, compute a match score against each candidate `(king, year)` from
fragment overlap, weighted by fragment specificity (`us2-sa` "year-after"
disambiguators weigh heavily). Emit a **posterior over years**, not a verdict:

- **resolved** — one candidate dominates (score gap above threshold) → assign with
  confidence equal to the normalised margin;
- **ambiguous** — several candidates competitive → keep the weighted set; do not
  pick one;
- **unresolved** — best score below floor → leave open.

The distinction that makes partial vocabulary safe:

- **absent** (nothing matches) ⇒ "year not yet in the vocabulary **or** damaged"
  — *never* treated as invalid. Degrades gracefully (see I15).
- **contradicted** (fragments match a *different* king's year, or two mutually
  exclusive years) ⇒ a genuine anomaly, surfaced for inspection.

So completeness raises the **resolution rate** but is never a precondition for
**correctness**. Quality metrics: resolution rate, ambiguity rate, and
contradiction rate over all date lines.

### 7.3 Prosopographic triangulation — *weight-of-evidence, default-split*
T3 is an explicit scoring + constrained-clustering model, not a hand-wave. Its
default is **non-merge**: two attestations of the same raw string are *different
people* until positive evidence beyond the name says otherwise. This inverts the
usual normalisation bias and is the safe direction — under-merging only loses
links, whereas over-merging *fabricates a person who never existed*.

**Pairwise evidence score.** For two attestations of a (fuzzy-)matching name,
accumulate weight-of-evidence (log-odds) contributions:

| Evidence | Effect |
|----------|--------|
| same attested father (`dumu`) | strong + |
| **conflicting** attested fathers | **cannot-link** (hard constraint) |
| date-windows incompatible (> plausible career span, ~40 yr) | hard negative |
| shared title / profession | weak + |
| shared provenance / archive | weak + |
| shared role / commodity milieu | very weak + |

**Constrained clustering.** Build a graph whose edges are positive pairwise
scores, subject to **cannot-link constraints** (conflicting fathers, incompatible
dates) that may never be merged across. Cluster by constrained
connected-components / correlation clustering above a score threshold. Outputs:

- **clusters** — confidence = internal evidence density;
- **ambiguous pools** — same-name attestations with *no* disambiguating evidence
  stay an explicit unresolved pool, neither merged nor split by fiat;
- **forced splits** — a name with conflicting fathers becomes ≥2 clusters by
  construction. This is exactly how `lugal`'s title/name fusion is represented:
  as several evidenced clusters *plus* a large ambiguous pool, never one node.

Tracked health metrics: homonym count (currently 675 names with ≥2 fathers),
merge rate, and **ambiguous-pool size** — the honest measure of the identity we
*cannot* resolve, which the system reports rather than hides.

### 7.4 Round-trip / reversibility tests
Assert I7 and I10: reconstruct raw from tokenised, and raw-name from canonical +
log. A failure means information was destroyed — a defect, regardless of whether
the output "looks right".

---

## 8. What this unlocks (scoped honestly)

Built on the tiered, self-checked core, defensible second-order knowledge becomes
reachable — each stated at the scope the data supports, never broader:

- **Commodity-flow time-series at a single centre across regnal years** (e.g.
  barley disbursements at Drehem, Šulgi 44–48), enabling detection of
  administrative reforms, supply shocks, and the Ibbi-Suen contraction.
- **The bala redistribution cycle** quantified province by province.
- **Prosopographic networks** — who disbursed to whom, career arcs, household
  structure via filiation — as *scored* graphs.
- **Scribal-convention drift** as its own historical signal.

> **I13.** Every published claim names its scope (centre, period, commodity) and
> its coverage. "Gini of barley disbursements at Drehem, Šulgi 44–48, over
> balanced records covering N% of attested volume" — never "the Gini of Ur III".

---

## 9. Output contract

### 9.0 Coverage, with an explicit denominator
A coverage number is meaningless without naming what it is *over*, so coverage is
reported as a **vector against a declared frame**, never a lone percentage.

- **Frame** — the scope predicate defining a claim's universe
  (e.g. `commodity=barley ∧ centre=Drehem ∧ period=Šulgi 44–48`). **The frame is
  the denominator's definition.** No frame, no coverage.
- **record_coverage** = `balanced_records / records_in_frame`.
- **volume_coverage** = `Σqty(balanced) / Σqty(parseable records in frame)`, where
  the denominator spans balanced + no-total + unbalanced-with-parseable-qty and
  **excludes** damage-unparseable quantities (which cannot be summed — I6).
- **dark_fraction** — the part that *cannot* enter a ratio: a count of
  damage-unparseable records in frame, plus a Σ **lower bound** of their legible
  quantities. Reported as a separate pair, never folded into the percentages.

A claim therefore reads: *"X over frame F; record_coverage 0.71, volume_coverage
0.83, dark 240 records (≥1.1 M sila3 legible)."* The reader sees precisely what
the number rests on and what it omits — the dark fraction is shown, not buried.

### 9.1 Per-artifact requirements

| Artifact | Tier | Must carry |
|----------|------|-----------|
| `entries.csv` (line items) | T1/T2 | raw span, quantity+`damaged` flag, commodity or `unresolved`, record reconciliation tag |
| `records.csv` | T2 | role assignments, `balanced/unbalanced/no-total`, date + validation flag |
| `transactions_*.csv` | T2 | issuer/recipient/agent as **raw refs**, never a forced identity |
| `entities.csv` | T2→T3 | attestation count, roles, evidence; clusters scored, not fused |
| `patronymics.csv` | T2 | name→father edges with `_PATRONYM_STOP` applied; homonym flag |
| network / GEXF | T4 | node = raw ref or scored cluster (declared), edge weight + coverage |
| any aggregate | T4 | `{frame, coverage vector (§9.0), confidence_band}` (I12) |

> **I14.** A consumer can filter any artifact to "balanced + dated + resolved"
> and obtain the rock-solid subset with a single predicate.

---

## 10. Current state vs. target (grounded gap analysis)

| Capability | Today | Target | Gap |
|------------|-------|--------|-----|
| Quantity → sila3 | strong (`extract_quantity.py`) | + `damaged` exclusion flag (I6) | small |
| Role grammar | strong (`patterns.py`) | unchanged | — |
| Record tree | built (`extract_structure.py`) | + reconciliation tag (I9) | **arithmetic check (7.1)** |
| szunigin totals | **skipped** | **reconciled** | the key flip |
| Year vocabulary | partial (`chronology.py`, 3–9 yrs/king) | full reigns + validation (7.2) | **complete the oracle** |
| Normalisation | strong, ad-hoc (`entities.py` filters) | rule-logged, reversible (I10) | provenance logging |
| Identity (T3) | evidence only (csv) | separate scored cluster store (I4/I11) | **layer L5** |
| Confidence on outputs | implicit | explicit per-datum (I1) | **confidence schema** |
| Coverage on aggregates | absent | required (I12) | L6 provenance |
| Trailing-recipient lists | unattributed (~60% party-less rows) | explicit pattern w/ confidence penalty | structural parse (L3) |

---

## 11. Roadmap (in dependency order)

1. **Confidence schema** — define how (raw-span, rule-id, tier) travels with
   every datum. *Unblocks everything; I1.*
2. **Arithmetic reconciliation harness** — parse `szunigin`, reconcile, tag
   records, and **measure the balance rate**. *Done (first pass):
   `tools/reconcile_szunigin.py`; grain genre-1 measured at 43% of checkable,
   §7.1.* This single number sized the rock-solid core and exposed the genre
   dependency below.
   - **2a. Genre classifier** — dispatch reconciliation on accounting genre
     (direct-sum · equivalent-ledger · area-rate · header-total · multi-section)
     before applying an equation. Surfaced as a prerequisite by step 2. Extends
     the gold set beyond genre 1 and the parser-bug queue with it.
3. **Year-name oracle, scoring resolver** — ship the probabilistic resolver
   (§7.2) *first*, against the partial vocabulary; expand `chronology.py`
   incrementally thereafter. **Non-blocking overlay (I15).**
4. **Reversible normalisation log** — make L4 auditable (I10).
5. **Prosopography layer (L5)** — scored clusters in a separate store (I4/I11).
   Begin with the evidence already in `patronymics.csv`; the ambiguous pool is a
   valid first output. **Non-blocking overlay (I15).**
6. **Provenance-carrying analytics (L6)** — frame + coverage vector + confidence
   bands on every aggregate (I12, I13, §9.0).
7. **Trailing-recipient attribution** — model the "goods, then recipient name"
   ration-list pattern explicitly, with a confidence penalty, rather than
   dropping it.

> The ordering is logical, not merely practical: step 2 produces the metric every
> later step is measured against — build the scoreboard before the game. And by
> I15, steps 3 and 5 ship *useful at partial completeness* and never block the
> rest: the oracle resolves what it can today, the identity layer emits clusters
> plus an honest ambiguous pool. Completeness is a dial, not a gate.

---

## 12. Invariants & non-goals (the contract, restated)

**Invariants:** I1–I15 above are binding. A change that violates one is a
regression even if all unit tests pass.

**Non-goals (explicitly out of scope):**
- Interpreting *intent* or *meaning* beyond the administrative formula.
- Claiming population-level (societal) statistics from an institutional archive.
- Recovering damaged signs by generative inference.
- Forcing a single identity onto an ambiguous name to make the graph tidier.
- Supporting non-Ur-III periods without explicit re-tuning (the grammar is
  period-specific).

---

## 13. Glossary

- **ATF** — ASCII Transliteration Format; CDLI's machine-readable transcription.
- **sila3** — base capacity unit (~0.84 L); all grain resolved to it.
- **szunigin** — scribal grand total; basis of the arithmetic self-check (§7.1).
- **ki … -ta** — ablative "from"; marks the issuer/source.
- **szu ba-ti** — "received"; marks the recipient.
- **giri3** — "via"; the conveying/responsible agent.
- **kiszib3** — "(under) seal of"; sealing authority.
- **dumu** — "son of"; filiation marker (mind `_PATRONYM_STOP`).
- **year-name** — Ur III year identified by a royal event; a closed vocabulary.
- **gold set** — records whose line items reconcile with their stated total; the
  self-verified, high-trust core.
- **T0–T4** — the certainty tiers (§4); the logical spine of the system.
