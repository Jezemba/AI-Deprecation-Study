# AI Deprecation Study

Data and code accompanying the paper **"Closed-Source Model Deprecation Policies
Should Prioritize Scientific Reproducibility."**

The study quantifies how much published machine learning research depends on
closed-source models from OpenAI, Anthropic, and Google, and how much of that
research has already become non-reproducible because the models it relies on have
been deprecated. Closed-source model references are extracted from paper text,
linked code, and supplementary material, classified by usage context, and
cross-referenced against official provider deprecation schedules.

## Repository structure

| Directory | Corpus | Summary |
|---|---|---|
| [`Supplementary/`](Supplementary) | 42,384 papers at AAAI, NeurIPS, ICLR, and ICML (2022-2025) | Primary analysis. Keyword lists, deprecation registry, search and inference code, canonical result tables, the stratified usage audit, and the complete manual deprecation census. |
| [`Nature Machine Intelligence/`](Nature%20Machine%20Intelligence) | 439 *Nature Machine Intelligence* articles (2022-2025) | Journal cross-check. Applies the same pipeline to a journal venue, extending the search to separately published supplementary PDFs and code. |

Each directory has its own `README.md` documenting every file.

## Headline findings

**Conferences (primary corpus).** 4,817 of 42,384 papers (11.4%) reference a
closed-source model; usage grows from 0.1% of papers in 2022 to 20.1% in 2025.
640 papers reference a model that has already been shut down, and 3,021 papers
(7.1%) are directly non-reproducible through deprecation, ChatGPT-only reporting,
or base-name-only reporting without a recoverable checkpoint.

**Nature Machine Intelligence (cross-check).** Combining main text, supplementary
PDFs, and supplementary code, 42 of 424 converted articles (9.9%) reference a
specific closed-source model, rising from 2.2% in 2022 to 18.5% in 2025, with 6
articles referencing an already-deprecated model. The supplementary material
alone surfaces 7 of the 42 matched articles, confirming that the pattern is not
specific to conferences.

## Method (shared pipeline)

1. Collect all papers/articles and convert them to Markdown with
   [Docling](https://github.com/DS4SD/docling), preserving section boundaries.
2. Search the text (references section excluded) for 248 closed-source model
   identifiers, with compound-token and mathematical-notation filtering.
3. For code, walk every ASCII-readable file in the linked repositories or
   supplementary code and match the same identifiers.
4. Classify usage context (methodology vs evaluation) and cross-reference every
   detected model against a deprecation registry frozen at 2026-02-13.

## Citation

If you use this data or code, please cite the accompanying paper. See each
subdirectory's `README.md` for file-level detail and reproduction steps.

## License

See [`LICENSE`](LICENSE).
