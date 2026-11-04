# ADR-0009: The data check before a question runs

Status: accepted, 2026-11-04

## Context

Researchers ask questions this workspace cannot answer: a gene off GSE286184's 50-gene panel, a cell type no label
rule names, a disease the cohort lacks, another organ or species. A run on such a question either fails at plan
validation or, worse, answers a nearby question without saying so. The researcher should learn, before anything
runs, what is missing and where to get it.

## Decision

`POST /api/data-fit` runs before any question that no recording answers.

- **Reading the question is code, not a model.** Genes are HGNC protein-coding symbols or unambiguous aliases
  (`artifacts/reference/hgnc_genes.tsv.gz`, built by `scripts/build_gene_vocabulary.py`) plus protein names; a
  letters-only word counts only when written in capitals, and disease, cell-type and assay abbreviations never do.
  Cell types, groups, organs, species and assays come from fixed phrase lists set against the dataset's own label
  rules, groups and the KPMP enrollment categories.
- **Hard gaps stop the run**: a known protein-coding gene off the panel, an unlabelled cell type, another organ,
  another species, or an assay the workspace lacks (chromatin, methylation, metabolites, genome-wide expression).
  **Soft gaps** are shown and a live run may go ahead on what is here: a disease the cohort lacks, outcomes, treatment,
  time, a gene-shaped word that is no known protein-coding gene, and a gene whose protein the KPMP biopsies image
  (the note sends the researcher to the biopsy's box audit). CKD stage codes (G3a, A2) are never read as genes.
- **Two ways to get the rest**: the Your data page, prefilled with the question's cell type and genes and the exact
  columns the files need; and public datasets from a live NCBI GEO search (E-utilities, db=gds), most specific query
  first, topped up from broader ones. Each dataset is a record GEO returned; its technology is read from its title and
  summary, and only human Xenium records are marked "audit it here". GSE286184 itself is left out.
- When it fails, it fails open: if the check cannot run, the question runs as before.

## Consequences

- No model call, so the check costs nothing and plays the same in every run mode.
- Reading by phrase lists misses wordings the lists lack; a missed need means a question runs that would have been
  flagged. A wrong block is possible only through a word the lists misread, so the words the biopsy screens show are
  tested never to block. All-capitals text is not read for letters-only genes.
- GEO search quality is GEO's: results are leads to read, not claims the product makes.
