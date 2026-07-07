#!/usr/bin/env python3
"""
Combine the three NMI evidence sources per paper:
  - main text   (search_results_*.csv over the 424 article PDFs)
  - SI/appendix (SI/search_results_*.csv over the 454 supplementary PDFs)
  - code        (code_apparatus_search.csv over the 13 code bundles)

Reports, per source and combined: papers referencing a SPECIFIC closed-source
model (generic company/interface terms excluded), and what the SI + code surface
that the main text alone missed.
"""
import csv, glob, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_results as er

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
GENERIC = {er.normalize_keyword(t) for t in ['chatgpt', 'claude', 'gemini', 'openai', 'anthropic', 'google']}
YEAR_RE = re.compile(r'/(20\d{2})/')


def latest(pat):
    fs = sorted(glob.glob(pat))
    return fs[-1] if fs else None


def specific_kws(kw_csv_field):
    out = set()
    for k in kw_csv_field.split(','):
        k = k.strip()
        if not k:
            continue
        n = er.normalize_keyword(k)
        if n and n not in GENERIC:
            out.add(n)
    return out


def art_from_path(p):
    """article_id = filename stem for main; parent dir for SI."""
    stem = os.path.splitext(os.path.basename(p))[0]
    if stem.startswith('s42256'):
        return stem
    return os.path.basename(os.path.dirname(p))


def year_of(art, fallback_path=''):
    m = YEAR_RE.search(fallback_path)
    if m:
        return m.group(1)
    mm = re.search(r's42256-(\d{2})', art)  # publication year prefix is unreliable; prefer path
    return None


# ---- main text ----
main_spec = {}      # article -> set(specific kw)
main_year = {}
with open(os.path.join(RES, "paper_text_search_results.csv")) as f:
    for r in csv.DictReader(f):
        art = art_from_path(r['File'])
        y = (YEAR_RE.search(r['File']) or [None, None])[1]
        main_year[art] = y
        s = specific_kws(r.get('Keywords Matched', ''))
        if s:
            main_spec[art] = s

# ---- SI ----
si_spec = {}
si_year = {}
with open(os.path.join(RES, "si_text_search_results.csv")) as f:
    for r in csv.DictReader(f):
        art = art_from_path(r['File'])
        y = (YEAR_RE.search(r['File']) or [None, None])[1]
        si_year[art] = y
        s = specific_kws(r.get('Keywords Matched', ''))
        if s:
            si_spec[art] = s

# ---- code ----
code_spec = {}
code_year = {}
with open(os.path.join(RES, "code_search_results.csv")) as f:
    for r in csv.DictReader(f):
        art = r['article_id']
        code_year[art] = r['year']
        s = specific_kws(r.get('keywords_found', ''))
        if s:
            code_spec[art] = s

yr_of = {**si_year, **code_year, **main_year}

# ---- combine ----
all_arts = set(main_spec) | set(si_spec) | set(code_spec)
print("=" * 70)
print("NMI SPECIFIC-MODEL REFERENCES BY SOURCE (generic company terms excluded)")
print("=" * 70)
print(f"  main text  : {len(main_spec)} papers")
print(f"  SI/appendix: {len(si_spec)} papers")
print(f"  code       : {len(code_spec)} papers")

si_new = set(si_spec) - set(main_spec)
code_new = set(code_spec) - set(main_spec) - set(si_spec)
combined = all_arts
print(f"\n  SI surfaces NEW papers not in main text: {len(si_new)}")
for a in sorted(si_new):
    print(f"      {a}: {sorted(si_spec[a])}")
print(f"  code surfaces NEW papers not in main/SI: {len(code_new)}")
for a in sorted(code_new):
    print(f"      {a}: {sorted(code_spec[a])}")

print(f"\n  COMBINED unique papers w/ specific model (main ∪ SI ∪ code): {len(combined)}")

# by year
by_year = defaultdict(lambda: [0, 0, 0, 0])  # main, +si, +code, combined
for a in combined:
    y = yr_of.get(a) or '?'
    if a in main_spec: by_year[y][0] += 1
    if a in si_new: by_year[y][1] += 1
    if a in code_new: by_year[y][2] += 1
    by_year[y][3] += 1
print("\n  By year (main / +SI-new / +code-new / combined):")
for y in sorted(k for k in by_year if k != '?'):
    m, s, c, t = by_year[y]
    print(f"      {y}: {m} / +{s} / +{c} / {t}")

# write combined per-paper csv
out = os.path.join(RES, "combined_specific_model_papers.csv")
with open(out, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['article_id', 'year', 'in_main', 'in_SI', 'in_code', 'specific_keywords'])
    for a in sorted(combined):
        kws = sorted(set().union(main_spec.get(a, set()), si_spec.get(a, set()), code_spec.get(a, set())))
        w.writerow([a, yr_of.get(a, ''), a in main_spec, a in si_spec, a in code_spec, ','.join(kws)])
print(f"\n[saved] {out}")
