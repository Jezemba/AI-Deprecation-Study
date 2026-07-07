#!/usr/bin/env python3
"""
Focused impact aggregator for the Nature Machine Intelligence (s42256) corpus.

Reuses the paper's canonical logic from extract_results.py (get_provider,
EXACT_MODELS, BASE_MODELS, DEPRECATED_MODELS_LIST, deprecation registry) but
only consumes the automated CSV outputs (keyword search, ChatGPT-by-section,
broad title/abstract). The GitHub-repo and manual-classification inputs that the
full extract_results.py also reads are intentionally skipped for this gauge.

Journal layout adapter: papers live at
    .../MachineIntelligence/<YEAR>/s42256-*.md
so YEAR is read from the path component and VENUE is fixed to "NatMachIntell".
"""
import os
import re
import sys
import csv
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_results as er

# ---- config (CLI: search_csv [chatgpt_csv] [abstract_csv]) ----
er.DEPRECATIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.pardir, "Supplementary", "keywords", "deprecation_registry.csv")
er.load_deprecation_dates()

SEARCH_CSV = sys.argv[1] if len(sys.argv) > 1 else None
CHATGPT_CSV = sys.argv[2] if len(sys.argv) > 2 else None
ABSTRACT_CSV = sys.argv[3] if len(sys.argv) > 3 else None

YEAR_RE = re.compile(r'/(20\d{2})/')


def venue_year(filepath):
    """Journal adapter: year from the /YYYY/ path part; venue fixed."""
    m = YEAR_RE.search(filepath.replace('\\', '/'))
    year = int(m.group(1)) if m else None
    return "NatMachIntell", year


def main():
    lines = []

    def out(s=""):
        lines.append(s)
        print(s)

    # Build deprecation lookups exactly as extract_results.main() does
    deprecated_norm = {er.normalize_keyword(m): m for m in er.ALREADY_DEPRECATED}
    additional_deprecated = [
        "gpt-4-turbo-preview", "gpt-4-turbo-preview-completions",
        "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-0301",
        "text-ada-001", "text-babbage-001", "text-curie-001",
        "text-davinci-001", "text-davinci-002", "code-davinci-002",
        "text-davinci-edit-001", "code-davinci-edit-001",
        "code-davinci-001", "code-cushman-002", "code-cushman-001",
        "claude-1.0", "claude-1.1", "claude-1.2", "claude-1.3",
        "claude-instant-1.0", "claude-instant-1.1", "claude-instant-1.2",
        "claude-2.0", "claude-2.1", "claude-3-sonnet-20240229",
        "claude-3-opus-20240229", "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "gemini-1.5-pro-001", "gemini-1.5-pro-002",
        "gemini-1.5-flash-001", "gemini-1.5-flash-002",
        "gemini-1.0-pro-001", "gemini-1.0-pro-002", "gemini-1.0-pro-vision-001",
        "text-bison", "chat-bison", "code-gecko",
        "textembedding-gecko@002", "textembedding-gecko@001",
    ]
    for m in er.DEPRECATED_MODELS_LIST + additional_deprecated:
        deprecated_norm[er.normalize_keyword(m)] = m
    future_norm = {er.normalize_keyword(m): m for m in er.FUTURE_DEPRECATED
                   if er.normalize_keyword(m) not in deprecated_norm}

    exact_norm = {er.normalize_keyword(m) for m in er.EXACT_MODELS}
    base_norm = {er.normalize_keyword(m) for m in er.BASE_MODELS}

    out("=" * 80)
    out("NATURE MACHINE INTELLIGENCE (s42256) - CLOSED-SOURCE MODEL IMPACT")
    out("=" * 80)

    # ---------- SECTION 1: prevalence ----------
    total_files = 0
    files_with_matches = 0
    total_matches = 0
    kw_occ = Counter()
    kw_files = Counter()
    year_files = defaultdict(int)
    year_match_files = defaultdict(int)
    provider_files = defaultdict(set)
    provider_occ = Counter()
    file_keywords = {}
    file_year = {}

    with open(SEARCH_CSV, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            total_files += 1
            fp = row['File']
            _, year = venue_year(fp)
            file_year[fp] = year
            year_files[year] += 1
            unique_kw = int(row['Unique Keywords Found'])
            matches = int(row['Total Matches'])
            if unique_kw > 0 and matches > 0:
                files_with_matches += 1
                total_matches += matches
                year_match_files[year] += 1
                kws = [k.strip() for k in row.get('Keywords Matched', '').split(',') if k.strip()]
                file_keywords[fp] = kws
                for kw in kws:
                    kw_files[kw] += 1
                    provider_files[er.get_provider(kw)].add(fp)
                for part in row.get('Match Details', '').split(';'):
                    if ':' in part:
                        k, c = part.rsplit(':', 1)
                        try:
                            n = int(c.strip())
                        except ValueError:
                            continue
                        kw_occ[k.strip()] += n
                        provider_occ[er.get_provider(k.strip())] += n

    pct = files_with_matches / total_files * 100 if total_files else 0
    out(f"\nTotal papers processed: {total_files:,}")
    out(f"Papers referencing >=1 closed-source model: {files_with_matches:,} ({pct:.1f}%)")
    out(f"Total keyword occurrences: {total_matches:,}")

    out("\n--- Prevalence by year ---")
    for y in sorted(k for k in year_files if k):
        tf, mf = year_files[y], year_match_files.get(y, 0)
        out(f"  {y}: {mf:,} / {tf:,} papers ({(mf/tf*100 if tf else 0):.1f}%)")

    out("\n--- By provider (papers) ---")
    for p in ['OpenAI', 'Anthropic', 'Google', 'Other']:
        out(f"  {p}: {len(provider_files.get(p, set())):,} papers, {provider_occ.get(p,0):,} occurrences")

    out("\n--- Top 20 models by paper count ---")
    for kw, c in kw_files.most_common(20):
        out(f"  {kw}: {c:,} papers ({kw_occ.get(kw,0):,} occ)")

    # ---------- SECTION 5: deprecation ----------
    out("\n" + "=" * 80)
    out("DEPRECATION IMPACT")
    out("=" * 80)
    papers_dep = set()
    papers_future = set()
    dep_kw = Counter()
    dep_by_year = defaultdict(set)
    dep_by_provider = defaultdict(set)
    for fp, kws in file_keywords.items():
        y = file_year.get(fp)
        has_dep = has_fut = False
        for kw in kws:
            n = er.normalize_keyword(kw)
            if n in deprecated_norm:
                has_dep = True
                dep_kw[kw] += 1
                dep_by_provider[er.get_provider(kw)].add(fp)
            elif n in future_norm:
                has_fut = True
        if has_dep:
            papers_dep.add(fp)
            if y:
                dep_by_year[y].add(fp)
        elif has_fut:
            papers_future.add(fp)

    out(f"\nPapers referencing an ALREADY-deprecated model: {len(papers_dep):,} / {files_with_matches:,} matched")
    out(f"Papers referencing a FUTURE-shutdown model (only): {len(papers_future):,}")
    out(f"Unique deprecated model names found: {len(dep_kw)}")
    out("\n--- Top deprecated models ---")
    for kw, c in dep_kw.most_common(15):
        out(f"  {kw}: {c:,} papers")
    out("\n--- Deprecated papers by year ---")
    for y in sorted(dep_by_year):
        mf = year_match_files.get(y, 0)
        out(f"  {y}: {len(dep_by_year[y]):,} / {mf:,} matched ({(len(dep_by_year[y])/mf*100 if mf else 0):.1f}%)")
    out("\n--- Deprecated papers by provider ---")
    for p in ['OpenAI', 'Anthropic', 'Google', 'Other']:
        c = len(dep_by_provider.get(p, set()))
        if c:
            out(f"  {p}: {c:,}")

    # ---------- base-only underreporting proxy ----------
    out("\n" + "=" * 80)
    out("UNDERREPORTING (base-only proxy: names a base model but NO versioned checkpoint)")
    out("=" * 80)
    base_only = 0
    has_exact = 0
    for fp, kws in file_keywords.items():
        norms = {er.normalize_keyword(k) for k in kws}
        any_exact = bool(norms & exact_norm)
        any_base = bool(norms & base_norm)
        if any_exact:
            has_exact += 1
        if any_base and not any_exact:
            base_only += 1
    out(f"\nMatched papers naming a versioned/exact checkpoint: {has_exact:,}")
    out(f"Matched papers with base-name only (no checkpoint): {base_only:,} "
        f"({(base_only/files_with_matches*100 if files_with_matches else 0):.1f}% of matched)")

    # ---------- ChatGPT underreporting (optional) ----------
    if CHATGPT_CSV and os.path.exists(CHATGPT_CSV):
        out("\n" + "=" * 80)
        out("CHATGPT MENTIONS (section-aware)")
        out("=" * 80)
        cg_files = 0
        cg_match = 0
        cg_by_year = defaultdict(int)
        with open(CHATGPT_CSV, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                cg_files += 1
                if int(row.get('Total Matches', 0) or 0) > 0:
                    cg_match += 1
                    _, y = venue_year(row['File'])
                    if y:
                        cg_by_year[y] += 1
        out(f"\nPapers mentioning 'ChatGPT': {cg_match:,} / {cg_files:,}")
        for y in sorted(cg_by_year):
            out(f"  {y}: {cg_by_year[y]:,}")

    # ---------- broad LLM engagement (optional) ----------
    if ABSTRACT_CSV and os.path.exists(ABSTRACT_CSV):
        out("\n" + "=" * 80)
        out("BROAD LLM/VLM ENGAGEMENT (title + abstract)")
        out("=" * 80)
        ab_files = 0
        ab_match = 0
        with open(ABSTRACT_CSV, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                ab_files += 1
                tm = row.get('Total Matches') or row.get('total_matches') or 0
                try:
                    if int(tm) > 0:
                        ab_match += 1
                except ValueError:
                    pass
        out(f"\nPapers engaging LLM/VLM topics in title/abstract: {ab_match:,} / {ab_files:,} "
            f"({(ab_match/ab_files*100 if ab_files else 0):.1f}%)")

    # save
    outpath = os.path.join(os.path.dirname(SEARCH_CSV), "IMPACT_SUMMARY.txt")
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"\n[saved] {outpath}")


if __name__ == "__main__":
    if not SEARCH_CSV:
        print("usage: aggregate_MI.py <search_results.csv> [chatgpt_section.csv] [abstract_title.csv]")
        sys.exit(1)
    main()
