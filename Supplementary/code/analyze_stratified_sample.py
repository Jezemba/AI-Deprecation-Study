#!/usr/bin/env python3
"""
Inference for the stratified-audit sample.

Reads the labeled stratified-sample CSV and produces:
- corpus-level marginal estimates of each label class (4 classes)
- a "substantive" headline number (Methods + Methods and Evaluation)
- year-stratified and venue-stratified subgroup estimates
- per-keyword estimates for the top sampled keywords
- 95% confidence intervals via stratified bootstrap (10,000 resamples)
- with and without finite-population correction

Usage
-----
    python analyze_stratified_sample.py [labeled.csv] [output_dir]

Default labeled CSV path is `stratified_sample_v1_labeled.csv` next to
the locked sample. If that file does not exist yet, the script falls
back to the locked sample (which has empty Labels) and prints what the
analysis would look like once labeling is complete.
"""
import csv
import os
import sys
import math
import random
import statistics
from collections import defaultdict, Counter

csv.field_size_limit(sys.maxsize)

DEFAULT_LABELED = "<results>/stratified_sample_v1_labeled.csv"
LOCKED_SAMPLE   = "<results>/stratified_sample_v1.csv"
DEFAULT_OUT_DIR = "<analysis>/results"
SEED = 42
N_BOOTSTRAP = 10000
CLASSES = ['Methods', 'Evaluation', 'Methods and Evaluation', 'N/A']
SUBSTANTIVE = {'Methods', 'Methods and Evaluation'}


def load_labeled(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            r['Stratum_Population_Size'] = int(r['Stratum_Population_Size'])
            r['Stratum_Sample_Size'] = int(r['Stratum_Sample_Size'])
            r['Inclusion_Probability'] = float(r['Inclusion_Probability'])
            r['Weight'] = float(r['Weight'])
            rows.append(r)
    return rows


def stratified_estimate(rows, predicate):
    """Population-weighted proportion of rows where predicate(row) is True."""
    total_pop = sum(r['Stratum_Population_Size'] for r in
                    {r['Stratum']: r for r in rows}.values())
    by_stratum = defaultdict(list)
    for r in rows:
        by_stratum[r['Stratum']].append(r)
    weighted_sum = 0.0
    for stratum, rs in by_stratum.items():
        N_h = rs[0]['Stratum_Population_Size']
        n_h = len(rs)
        if n_h == 0:
            continue
        p_h = sum(1 for r in rs if predicate(r)) / n_h
        weighted_sum += N_h * p_h
    return weighted_sum / total_pop


def stratified_bootstrap(rows, predicate, B=N_BOOTSTRAP, seed=SEED, fpc=False):
    """Resample within each stratum with replacement, return (low, high)."""
    rng = random.Random(seed)
    by_stratum = defaultdict(list)
    for r in rows:
        by_stratum[r['Stratum']].append(r)
    total_pop = sum(rs[0]['Stratum_Population_Size'] for rs in by_stratum.values())

    estimates = []
    for _ in range(B):
        ws = 0.0
        for stratum, rs in by_stratum.items():
            N_h = rs[0]['Stratum_Population_Size']
            n_h = len(rs)
            resampled = [rs[rng.randrange(n_h)] for _ in range(n_h)]
            p_h = sum(1 for r in resampled if predicate(r)) / n_h
            ws += N_h * p_h
        estimate = ws / total_pop
        estimates.append(estimate)

    estimates.sort()
    low = estimates[int(0.025 * B)]
    high = estimates[int(0.975 * B)]
    if fpc:
        # FPC tightens the CI by sqrt(1 - n/N)
        point = stratified_estimate(rows, predicate)
        n = sum(len(rs) for rs in by_stratum.values())
        N = total_pop
        fpc_factor = math.sqrt(max(0.0, 1 - n / N))
        low = point - (point - low) * fpc_factor
        high = point + (high - point) * fpc_factor
    return low, high


def report_section(rows, title, predicates):
    """Print one section: a list of (label, predicate) with point + CI."""
    out = []
    out.append("=" * 78)
    out.append(title)
    out.append("=" * 78)
    out.append(f"{'Label':<28} {'Point':>8} {'CI Lo':>8} {'CI Hi':>8} {'CI Lo (FPC)':>12} {'CI Hi (FPC)':>12}")
    for label, pred in predicates:
        p = stratified_estimate(rows, pred)
        low, high = stratified_bootstrap(rows, pred, fpc=False)
        low_f, high_f = stratified_bootstrap(rows, pred, fpc=True)
        out.append(f"{label:<28} {p*100:>7.1f}% {low*100:>7.1f}% {high*100:>7.1f}% "
                   f"{low_f*100:>11.1f}% {high_f*100:>11.1f}%")
    return '\n'.join(out)


def main():
    labeled_csv = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LABELED
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    if not os.path.exists(labeled_csv):
        print(f"Labeled file not found: {labeled_csv}")
        print(f"Falling back to locked sample (will report 0% for all classes "
              f"because Labels are blank pre-labeling).")
        labeled_csv = LOCKED_SAMPLE

    rows = load_labeled(labeled_csv)
    print(f"Loaded {len(rows)} rows from {labeled_csv}")
    labeled_rows = [r for r in rows if r.get('Label', '').strip()]
    blank = len(rows) - len(labeled_rows)
    print(f"  {len(labeled_rows)} have non-blank Label; {blank} are unlabeled")

    if blank > 0:
        print(f"\nWARNING: {blank} rows are unlabeled. The reported numbers are "
              f"only correct once all 1,000 rows have a Label.")

    out_lines = []
    out_lines.append(f"STRATIFIED AUDIT RESULTS")
    out_lines.append(f"Source: {labeled_csv}")
    out_lines.append(f"Total rows: {len(rows)} (labeled: {len(labeled_rows)})")
    out_lines.append(f"Bootstrap resamples: {N_BOOTSTRAP}, seed: {SEED}")
    out_lines.append("")

    # Headline: substantive
    preds_main = [
        ('Methods or Meth+Eval (Substantive)',
         lambda r: r['Label'].strip() in SUBSTANTIVE),
        ('Methods (only)',
         lambda r: r['Label'].strip() == 'Methods'),
        ('Evaluation (only)',
         lambda r: r['Label'].strip() == 'Evaluation'),
        ('Methods and Evaluation',
         lambda r: r['Label'].strip() == 'Methods and Evaluation'),
        ('N/A',
         lambda r: r['Label'].strip() == 'N/A'),
    ]
    out_lines.append(report_section(labeled_rows or rows,
                                    "OVERALL CORPUS-LEVEL ESTIMATES (95% CI)",
                                    preds_main))

    # Per year
    out_lines.append("\n")
    by_year = defaultdict(list)
    for r in (labeled_rows or rows):
        by_year[r['Year']].append(r)
    for year in sorted(by_year):
        out_lines.append(report_section(by_year[year],
                                        f"YEAR {year} (n={len(by_year[year])})",
                                        preds_main))
        out_lines.append("")

    # Per venue
    by_venue = defaultdict(list)
    for r in (labeled_rows or rows):
        by_venue[r['Venue']].append(r)
    for venue in sorted(by_venue):
        out_lines.append(report_section(by_venue[venue],
                                        f"VENUE {venue.upper()} (n={len(by_venue[venue])})",
                                        preds_main))
        out_lines.append("")

    out_text = '\n'.join(out_lines)
    out_path = os.path.join(out_dir, "stratified_audit_results.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(out_text)
    print(out_text)
    print(f"\nWrote {out_path}")


if __name__ == '__main__':
    main()
