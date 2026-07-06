# Supplementary Material

This directory contains every file referenced in the methodology
appendix and the deprecation census appendix of the paper. Each file
is paired below with the appendix subsection that cites it. All files
are anonymized for double-blind review.

## Directory Layout

```
Supplementary/
├── keywords/   (keyword lists, deprecation registry, broad-term list)
├── code/       (sampling, search, extraction, and inference scripts)
├── data/       (canonical analysis outputs from the search pipeline)
├── audit/      (locked stratified sample and labeled audit results)
└── census/     (manually labeled deprecated-model census)
```

## File Index

### keywords/

| File | Cited in Appendix | Description |
|---|---|---|
| `keywords_active.txt` | A.2 (Model Name Extraction) | The active closed-source identifier list used for the keyword search. Includes base names and versioned checkpoints across OpenAI, Anthropic, and Google. |
| `keywords_updated.txt` | A.2 (Model Name Extraction) | The expanded keyword list including older / deprecated identifiers no longer in the active set. The keyword search uses the union of both files (248 unique identifiers after deduplication, per Table A.2). |
| `general_llm_terms.txt` | A.3 (Broad LLM Engagement Search) | The 81-term general LLM/VLM term list searched against titles and abstracts only, organized into nine thematic sections. |
| `deprecation_registry.csv` | A.7 (Deprecation Cross-Referencing) | Provider-published shutdown-date registry covering 120 closed-source models. Each row pairs a model identifier with its shutdown date. The analysis uses this registry plus a manually-curated list of additional deprecated identifiers documented in `code/extract_results.py:589-606`. |

### code/

| File | Cited in Appendix | Description |
|---|---|---|
| `search_md_files.py` | A.2 (Model Name Extraction) | Top-level keyword search pipeline. Walks the markdown extraction, runs the per-paper keyword regex with references-section exclusion, compound-token exclusion, and o1/o3 disambiguation. Produces `data/paper_text_search_results.csv`. |
| `md_processor.py` | A.2.2 (Search Procedure) | Section parsing, references-section detection, compound-token exclusion list (`COMPOUND_MODELS`), and o1/o3 suffix list (`O1_O3_SUFFIXES`). The compound-check keyword subset is `COMPOUND_CHECK_KEYWORDS = {gpt4, gpt3, gpt35, gpt}`. |
| `extract_results.py` | A.2 / A.7 / A.8 | Master analysis script. Defines `EXACT_MODELS`, `BASE_MODELS`, the deprecation cutoff date 2026-02-13, and the manually-curated additional deprecated identifiers list at lines 589-606. Computes per-year corpus counts, deprecation impact, ChatGPT-only counts, base-name-only counts, and exact-vs-base reporting practice statistics. |
| `search_chatgpt_by_section.py` | A.8 (Underreporting Analysis) | The section-aware search for ``ChatGPT'' mentions. Produces `data/chatgpt_section_search.csv` with per-paper match counts broken down by section type (methods, experiments, results, intro, references, etc.). |
| `search_abstract_title.py` | A.3 (Broad LLM Engagement Search) | Title-and-abstract-restricted search for the 81 broad LLM terms in `keywords/general_llm_terms.txt`. Produces the 16,063-paper (37.9\%) broad-engagement count. |
| `draw_stratified_sample.py` | A.4 (Stratified Manual Audit) | Sampling code for the 1,000-paper audit. Locks the random seed at 42 and writes the sample list to `audit/audit_locked_sample.csv`. Re-running this script with the same input bit-for-bit reproduces the audit sample. |
| `analyze_stratified_sample.py` | A.4 (Stratified Manual Audit) | Inference script for the audit. Reads the labeled audit file and produces the corpus-level estimates with stratified-bootstrap 95\% confidence intervals reported in Tables A.4 through A.6. |
| `extract_deprecation_evidence.py` | B (Deprecated-Model Census) | Builds the (paper, deprecated-keyword) pair list from the deprecation registry intersected with the keyword search results. Used to produce the 1,008-pair census file. |

### data/

| File | Cited in Appendix | Description |
|---|---|---|
| `paper_text_search_results.csv` | A.2 / A.7 / A.8 | Canonical output of the paper-text keyword search. One row per paper, with columns for total matches, unique keywords matched, and per-keyword occurrence counts. Source for the 4,817 matched-paper figure, the 64,506 total-occurrence figure, and the per-provider breakdowns. |
| `chatgpt_section_search.csv` | A.8 / A.8.3 | Section-level breakdown of ``ChatGPT'' mentions, one row per paper with per-section match counts. Source for the 312 substantive ChatGPT-only count and the 1,005-paper non-substantive subset. |
| `github_repository_keywords.csv` | A.6 (Repository Analysis) | Repository keyword search results. One row per (paper, repository) entry, with columns for repository accessibility and the exact identifiers extracted from the repository's code. Source for the 26,849 entry count, the 23,038 / 3,811 accessibility split, and the top-10 repository keyword table. |
| `github_analysis_report.txt` | A.6 (Repository Analysis) | Human-readable report summarizing the repository analysis, including the o1/o3/o4 false-positive exclusion counts and the per-keyword occurrence ranks. |

### audit/

| File | Cited in Appendix | Description |
|---|---|---|
| `audit_locked_sample.csv` | A.4 (Stratified Manual Audit) | The 1,000-paper sample with strata, weights, and per-row sampling metadata. Locked before annotation began. Re-running `code/draw_stratified_sample.py` produces this file bit-for-bit. |
| `audit_locked_sample_summary.txt` | A.4 (Stratified Manual Audit) | Audit trail summary: per-stratum population, sample size, inclusion probability, weight, and sampled-keyword frequency. Confirms the proportional allocation reported in Table A.5. |
| `audit_labels_final.csv` | A.4 (Stratified Manual Audit) | Manually labeled audit data, one row per (paper, sampled-keyword) pair. Columns: `Sample_ID`, `Year`, `Venue`, `Sampled_Keyword`, `Section`, `Label`, `Reasoning`. |

### census/

| File | Cited in Appendix | Description |
|---|---|---|
| `deprecation_labels_final.csv` | B (Deprecated-Model Census) | Complete manual census of every (paper, deprecated-keyword) pair in the matched-paper set. 1,008 rows covering 640 affected papers. Columns: `Pair_ID`, `Year`, `Venue`, `Deprecated_Keyword`, `Sections_Hit`, `Window_Count`, `Label`, `Reasoning`. |

## Snapshot Dates

The analysis is fixed to three snapshot dates, one per input
artifact, as documented in Appendix A.1:

| Component | Snapshot date |
|---|---|
| Paper-text keyword search | 2026-01-26 |
| Deprecation registry cutoff | 2026-02-13 |
| GitHub repository keyword search and accessibility checks | 2026-02-12 |

Any deprecation announcement, paper publication, or repository state
change after these dates is not reflected in the headline figures
unless the corresponding pipeline component is re-run.

## Reproducing the Headline Figures

The supplemental material is sufficient to reproduce every
quantitative claim in the paper. The flow is:

1. Run `code/search_md_files.py` against the markdown corpus to
   produce `data/paper_text_search_results.csv`. This requires the
   markdown corpus, which is not redistributed here for size and
   licensing reasons; the search results CSV is provided as the
   canonical output.
2. Run `code/search_chatgpt_by_section.py` to produce
   `data/chatgpt_section_search.csv`.
3. Run `code/search_abstract_title.py` against
   `keywords/general_llm_terms.txt` to produce the broad-engagement
   count.
4. Run `code/extract_results.py` to compute Table 1 of the main
   paper, the deprecation impact figures, the ChatGPT-only counts,
   and the exact-vs-base reporting practice statistics.
5. Run `code/draw_stratified_sample.py` to reproduce
   `audit/audit_locked_sample.csv`. Combine with the manually
   labeled `audit/audit_labels_final.csv` and pass to
   `code/analyze_stratified_sample.py` to reproduce the audit
   results.
6. Run `code/extract_deprecation_evidence.py` to build the census
   pair list. The labeled census is in
   `census/deprecation_labels_final.csv`.

## Anonymization

The data files in this supplementary package have been anonymized
in three ways for double-blind review.

**Paper titles removed.** The `Paper_Title` column has been dropped
from `audit/audit_labels_final.csv` and
`census/deprecation_labels_final.csv`. Each row is identified by a
stable internal identifier (`Sample_ID` for the audit,
`Pair_ID` for the census) and by a venue-and-paper-id stub (e.g.,
`aaai_2023/AAAI_2023_26094` or
`iclr_2024/ICLR2024_poster_t9dWHpGkPj`) that allows reviewers to
locate the underlying paper through the conference proceedings
without exposing author identity. **Reviewers requiring the full
paper title for any specific row are welcome to reach out to the
authors after review.**

