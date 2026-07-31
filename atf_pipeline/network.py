"""Directed-weighted network construction, centrality metrics, and GEXF export."""

import logging
import os
from typing import Dict, List

import networkx as nx

from atf_pipeline.models import Transaction

logger = logging.getLogger(__name__)


class NetworkBuilder:
    """Build a directed weighted NetworkX graph from a list of transactions."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_transaction(self, tx: Transaction) -> None:
        if not tx.issuer or not tx.recipient:
            return
        weight = tx.quantity if tx.quantity else 1.0
        if self.graph.has_edge(tx.issuer, tx.recipient):
            self.graph[tx.issuer][tx.recipient]["weight"] += weight
            self.graph[tx.issuer][tx.recipient]["count"]  += 1
        else:
            self.graph.add_edge(
                tx.issuer, tx.recipient,
                weight=weight, count=1,
                commodity=tx.commodity or "",
            )
        for node in (tx.issuer, tx.recipient):
            if "commodities" not in self.graph.nodes[node]:
                self.graph.nodes[node]["commodities"] = set()
            if tx.commodity:
                self.graph.nodes[node]["commodities"].add(tx.commodity)

    def build(self, transactions: List[Transaction]) -> nx.DiGraph:
        for tx in transactions:
            self.add_transaction(tx)
        return self.graph


def compute_metrics(G: nx.DiGraph) -> Dict:
    metrics = {
        "degree_centrality":      nx.degree_centrality(G),
        "in_degree_centrality":   nx.in_degree_centrality(G),
        "out_degree_centrality":  nx.out_degree_centrality(G),
        "betweenness_centrality": nx.betweenness_centrality(G, weight="weight"),
        "density":                nx.density(G),
        "num_weakly_connected_components": nx.number_weakly_connected_components(G),
    }
    try:
        metrics["pagerank"] = nx.pagerank(G, weight="weight")
    except Exception:
        metrics["pagerank"] = metrics["in_degree_centrality"]
    return metrics


def export_to_gexf(G: nx.DiGraph, filepath: str) -> None:
    H = G.copy()
    for node in H.nodes():
        if "commodities" in H.nodes[node]:
            H.nodes[node]["commodities"] = ",".join(
                sorted(H.nodes[node]["commodities"])
            )
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        nx.write_gexf(H, filepath)
        logger.info("Network exported to GEXF: %s", filepath)
    except OSError as exc:
        logger.error("Failed to write GEXF to %s: %s", filepath, exc)
