#!/usr/bin/env python3
"""
Draw a stratified random sample of 1,000 papers from the 4,817 matched
papers for a corpus-level usage-context audit. Sampling is paper-level,
stratified by (year x venue), with proportional allocation and a 10-paper
floor per non-empty stratum.

For each sampled paper we also randomly select ONE keyword from the
paper's set of matched keywords. The labeler will read all windows of
that keyword in the paper and assign one of {Methods, Evaluation,
Methods and Evaluation, N/A} at the paper-keyword level (Option A from
the proposal).

Inputs
------
- PDFAnalysis/results/search_results_20260126_164130.csv

Outputs
-------
- PDFAnalysis/results/stratified_sample_v1.csv   -- the locked sample
- PDFAnalysis/results/stratified_sample_v1_summary.txt -- audit trail

Reproducibility
---------------
Seed 42. Re-running this script reproduces the same sample bit-for-bit.
"""
import csv
import os
import re
import sys
import random
from collections import defaultdict, Counter
from pathlib import Path

csv.field_size_limit(sys.maxsize)


SEARCH_CSV   = "<results>/search_results_20260126_164130.csv"
OUT_CSV      = "<results>/stratified_sample_v1.csv"
OUT_SUMMARY  = "<results>/stratified_sample_v1_summary.txt"

SEED = 42
TARGET_N = 1000
PER_STRATUM_FLOOR = 10
VENUES = ('aaai', 'iclr', 'icml', 'neurips')
YEAR_VENUE_RE = re.compile(r'/((?:aaai|iclr|icml|neurips))_(\d{4})/', re.IGNORECASE)


def load_matched_papers(search_csv):
    """Return list of dicts with file, year, venue, keywords (as list of strings)."""
    papers = []
    with open(search_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row.get('Total Matches', 0) or 0) == 0:
                continue
            m = YEAR_VENUE_RE.search(row['File'])
            if not m:
                continue
            venue = m.group(1).lower()
            year = m.group(2)
            kws = [k.strip() for k in row.get('Keywords Matched', '').split(',') if k.strip()]
            papers.append({
                'file': row['File'],
                'year': year,
                'venue': venue,
                'keywords': kws,
                'total_matches': int(row['Total Matches']),
            })
    return papers


def proportional_allocation(strata_counts, target_n, floor):
    """Allocate target_n across strata in proportion to size, with min `floor`."""
    total = sum(strata_counts.values())
    raw = {s: target_n * n / total for s, n in strata_counts.items()}
    alloc = {s: max(floor, int(round(raw[s]))) for s in strata_counts}
    # Cap by population
    for s, n in alloc.items():
        alloc[s] = min(alloc[s], strata_counts[s])
    # Adjust to target if over/under
    diff = target_n - sum(alloc.values())
    if diff != 0:
        # Allocate residual to the largest strata (with room) one at a time
        order = sorted(strata_counts.keys(),
                       key=lambda s: (strata_counts[s], s),
                       reverse=(diff > 0))
        i = 0
        while diff != 0 and i < len(order) * 10:
            s = order[i % len(order)]
            if diff > 0 and alloc[s] < strata_counts[s]:
                alloc[s] += 1
                diff -= 1
            elif diff < 0 and alloc[s] > floor and alloc[s] > 0:
                alloc[s] -= 1
                diff += 1
            i += 1
    return alloc


def main():
    rng = random.Random(SEED)

    print(f"Loading matched papers from {SEARCH_CSV}...")
    papers = load_matched_papers(SEARCH_CSV)
    print(f"  matched papers (stratum-resolvable): {len(papers)}")

    # Group into strata
    strata = defaultdict(list)
    for p in papers:
        strata[(p['year'], p['venue'])].append(p)
    strata_sizes = {s: len(ps) for s, ps in strata.items()}

    print("\nStratum sizes (year x venue):")
    for year in sorted({y for y, _ in strata_sizes.keys()}):
        line = f"  {year}: "
        for venue in VENUES:
            n = strata_sizes.get((year, venue), 0)
            line += f" {venue}={n:>5}"
        line += f"  total={sum(v for (y, _), v in strata_sizes.items() if y == year)}"
        print(line)

    alloc = proportional_allocation(strata_sizes, TARGET_N, PER_STRATUM_FLOOR)
    print(f"\nAllocation (target {TARGET_N}, floor {PER_STRATUM_FLOOR}):")
    print(f"  total allocated: {sum(alloc.values())}")
    for year in sorted({y for y, _ in alloc.keys()}):
        line = f"  {year}: "
        for venue in VENUES:
            line += f" {venue}={alloc.get((year, venue), 0):>4}"
        line += f"  total={sum(v for (y, _), v in alloc.items() if y == year)}"
        print(line)

    # Draw sample
    print("\nDrawing stratified sample...")
    sample_rows = []
    for stratum, n_h in alloc.items():
        pool = strata[stratum]
        picked = rng.sample(pool, k=n_h)
        for paper in picked:
            kw = rng.choice(paper['keywords'])
            sample_rows.append({
                'File_Path': paper['file'],
                'Year': paper['year'],
                'Venue': paper['venue'],
                'Stratum': f"{paper['year']}-{paper['venue']}",
                'Stratum_Population_Size': strata_sizes[stratum],
                'Stratum_Sample_Size': n_h,
                'Inclusion_Probability': n_h / strata_sizes[stratum],
                'Weight': strata_sizes[stratum] / n_h,
                'Sampled_Keyword': kw,
                'All_Keywords_Matched': ', '.join(paper['keywords']),
                'Total_Matches_In_Paper': paper['total_matches'],
            })

    # Sort deterministically
    sample_rows.sort(key=lambda r: (r['Year'], r['Venue'], r['File_Path']))
    for i, row in enumerate(sample_rows, start=1):
        row['Sample_ID'] = f"S{i:04d}"

    # Reorder columns
    out_fields = [
        'Sample_ID', 'Year', 'Venue', 'Stratum',
        'Stratum_Population_Size', 'Stratum_Sample_Size',
        'Inclusion_Probability', 'Weight',
        'Sampled_Keyword', 'All_Keywords_Matched',
        'Total_Matches_In_Paper', 'File_Path',
        'Label', 'Notes', 'Reviewer',  # blank columns for the labeler
    ]

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in sample_rows:
            row['Label'] = ''
            row['Notes'] = ''
            row['Reviewer'] = ''
            writer.writerow(row)

    print(f"\nWrote {OUT_CSV} ({len(sample_rows)} rows)")

    # Write a human-readable audit trail summary
    with open(OUT_SUMMARY, 'w', encoding='utf-8') as f:
        f.write("STRATIFIED SAMPLE v1 - AUDIT TRAIL\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Source: {SEARCH_CSV}\n")
        f.write(f"Random seed: {SEED}\n")
        f.write(f"Target sample size: {TARGET_N}\n")
        f.write(f"Per-stratum floor: {PER_STRATUM_FLOOR}\n")
        f.write(f"Stratification: year x venue\n")
        f.write(f"Sampling unit: paper, with one randomly chosen keyword per paper\n\n")
        f.write(f"Universe: {len(papers)} matched papers across {len(strata)} non-empty strata\n\n")

        f.write("Strata population vs. sample (proportional allocation):\n")
        f.write(f"{'Stratum':<14} {'Pop':>6} {'Sample':>8} {'Pi':>9} {'Weight':>10}\n")
        for stratum in sorted(strata_sizes.keys()):
            year, venue = stratum
            pop = strata_sizes[stratum]
            n_h = alloc[stratum]
            pi = n_h / pop
            w = 1 / pi if pi > 0 else 0
            f.write(f"{year}-{venue:<8} {pop:>6} {n_h:>8} {pi:>8.4f} {w:>10.2f}\n")
        f.write(f"{'TOTAL':<14} {sum(strata_sizes.values()):>6} "
                f"{sum(alloc.values()):>8}\n\n")

        # Sample distribution by year and venue
        f.write("Sample distribution (sanity check):\n")
        sample_strata = Counter((r['Year'], r['Venue']) for r in sample_rows)
        f.write(f"{'Stratum':<14} {'Count':>6} {'Pop %':>7} {'Sample %':>10}\n")
        total_pop = sum(strata_sizes.values())
        total_sample = sum(sample_strata.values())
        for stratum in sorted(sample_strata.keys()):
            year, venue = stratum
            f.write(f"{year}-{venue:<8} {sample_strata[stratum]:>6} "
                    f"{strata_sizes[stratum]/total_pop*100:>6.1f}% "
                    f"{sample_strata[stratum]/total_sample*100:>9.1f}%\n")

        # Keyword distribution in the sample
        f.write("\nSampled keyword frequency (top 20):\n")
        kw_counts = Counter(r['Sampled_Keyword'] for r in sample_rows)
        for kw, c in kw_counts.most_common(20):
            f.write(f"  {kw:<30} {c:>4}\n")
        f.write(f"\n  unique keywords sampled: {len(kw_counts)}\n")

    print(f"Wrote {OUT_SUMMARY}\n")


if __name__ == '__main__':
    main()
