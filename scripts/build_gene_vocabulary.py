"""Build the gene vocabulary the data check reads (`artifacts/reference/hgnc_genes.tsv.gz`) from HGNC's
protein-coding gene list.

    uv run python scripts/build_gene_vocabulary.py <gene_with_protein_product.txt>

Source: https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/locus_types/gene_with_protein_product.txt
Each row: an approved symbol, then its previous symbols and aliases that name no other gene (an alias shared by two
genes is dropped, so a match is never a guess)."""

import csv
import gzip
import sys
from collections import Counter
from pathlib import Path

source = Path(sys.argv[1])
rows = list(csv.DictReader(source.open(encoding="utf-8"), delimiter="\t"))
approved = {r["symbol"].upper() for r in rows}
other = Counter()
for r in rows:
    for name in {a.strip().upper() for a in (r["alias_symbol"] + "|" + r["prev_symbol"]).split("|") if a.strip()}:
        other[name] += 1
out = Path("artifacts/reference/hgnc_genes.tsv.gz")
out.parent.mkdir(parents=True, exist_ok=True)
with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as handle:
    handle.write("# HGNC protein-coding genes (gene_with_protein_product.txt): symbol<TAB>unambiguous aliases and previous symbols\n")
    for r in sorted(rows, key=lambda r: r["symbol"]):
        names = sorted({a.strip().upper() for a in (r["alias_symbol"] + "|" + r["prev_symbol"]).split("|") if a.strip()})
        keep = [a for a in names if other[a] == 1 and a not in approved]
        handle.write(r["symbol"] + "\t" + "|".join(keep) + "\n")
print(f"{len(rows):,} genes -> {out} ({out.stat().st_size:,} bytes)")
