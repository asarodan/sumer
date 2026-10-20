#!/usr/bin/env python3
"""
analyze_verified.py — Economic analysis of reconciliation-verified grain tablets.

Restricts to the 90 tablets that pass the szunigin arithmetic self-check
(harness balanced ≤ 1 sila3 tolerance), giving a ground-truth subset where
the pipeline's extracted entries are independently confirmed correct by the
ancient scribe's own grand total.

Outputs:
  output/verified_entries.csv        – individual grain entries (verified only)
  output/verified_summary.txt        – text report with Gini, rations, issuers
  output/figures/fig_verified_*.png  – Lorenz curve, histogram, Lorenz by king
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from atf_pipeline import ATFExtractor
from atf_pipeline.loaders import load_cdli_export_file

# ── palette (matches make_paper_figures.py) ──────────────────────────────────
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["DejaVu Serif"],
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "figure.dpi": 130, "savefig.dpi": 200,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "axes.axisbelow": True,
})
INK   = "#1a1a1a"
ACC   = "#8b1a1a"
GOLD  = "#b8860b"
STEEL = "#2c4a6e"

# ── harness constants (mirror reconcile_szunigin.py) ─────────────────────────
_DAMAGE            = re.compile(r"[\[\]#]|(?<![a-z])x(?![a-z])|\?", re.I)
_SZU_WORD          = re.compile(r"^\[?(?:szunigin2?|šunigin2?|szu-nigin2?|šu-nigin2?)\b[#!?]*\s*", re.I)
_HAS_SZE           = re.compile(r"\bsze\b", re.I)
_OTHER_COMM        = re.compile(r"\b(kasz|ninda|i3|naga|zu2-lum|tug2|siki|ku3)\b", re.I)
_ARCHAIC           = re.compile(r"@c\b", re.I)
_EQUIV_BI          = re.compile(r"\b\S+-bi\b", re.I)
_QTY_TOKEN         = re.compile(r"\d+(?:/\d+)?\((?:asz|barig|ban2|sila3|gur|gesz2|gesz'u|szar2|szar'u|u|disz)[^)]*\)", re.I)
_LINE_START_ERASED = re.compile(r"^\d+[a-z']?\.\s*\[\.+\]")
_BROKEN_FACE       = re.compile(r"^\$\s+(?:rest\s+|beginning\s+)?broken\b", re.I)
_LA2_IA3           = re.compile(r"\bla2-ia3\b", re.I)
_SZA3_BI_TA        = re.compile(r"\bsza3-bi-ta\b", re.I)
_RATE_TA           = re.compile(
    r"\d+(?:/\d+)?\((?:asz|barig|ban2|sila3|gur|disz)[^)]*\)"
    r"(?:-ta\b|(?:\s+(?:asz|barig|ban2|sila3|gur))?\s+\S*-ta\b)", re.I)
_DURATION          = re.compile(
    r"(?:\bu4\s+\d+(?:/\d+)?\([^)]+\)(?:\s+la2\s+\d+(?:/\d+)?\([^)]+\))?"
    r"(?:\s+\d+(?:/\d+)?\([^)]+\))?(?:-sze3|-a)\b|\biti\s+\d+(?:/\d+)?\([^)]+\)-sze3\b)", re.I)
_GAN2_RATE         = re.compile(r"\bGAN2\b.*\bgur-ta\b", re.I)
_SZE_GAN2          = re.compile(r"\bsze\b.*\bGAN2\b", re.I)
_NAM_GROUP         = re.compile(r"\bnam-\d+\(", re.I)
_ITI_AKAM          = re.compile(r"\biti\s+(?:.*?-a-kam|\d+(?:/\d+)?\([^)]+\)-kam)\b", re.I)
_LEFT_FACE_MARKER  = re.compile(r"^@left\b", re.I)
_UGULA             = re.compile(r"\bugula\b", re.I)
_BARE_SUBTOTAL     = re.compile(
    r"^\d+[a-z']?\.\s*\d+(?:/\d+)?\([^)]+\)(?:\s+(?:la2\s+)?\d+(?:/\d+)?\([^)]+\))*\s*$", re.I)
_REVERSE_MARKER    = re.compile(r"^@reverse\b", re.I)
_STRIP_LINENUM     = re.compile(r"^\d+[a-z']?\.\s*")
_NON_GRAIN_COMM    = frozenset({"beer", "oil", "dates", "bread", "silver", "gold"})
_NON_BARLEY_GRAIN  = frozenset({"emmer", "wheat"})
_SISA2             = re.compile(r"\bsi-sa2\b", re.I)
_TOL               = 1.0


def _has_left_face_quantity(lines):
    in_left = False
    for ln in lines:
        s = ln.strip()
        if _LEFT_FACE_MARKER.match(s):
            in_left = True; continue
        if s.startswith("@") and not _LEFT_FACE_MARKER.match(s):
            in_left = False
        if in_left and _QTY_TOKEN.search(s):
            return True
    return False


def _has_supervisor_subtotals(lines):
    if not any(_UGULA.search(ln) for ln in lines):
        return False
    return any(_BARE_SUBTOTAL.match(ln.strip()) for ln in lines)


def _has_reverse_source_block(lines):
    in_reverse = False
    for ln in lines:
        s = ln.strip()
        if _REVERSE_MARKER.match(s):
            in_reverse = True; continue
        if s.startswith("@") and not _REVERSE_MARKER.match(s):
            in_reverse = False; continue
        if not in_reverse:
            continue
        if not s or s.startswith("$") or s.startswith("#"):
            continue
        content = _STRIP_LINENUM.sub("", s).strip()
        if not content:
            continue
        if re.match(r"ki\s", content, re.I) and not re.search(r"-ta\b", content, re.I):
            return True
        break
    return False


def _has_damaged_quantity(lines):
    for ln in lines:
        if _QTY_TOKEN.search(ln) and _DAMAGE.search(ln):
            return True
        if _LINE_START_ERASED.match(ln):
            return True
    return False


def _is_genre1(lines):
    has_rate = has_duration = False
    for ln in lines:
        s = ln.strip()
        if _BROKEN_FACE.match(s):          return False
        if _LA2_IA3.search(s):             return False
        if _SZA3_BI_TA.search(s):          return False
        if _GAN2_RATE.search(s):           return False
        if _QTY_TOKEN.search(s) and _SZE_GAN2.search(s): return False
        if _NAM_GROUP.search(s):           return False
        if _ITI_AKAM.search(s):            return False
        if _RATE_TA.search(s):             has_rate = True
        if _DURATION.search(s):            has_duration = True
    if has_rate and has_duration:          return False
    if _has_left_face_quantity(lines):     return False
    if _has_supervisor_subtotals(lines):   return False
    if _has_reverse_source_block(lines):   return False
    return True


def _designation(lines):
    m = re.match(r"^&P\d+\s*=\s*(.+?)\s*$", lines[0].strip()) if lines else None
    return m.group(1) if m else ""


# ── helpers ───────────────────────────────────────────────────────────────────
def gini(x: np.ndarray) -> float:
    x = np.sort(x[x > 0])
    if len(x) == 0:
        return float("nan")
    n = len(x)
    i = np.arange(1, n + 1)
    return float((2 * np.sum(i * x) / (n * np.sum(x))) - (n + 1) / n)


def lorenz(x: np.ndarray):
    x = np.sort(x[x > 0])
    c = np.cumsum(x) / x.sum()
    return np.linspace(0, 1, len(c) + 1), np.concatenate([[0], c])


def fmt_sila3(v: float) -> str:
    gur = int(v // 300)
    rem = v - gur * 300
    barig = int(rem // 60)
    rem2 = rem - barig * 60
    ban2 = int(rem2 // 10)
    sila = int(rem2 % 10)
    parts = []
    if gur:   parts.append(f"{gur} gur")
    if barig: parts.append(f"{barig} barig")
    if ban2:  parts.append(f"{ban2} ban2")
    if sila:  parts.append(f"{sila} sila3")
    return " ".join(parts) or "0 sila3"


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    corpus_path = sys.argv[1] if len(sys.argv) > 1 else "data/cdli_export.txt"
    out_dir = "output"
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    ext = ATFExtractor()
    corpus = load_cdli_export_file(corpus_path)

    # ── Pass 1: reconciliation harness — collect verified tablet IDs ──────────
    verified_ids: list[str] = []
    for tablet_id, lines in corpus.items():
        if any(_ARCHAIC.search(ln) for ln in lines):
            continue
        szu_lines = [ln for ln in lines if ext._RE_SZUNIGIN.match(ln.strip())]
        if not szu_lines:
            continue
        szu_clean = ext._strip_linenum(szu_lines[0])
        szu_body  = _SZU_WORD.sub("", szu_clean).strip()
        if _EQUIV_BI.search(szu_body):
            continue
        if not _HAS_SZE.search(szu_body) or _OTHER_COMM.search(szu_body):
            continue
        total_q, total_u = ext.extract_quantity(szu_body, context_gur=True)
        if total_q is None or total_u != "sila3":
            continue
        if len(szu_lines) > 1:
            continue
        if _SISA2.search(szu_body):
            continue
        if not _is_genre1(lines) or _has_damaged_quantity(lines):
            continue

        summary = ext.extract_records(lines, tablet_id)
        barley_sum = grain_sum = 0.0
        n_items = 0
        for rec in summary.records:
            for e in rec.entries:
                if e.unit != "sila3" or e.quantity is None:
                    continue
                if e.commodity in _NON_GRAIN_COMM:
                    continue
                grain_sum += e.quantity
                n_items += 1
                if e.commodity not in _NON_BARLEY_GRAIN:
                    barley_sum += e.quantity
        if n_items == 0:
            continue

        if abs(barley_sum - total_q) <= _TOL:
            item_sum = barley_sum
        elif abs(grain_sum - total_q) <= _TOL:
            item_sum = grain_sum
        else:
            continue  # unbalanced — skip

        verified_ids.append(tablet_id)

    print(f"Verified tablets: {len(verified_ids)}", file=sys.stderr)

    # ── Pass 2: extract dates via transactions, then grain entries ───────────
    # Dates come from extract_transactions; grain entries from extract_records.
    tablet_dates: dict[str, dict] = {}
    for tablet_id in verified_ids:
        lines = corpus[tablet_id]
        for tx in ext.extract_transactions(lines, tablet_id):
            d = tx.date
            if d and (d.king or d.year_name or d.month):
                tablet_dates[tablet_id] = {
                    "king":  d.king or "",
                    "year":  d.year_number,
                    "month": d.month or "",
                }
                break

    rows = []
    for tablet_id in verified_ids:
        lines = corpus[tablet_id]
        desig = _designation(lines)
        summary = ext.extract_records(lines, tablet_id)
        dt = tablet_dates.get(tablet_id, {})

        for rec in summary.records:
            for e in rec.entries:
                if e.unit != "sila3" or e.quantity is None or e.quantity <= 0:
                    continue
                if e.commodity in _NON_GRAIN_COMM:
                    continue
                rows.append({
                    "tablet_id":  tablet_id,
                    "designation": desig,
                    "issuer":     rec.issuer or "",
                    "recipient":  e.recipient or "",
                    "quantity":   e.quantity,
                    "commodity":  e.commodity or "barley",
                    "date_king":  dt.get("king", ""),
                    "date_year":  dt.get("year"),
                    "date_month": dt.get("month", ""),
                })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "verified_entries.csv"), index=False)
    print(f"Entries written: {len(df)}", file=sys.stderr)

    # ── Analysis ──────────────────────────────────────────────────────────────
    b  = df[df.commodity.isin({"barley"}) | df.commodity.isna()]
    gb = df[~df.commodity.isin(_NON_BARLEY_GRAIN)]  # barley + unlabelled (= barley)
    q  = df.quantity.values

    lines_out = []
    W = lambda *a: lines_out.append(" ".join(str(x) for x in a))

    W("=" * 68)
    W("  VERIFIED-CORPUS GRAIN ECONOMIC ANALYSIS")
    W(f"  {len(verified_ids)} reconciliation-verified genre-1 tablets")
    W("=" * 68)
    W()
    W(f"{'Grain entries (all commodities)':40s}: {len(df):,}")
    W(f"{'Unique tablets':40s}: {df.tablet_id.nunique():,}")
    W(f"{'Unique recipients (named)':40s}: {(df.recipient != '').sum():,} entries, "
      f"{df[df.recipient != ''].recipient.nunique():,} unique names")
    W(f"{'Unique issuers (named)':40s}: {(df.issuer != '').sum():,} entries, "
      f"{df[df.issuer != ''].issuer.nunique():,} unique names")
    W()

    # Commodity breakdown
    W("── Commodity breakdown ──────────────────────────────────────────")
    comm_vol = df.groupby("commodity").quantity.agg(["sum", "count"]).sort_values("sum", ascending=False)
    for comm, row in comm_vol.iterrows():
        W(f"  {comm or 'unlabelled':15s}: {row['count']:5,} entries  "
          f"  {row['sum']:>12,.0f} sila3  ({row['sum']/300:,.0f} gur)")
    W(f"  {'TOTAL':15s}: {len(df):5,} entries  "
      f"  {df.quantity.sum():>12,.0f} sila3  ({df.quantity.sum()/300:,.0f} gur)")
    W()

    # Distribution statistics
    W("── Entry-level distribution (all grain, sila3) ──────────────────")
    pcts = [10, 25, 50, 75, 90, 95, 99]
    for p in pcts:
        W(f"  p{p:02d}: {np.percentile(q, p):>10,.0f}  ({fmt_sila3(np.percentile(q, p))})")
    W(f"  Mean:  {np.mean(q):>10,.0f}  ({fmt_sila3(np.mean(q))})")
    W(f"  Max:   {np.max(q):>10,.0f}  ({fmt_sila3(np.max(q))})")
    W()

    # Gini
    G_entry  = gini(q)
    G_tablet = gini(df.groupby("tablet_id").quantity.sum().values)
    G_recip  = gini(df[df.recipient != ""].groupby("recipient").quantity.sum().values)
    W("── Inequality (Gini coefficients) ───────────────────────────────")
    W(f"  Per-entry       : {G_entry:.4f}")
    W(f"  Per-tablet      : {G_tablet:.4f}  (grain totals by tablet)")
    if len(df[df.recipient != ""]) > 1:
        W(f"  Per-recipient   : {G_recip:.4f}  (total received per named person)")
    W("  (0 = perfect equality, 1 = maximum concentration)")
    W()

    # Most common ration sizes
    W("── Most common entry sizes (sila3) ──────────────────────────────")
    size_counts = Counter(int(round(v)) for v in q)
    max_cnt = max(size_counts.values()) if size_counts else 1
    for size, cnt in size_counts.most_common(12):
        bar = "█" * min(cnt * 40 // max(max_cnt, 1) + 1, 40)
        W(f"  {size:>6,}  {fmt_sila3(size):20s}  {cnt:4,}  {bar}")
    W()

    # Top issuers
    issued = df[df.issuer != ""]
    if len(issued):
        W("── Top 10 grain issuers (verified corpus) ───────────────────────")
        top_issuers = (issued.groupby("issuer")
                       .agg(tablets=("tablet_id","nunique"), entries=("quantity","count"),
                            total_sila3=("quantity","sum"))
                       .sort_values("total_sila3", ascending=False).head(10))
        for name, row in top_issuers.iterrows():
            W(f"  {name[:30]:30s}  {int(row.tablets):2d} tablets  "
              f"{int(row.entries):4,} entries  {row.total_sila3:>10,.0f} sila3")
        W()

    # Top recipients
    received = df[df.recipient != ""]
    if len(received):
        W("── Top 10 grain recipients (verified corpus) ────────────────────")
        top_recip = (received.groupby("recipient")
                     .agg(tablets=("tablet_id","nunique"), entries=("quantity","count"),
                          total_sila3=("quantity","sum"))
                     .sort_values("total_sila3", ascending=False).head(10))
        for name, row in top_recip.iterrows():
            W(f"  {name[:30]:30s}  {int(row.tablets):2d} tablets  "
              f"{int(row.entries):4,} entries  {row.total_sila3:>10,.0f} sila3")
        W()

    # Temporal breakdown
    dated = df[df.date_king != ""]
    if len(dated):
        W("── Temporal breakdown (dated tablets) ───────────────────────────")
        by_king = dated.groupby("date_king").agg(
            tablets=("tablet_id","nunique"), entries=("quantity","count"),
            total_sila3=("quantity","sum"))
        for king, row in by_king.sort_values("total_sila3", ascending=False).iterrows():
            W(f"  {king:15s}: {int(row.tablets):3d} tablets  "
              f"{int(row.entries):5,} entries  {row.total_sila3:>12,.0f} sila3")
        W()

    # Cross-tablet recipients (appearing on ≥2 tablets)
    if len(received):
        multi = (received.groupby("recipient")
                 .agg(tablets=("tablet_id","nunique"), total=("quantity","sum"))
                 .query("tablets >= 2").sort_values("total", ascending=False))
        W("── Recipients on 2+ verified tablets ────────────────────────────")
        W(f"  {len(multi):,} unique names appear across multiple verified tablets")
        for name, row in multi.head(10).iterrows():
            W(f"  {name[:30]:30s}  {int(row.tablets)} tablets  {row.total:,.0f} sila3")
        W()

    report = "\n".join(lines_out)
    print(report)
    with open(os.path.join(out_dir, "verified_summary.txt"), "w") as f:
        f.write(report + "\n")

    # ── Figures ───────────────────────────────────────────────────────────────
    # Fig A: Entry-size distribution (log scale)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    lq = np.log10(q[q > 0])
    ax.hist(lq, bins=50, color=STEEL, edgecolor="white", linewidth=0.3, alpha=0.9)
    ax.axvline(np.log10(np.median(q)), color=ACC, ls="--", lw=1.4,
               label=f"median = {np.median(q):.0f} sila₃")
    ax.axvline(np.log10(300), color=GOLD, ls=":", lw=1.4, label="1 gur = 300 sila₃")
    ax.set_xlabel("Entry size  (log₁₀ sila₃)")
    ax.set_ylabel("Number of entries")
    ax.set_title(f"(a)  Grain entry-size distribution — verified corpus  (N = {len(q):,})")
    ax.legend(frameon=False, fontsize=8.5)
    xt = [0, 1, 2, 3, 4, 5]
    ax.set_xticks(xt); ax.set_xticklabels(["1","10","100","1k","10k","100k"])
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "fig_verified_a_txsize.png")); plt.close()

    # Fig B: Lorenz curve
    fig, ax = plt.subplots(figsize=(5.2, 5))
    for data, col, lab in [
        (q,                                              STEEL, f"entries  (G={G_entry:.3f})"),
        (df.groupby("tablet_id").quantity.sum().values,  ACC,   f"tablets  (G={G_tablet:.3f})"),
    ]:
        px, ly = lorenz(data)
        ax.plot(px, ly, color=col, lw=1.8, label=lab)
    ax.plot([0, 1], [0, 1], color=INK, ls="--", lw=1, label="equality")
    ax.fill_between(px, ly, px, color=ACC, alpha=0.06)
    ax.set_xlabel("Cumulative share of entries (ranked low→high)")
    ax.set_ylabel("Cumulative share of grain volume")
    ax.set_title("(b)  Grain concentration — verified corpus")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_aspect("equal"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "fig_verified_b_lorenz.png")); plt.close()

    # Fig C: Ration frequency bar chart (common sizes)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    top_sizes = [(sz, cnt) for sz, cnt in size_counts.most_common(15)]
    sizes  = [s for s, _ in top_sizes]
    counts = [c for _, c in top_sizes]
    ax.bar(range(len(sizes)), counts, color=STEEL, edgecolor="white", linewidth=0.4)
    ax.set_xticks(range(len(sizes)))
    ax.set_xticklabels([fmt_sila3(s).replace(" ", "\n") for s in sizes], fontsize=7)
    ax.set_ylabel("Number of entries")
    ax.set_title("(c)  Most common grain ration sizes — verified corpus")
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "fig_verified_c_rations.png")); plt.close()

    print(f"\nFigures written to {fig_dir}/fig_verified_*.png", file=sys.stderr)
    print(f"Report written to {out_dir}/verified_summary.txt", file=sys.stderr)
    print(f"Data written to {out_dir}/verified_entries.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
