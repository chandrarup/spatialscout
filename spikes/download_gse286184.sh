#!/bin/zsh
# Downloads per-section Xenium transcripts, cells and features for GSE286184 (22 sections). Raw data is never committed.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)/data/raw/GSE286184
for n in {1..22}; do
  gsm=GSM$((8720408 + n)); base=${gsm}_kidney_xenium_${n}
  mkdir -p "$ROOT/$gsm"
  for f in transcripts.parquet.gz cells.csv.gz features.tsv.gz; do
    out="$ROOT/$gsm/${base}_$f"
    [[ -s "$out" ]] && continue
    curl -fsSL --retry 3 -o "$out.part" "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM8720nnn/$gsm/suppl/${base}_$f" && mv "$out.part" "$out"
  done
  echo "done $gsm"
done
du -sh "$ROOT"
