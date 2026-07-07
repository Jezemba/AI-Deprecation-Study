#!/usr/bin/env python3
"""
Impact aggregation on the COMBINED NMI evidence set (main text + SI/appendix +
code), specific-model identifiers only. Reuses the paper's canonical deprecation
/ EXACT / BASE logic from extract_results.py.
"""
import csv, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_results as er

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
er.DEPRECATIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.pardir, "Supplementary", "keywords", "deprecation_registry.csv")
er.load_deprecation_dates()
TOTAL_CORPUS = 424  # main article PDFs processed

# deprecation lookups (identical to aggregate_MI.py)
dep_norm = {er.normalize_keyword(m): m for m in er.ALREADY_DEPRECATED}
additional = [
    "gpt-4-turbo-preview","gpt-4-turbo-preview-completions","gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k-0613","gpt-3.5-turbo-0301","text-ada-001","text-babbage-001",
    "text-curie-001","text-davinci-001","text-davinci-002","code-davinci-002",
    "text-davinci-edit-001","code-davinci-edit-001","code-davinci-001","code-cushman-002",
    "code-cushman-001","claude-1.0","claude-1.1","claude-1.2","claude-1.3",
    "claude-instant-1.0","claude-instant-1.1","claude-instant-1.2","claude-2.0","claude-2.1",
    "claude-3-sonnet-20240229","claude-3-opus-20240229","claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620","gemini-1.5-pro-001","gemini-1.5-pro-002",
    "gemini-1.5-flash-001","gemini-1.5-flash-002","gemini-1.0-pro-001","gemini-1.0-pro-002",
    "gemini-1.0-pro-vision-001","text-bison","chat-bison","code-gecko",
    "textembedding-gecko@002","textembedding-gecko@001",
]
for m in er.DEPRECATED_MODELS_LIST + additional:
    dep_norm[er.normalize_keyword(m)] = m
future_norm = {er.normalize_keyword(m): m for m in er.FUTURE_DEPRECATED
               if er.normalize_keyword(m) not in dep_norm}
exact_norm = {er.normalize_keyword(m) for m in er.EXACT_MODELS}
base_norm = {er.normalize_keyword(m) for m in er.BASE_MODELS}

rows = list(csv.DictReader(open(f"{RES}/combined_specific_model_papers.csv")))
lines = []
def out(s=""):
    lines.append(s); print(s)

out("=" * 72)
out("NMI COMBINED IMPACT (main text + SI/appendix + code; specific models only)")
out("=" * 72)
n = len(rows)
out(f"\nPapers with a specific closed-source model: {n} / {TOTAL_CORPUS} ({n/TOTAL_CORPUS*100:.1f}%)")

# by year + source
by_year = defaultdict(int)
src = Counter()
prov_papers = defaultdict(set)
kw_papers = Counter()
dep_papers = set(); fut_papers = set(); dep_by_year = defaultdict(set); dep_kw = Counter()
base_only = 0; has_exact_n = 0
for r in rows:
    art, y = r['article_id'], r['year']
    by_year[y] += 1
    if r['in_main'] == 'True': src['main'] += 1
    if r['in_SI'] == 'True': src['SI'] += 1
    if r['in_code'] == 'True': src['code'] += 1
    kws = [k for k in r['specific_keywords'].split(',') if k]
    norms = set(kws)
    for k in kws:
        kw_papers[k] += 1
        prov_papers[er.get_provider(k)].add(art)
    has_dep = any(k in dep_norm for k in norms)
    has_fut = any(k in future_norm for k in norms)
    if has_dep:
        dep_papers.add(art); dep_by_year[y].add(art)
        for k in norms:
            if k in dep_norm: dep_kw[k] += 1
    elif has_fut:
        fut_papers.add(art)
    any_exact = bool(norms & exact_norm)
    any_base = bool(norms & base_norm)
    if any_exact: has_exact_n += 1
    if any_base and not any_exact: base_only += 1

out("\n--- By year (combined) ---")
for y in sorted(by_year):
    out(f"  {y}: {by_year[y]}")
out(f"\n--- Source contribution (a paper can be in several) ---")
out(f"  main text: {src['main']}   SI/appendix: {src['SI']}   code: {src['code']}")

out("\n--- By provider (papers) ---")
for p in ['OpenAI', 'Anthropic', 'Google', 'Other']:
    if prov_papers.get(p):
        out(f"  {p}: {len(prov_papers[p])}")

out("\n--- Top models (papers) ---")
for k, c in kw_papers.most_common(15):
    out(f"  {k}: {c}")

out("\n--- DEPRECATION (combined) ---")
out(f"  Papers referencing an already-deprecated model: {len(dep_papers)} / {n}")
out(f"  Papers referencing a future-shutdown model (only): {len(fut_papers)}")
for k, c in dep_kw.most_common():
    out(f"     {k}: {c}")
out("  deprecated papers by year:")
for y in sorted(dep_by_year):
    out(f"     {y}: {len(dep_by_year[y])}")

out("\n--- UNDERREPORTING (base-only proxy) ---")
out(f"  Papers naming a versioned checkpoint: {has_exact_n}")
out(f"  Papers base-name-only (no checkpoint): {base_only} ({base_only/n*100:.1f}% of matched)")

with open(f"{RES}/COMBINED_IMPACT_SUMMARY.txt", 'w') as f:
    f.write('\n'.join(lines) + '\n')
out(f"\n[saved] {RES}/COMBINED_IMPACT_SUMMARY.txt")
