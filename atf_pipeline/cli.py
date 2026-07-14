"""Command-line entry point: run the full pipeline over a corpus."""

import logging
import os
from typing import Dict, List

from atf_pipeline.entities import EntityScanner
from atf_pipeline.export import export_hierarchy_csv, export_transactions_csv
from atf_pipeline.extractor import ATFExtractor
from atf_pipeline.loaders import load_cdli_export_file, load_corpus
from atf_pipeline.models import TabletSummary, Transaction
from atf_pipeline.network import NetworkBuilder, compute_metrics, export_to_gexf
from atf_pipeline.normalize import Normalizer

logger = logging.getLogger(__name__)


def main() -> None:
    import sys
    output_dir = "output/"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        corpus = (load_cdli_export_file(arg) if os.path.isfile(arg)
                  else load_corpus(arg) if os.path.isdir(arg)
                  else {})
        if not corpus:
            logger.error("Nothing loaded from: %s", arg)
            return
    elif os.path.isfile("data/cdli_export.txt"):
        corpus = load_cdli_export_file("data/cdli_export.txt")
    else:
        corpus = load_corpus("data/raw_atf/")
    if not corpus:
        logger.error("No tablets loaded.")
        return

    # No default king: date_king is only set when the year-name (or an explicit
    # royal name in it) resolves.  King-less year-names are searched against
    # every reign's formulary, so a default would only mislabel the residue of
    # genuinely ambiguous or damaged datelines.
    extractor  = ATFExtractor()
    normalizer = Normalizer()

    all_transactions:    List[Transaction]  = []
    barley_transactions: List[Transaction]  = []
    commodity_counts:    Dict[str, int]     = {}
    all_summaries:       List[TabletSummary] = []

    # Pass 1: extract every tablet (raw, un-normalised), plus parentage pairs.
    raw_transactions: List[Transaction] = []
    patronymics = []
    for tablet_id, lines in corpus.items():
        raw_transactions.extend(extractor.extract_transactions(lines, tablet_id))
        patronymics.extend(
            (name, father, tablet_id)
            for name, father in extractor.extract_patronymics(lines)
        )
        summary = extractor.extract_records(lines, tablet_id)
        if summary.n_records > 0:
            all_summaries.append(summary)

    # Fit the normaliser on the full set of attested names so a grammatical
    # case suffix is only merged when the bare form is independently attested.
    normalizer.fit(
        [who
         for tx in raw_transactions
         for who in (
             tx.issuer,
             tx.recipient,
             *(tx.agent.split("; ") if tx.agent else [None]),
         )]
        + [e.recipient for s in all_summaries for r in s.records for e in r.entries]
    )

    # Pass 2: normalise transactions and scan entities.
    entity_scanner = EntityScanner(normalizer)
    for tx in raw_transactions:
        tx = normalizer.normalize_transaction(tx)
        all_transactions.append(tx)
        if tx.commodity:
            commodity_counts[tx.commodity] = commodity_counts.get(tx.commodity, 0) + 1
        if tx.commodity == "barley":
            barley_transactions.append(tx)
    for summary in all_summaries:
        entity_scanner.scan(summary)
    entity_scanner.add_patronymics(patronymics)

    n_total   = len(all_transactions)
    n_barley  = len(barley_transactions)
    n_tablets = len(set(tx.tablet_id for tx in all_transactions))
    n_complete = sum(1 for tx in all_transactions if tx.issuer and tx.recipient)
    n_complete_barley = sum(1 for tx in barley_transactions if tx.issuer and tx.recipient)

    logger.info("Extracted %d transactions from %d tablets; %d barley.",
                n_total, n_tablets, n_barley)

    print(f"\nExtraction summary")
    print(f"  Total transactions : {n_total}")
    print(f"  Tablets with data  : {n_tablets}/{len(corpus)} ({100*n_tablets//len(corpus)}%)")
    print(f"  Fully complete     : {n_complete}/{n_total} ({100*n_complete//max(n_total,1)}%)")

    print(f"\nCommodity breakdown:")
    for comm, cnt in sorted(commodity_counts.items(), key=lambda x: -x[1]):
        print(f"  {comm:15s}: {cnt}")

    # Volume by commodity — grain (sila3), silver (gin2), animals (head), labor (worker-day)
    # bran/groats are barley byproducts (see extract_quantity.py's "sze X"
    # compound handling) and belong in the grain total; dairy (ga-sze-a,
    # ga-UD) is milk-derived and does not.
    GRAIN_COMMS = {"barley", "emmer", "wheat", "flour", "beer", "oil", "dates", "malt",
                   "bran", "groats"}
    by_comm: Dict[str, float] = {}
    for tx in all_transactions:
        if tx.quantity and tx.commodity:
            by_comm[tx.commodity] = by_comm.get(tx.commodity, 0) + tx.quantity
    grain_sila3 = sum(
        v for c, v in by_comm.items() if c in GRAIN_COMMS
    )
    print(f"\nVolumes by commodity:")
    print(f"  {'Grain total (sila3)':<20s}: {grain_sila3:>20,.0f}")
    for comm, vol in sorted(by_comm.items(), key=lambda x: -x[1]):
        unit_label = (
            "sila3" if comm in GRAIN_COMMS
            else "gin2" if comm == "silver"
            else "head" if comm == "animal"
            else "worker-day" if comm == "labor"
            else ""
        )
        print(f"  {comm:<20s}: {vol:>20,.0f}  {unit_label}")

    sulgi_slice = [
        tx for tx in barley_transactions
        if tx.date and tx.date.in_range("Šulgi", 45, 48)
    ]
    logger.info("Šulgi yr 45-48 barley: %d", len(sulgi_slice))

    builder = NetworkBuilder()
    G = builder.build(barley_transactions)

    print(f"\nBarley network")
    print(f"  Nodes : {G.number_of_nodes()}")
    print(f"  Edges : {G.number_of_edges()}")
    print(f"  Fully-resolved barley tx : {n_complete_barley}/{n_barley} "
          f"({100*n_complete_barley//max(n_barley,1)}%)")

    if G.number_of_nodes() > 0:
        metrics = compute_metrics(G)
        print(f"  Density : {metrics['density']:.4f}")
        print(f"  Weakly conn. comps : {metrics['num_weakly_connected_components']}")

        print("\nTop 5 by PageRank:")
        pr = sorted(metrics["pagerank"].items(), key=lambda x: x[1], reverse=True)
        for node, val in pr[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by betweenness (brokers):")
        bc = sorted(metrics["betweenness_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in bc[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by in-degree (major recipients):")
        idc = sorted(metrics["in_degree_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in idc[:5]:
            print(f"  {node}: {val:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    export_to_gexf(G, os.path.join(output_dir, "barley_network.gexf"))
    export_transactions_csv(all_transactions,    os.path.join(output_dir, "transactions_all.csv"))
    export_transactions_csv(barley_transactions, os.path.join(output_dir, "transactions_barley.csv"))
    if sulgi_slice:
        export_transactions_csv(sulgi_slice, os.path.join(output_dir, "transactions_sulgi_45-48.csv"))

    # Hierarchical outputs
    export_hierarchy_csv(
        all_summaries,
        os.path.join(output_dir, "tablets.csv"),
        os.path.join(output_dir, "records.csv"),
        os.path.join(output_dir, "entries.csv"),
    )
    entity_scanner.export_csv(os.path.join(output_dir, "entities.csv"))
    entity_scanner.export_patronymics_csv(os.path.join(output_dir, "patronymics.csv"))

    total_records = sum(s.n_records for s in all_summaries)
    total_entries = sum(s.n_entries for s in all_summaries)
    print(f"\nHierarchical counts:")
    print(f"  Tablets with records : {len(all_summaries)}")
    print(f"  Total records        : {total_records}")
    print(f"  Total entries        : {total_entries}")
    print(f"  Unique entities      : {entity_scanner.entity_count}")
    print(f"  Entity appearances   : {entity_scanner.total_appearances}")
    print(f"  Shared names (2+ fathers): {entity_scanner.homonym_count}")
