"""Deterministic regression harness: runs the extraction pipeline over a fixed
sample of tablets and prints a stable digest. Used to prove the package split
is behaviour-preserving (run before refactor, run after, diff the output)."""
import hashlib
import sys

from atf_pipeline import (
    ATFExtractor, Normalizer, NetworkBuilder, EntityScanner,
    load_cdli_export_file, compute_metrics,
)

N = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
corpus = load_cdli_export_file(sys.argv[1] if len(sys.argv) > 1 else "data/cdli_export.txt")
# Stride-sample across the whole corpus so the digest exercises real Ur III
# material rather than the lexicographically-first (mostly non-Ur III) IDs.
all_ids = sorted(corpus)
stride = max(1, len(all_ids) // N)
ids = all_ids[::stride]

extractor  = ATFExtractor()
normalizer = Normalizer()
scanner    = EntityScanner(normalizer)

tx_lines, rec_lines = [], []
for tid in ids:
    lines = corpus[tid]
    for tx in extractor.extract_transactions(lines, tid):
        tx = normalizer.normalize_transaction(tx)
        tx_lines.append("|".join(str(x) for x in (
            tx.tablet_id, tx.tx_type, tx.issuer, tx.recipient, tx.agent,
            tx.quantity, tx.unit, tx.commodity,
            (tx.date.king if tx.date else None),
            (tx.date.year_number if tx.date else None),
            tx.raw_date,
        )))
    s = extractor.extract_records(lines, tid)
    if s.n_records:
        scanner.scan(s)
        for r in s.records:
            for e in r.entries:
                rec_lines.append("|".join(str(x) for x in (
                    s.tablet_id, r.record_idx, r.record_type, r.issuer, r.agent,
                    e.entry_idx, e.recipient, e.quantity, e.unit, e.commodity,
                )))

def digest(rows):
    h = hashlib.sha256()
    for r in rows:
        h.update(r.encode("utf-8")); h.update(b"\n")
    return h.hexdigest()

print(f"tablets_sampled    : {len(ids)}")
print(f"transaction_rows   : {len(tx_lines)}")
print(f"entry_rows         : {len(rec_lines)}")
print(f"entities           : {scanner.entity_count}")
print(f"entity_appearances : {scanner.total_appearances}")
print(f"tx_digest          : {digest(tx_lines)}")
print(f"entry_digest       : {digest(rec_lines)}")
