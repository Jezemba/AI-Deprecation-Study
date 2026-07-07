# Nature Machine Intelligence Cross-Check

This directory applies the deprecation analysis pipeline to a journal venue,
*Nature Machine Intelligence* (NMI, DOI prefix `s42256`), covering all articles
published from 2022 to 2025. It serves as an external-validity check on the
conference analysis in the [`Supplementary/`](../Supplementary) directory:
does the pattern of closed-source model reliance and deprecation-driven
irreproducibility hold outside the four major ML conferences?

Unlike conference proceedings, where appendices and code are embedded in or
linked from the main paper, NMI publishes supplementary information and code as
separate files. The analysis therefore extends the search to three sources per
article: the **main text**, the **supplementary PDFs**, and the **supplementary
code**, and combines them per article.

All headline figures count **specific** closed-source model identifiers and
exclude the six generic interface terms (`ChatGPT`, `Claude`, `Gemini`,
`OpenAI`, `Anthropic`, `Google`), which in this corpus are dominated by author
affiliations and software imports rather than model usage.

## Headline result

| Metric | Value |
|---|---|
| Articles collected (2022-2025) | 439 |
| Articles successfully converted | 424 (96.6%) |
| Articles referencing a specific closed-source model (combined) | **42 / 424 (9.9%)** |
| from main text | 35 |
| added by supplementary PDFs | +6 |
| added by supplementary code | +1 |
| Articles referencing an already-deprecated model | 6 |
| Articles naming only a base model (no dated checkpoint) | 20 (48% of matched) |

Combined prevalence by year: 2.2% (2022), 9.9% (2023), 6.4% (2024), 18.5% (2025),
tracking the conference trend and rising toward the conference 2025 figure.

## Directory Layout

```
Nature_Machine_Intelligence/
├── keywords/   (model identifier list and broad-term list)
├── code/       (extraction, search, aggregation, and figure scripts)
├── data/       (per-source search results, combined table, impact summaries, corpus provenance)
└── figures/    (cross-check figure used in the paper, plus analysis dashboards)
```

## File Index

### keywords/

| File | Description |
|---|---|
| `keywords_union.txt` | The 248 closed-source model identifiers searched, the deduplicated union of `keywords_active.txt` and `keywords_updated.txt` from `../Supplementary/keywords/`. Includes base names and versioned checkpoints across OpenAI, Anthropic, and Google. |
| `general_llm_terms.txt` | The broad LLM/VLM term list used for the title-and-abstract engagement search (same list as the conference analysis). |

### code/

| File | Description |
|---|---|
| `extract_pdfs.py` | Docling PDF-to-Markdown extraction, used for both the 424 article PDFs and the 454 supplementary PDFs. Preserves section boundaries for references-section exclusion. |
| `reassemble.py` | Reassembles and checksum-verifies the split supplementary-material archives retrieved from the publisher, then extracts them. |
| `text_utils.py`, `md_processor.py` | Shared keyword-search engine: normalization, references-section exclusion, compound-token exclusion, and o1/o3 disambiguation (identical to the conference `Supplementary/code/`). |
| `search_md_files.py` | Runs the 248-identifier keyword search over the Markdown; used for both main text and supplementary PDFs. |
| `search_chatgpt_by_section.py` | Section-aware search for ``ChatGPT'' mentions. |
| `search_abstract_title.py` | Title-and-abstract broad LLM/VLM engagement search. |
| `search_code_apparatus.py` | Repository-analysis equivalent for the supplementary code: walks every ASCII-readable file and matches identifiers with the same engine used for GitHub repositories in the conference analysis. |
| `combine_MI_sources.py` | Combines main-text, supplementary-PDF, and code matches per article; separates specific identifiers from generic interface terms. Produces `data/combined_specific_model_papers.csv`. |
| `aggregate_MI.py` | Main-text impact aggregation (prevalence, providers, top models, deprecation, base-only). Reuses the canonical deprecation logic from `extract_results.py`. |
| `aggregate_combined.py` | Combined impact aggregation across all three sources. Produces `data/impact_summary_combined.txt`. |
| `extract_results.py` | Canonical model-classification and deprecation-registry logic imported by the aggregation scripts (from the conference analysis). |
| `make_charts.py` | Renders the analysis dashboard PNGs in `figures/`. |
| `make_nmi_figure.py` | Renders the two-panel cross-check figure (`figures/NMI_crosscheck.*`) used in the paper. |

### data/

| File | Description |
|---|---|
| `paper_text_search_results.csv` | Keyword search results over the 424 article main texts (one row per article). |
| `si_text_search_results.csv` | Keyword search results over the 454 supplementary PDFs (one row per supplementary document). |
| `code_search_results.csv` | Keyword search results over the 13 supplementary code bundles (one row per article's code). |
| `chatgpt_section_search.csv` | Section-level breakdown of ``ChatGPT'' mentions. |
| `abstract_title_search.csv` | Broad LLM/VLM engagement search over titles and abstracts. |
| `combined_specific_model_papers.csv` | The 42 matched articles with per-article flags for whether the model appears in main text, supplementary PDF, and/or code, plus the specific identifiers found. |
| `impact_summary_combined.txt` | Human-readable combined-impact summary (prevalence, by year, providers, top models, deprecation, base-only). |
| `impact_summary_maintext.txt` | Human-readable main-text-only impact summary. |
| `article_inventory.csv` | Every NMI article page checked during collection. |
| `code_inventory.csv` | The 13 supplementary assets classified as code/software. |
| `classification_summary.csv` | Counts of retrieved supplementary assets by category (code, source data, video, etc.). |
| `manifest.csv`, `chunk_manifest.csv`, `README_reassembly.txt` | Provenance for the retrieved supplementary materials and the split-archive reassembly. |

### figures/

| File | Description |
|---|---|
| `NMI_crosscheck.pdf` / `.svg` / `_preview.png` | Two-panel cross-check figure used in the paper: (A) prevalence by year with main-text vs supplementary contribution; (B) reproducibility risk by year with deprecated-model and base-name-only decomposition. |
| `0_NMI_dashboard.png` and `1` through `4_*.png` | Analysis dashboard panels (adoption trend, source contribution, absolute-scale comparison to conferences, reproducibility risk). |

## Snapshot Dates

| Component | Date |
|---|---|
| Article and supplementary-PDF Markdown extraction | 2026-06-22 to 2026-06-26 |
| Deprecation registry cutoff | 2026-02-13 (same registry as the conference analysis) |

## Reproducing the Figures

1. Convert the article and supplementary PDFs to Markdown with `code/extract_pdfs.py`
   (the raw PDFs are not redistributed here for size and licensing reasons; the
   search-result CSVs are provided as the canonical output).
2. Run `code/search_md_files.py` over the article Markdown and again over the
   supplementary-PDF Markdown to produce `paper_text_search_results.csv` and
   `si_text_search_results.csv`.
3. Run `code/search_code_apparatus.py` over the extracted code to produce
   `code_search_results.csv`.
4. Run `code/combine_MI_sources.py` to produce `combined_specific_model_papers.csv`,
   then `code/aggregate_combined.py` for the impact summary.
5. Run `code/make_nmi_figure.py` to render the cross-check figure.

## Scope and Caveats

- **Small n.** Because the venue publishes on the order of one hundred articles
  per year, the matched counts (42 articles, 6 deprecated) are small. They
  support a consistency check but not the stratified audit or manual census
  conducted for the conference corpus, so those `audit/` and `census/` folders
  have no counterpart here.
- **Generic-term inflation.** Counting the six generic interface terms would
  raise apparent prevalence from 9.9% to 18.6%; this is treated as spurious.
- **Coverage.** 15 of 439 article PDFs (mostly 2025) did not convert and are
  excluded, slightly understating the most recent year.

## Running the code

All scripts resolve paths relative to their own location, so the code runs from a
clone on any machine with no edits. Reproduction consumes the provided CSVs in
`data/` and the shared deprecation registry in
`../Supplementary/keywords/deprecation_registry.csv`.

To re-run the pipeline from raw PDFs (which are not redistributed here for size
and licensing reasons), place the extracted article and supplementary-PDF
Markdown under `markdown/` and the extracted supplementary code under
`code_apparatus/` inside this folder. The search scripts default to those input
locations and write their outputs to `data/` (`search_md_files.py` and
`search_code_apparatus.py` also accept an explicit input path as their first
argument); the figure scripts write to `figures/`.
