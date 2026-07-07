#!/usr/bin/env python3
"""
Search for 'ChatGPT' mentions in markdown files, broken down by paper section.
Case-insensitive search.
"""
import os
import re
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from multiprocessing import Pool, cpu_count
from collections import defaultdict


# Section categories and their matching patterns
SECTION_PATTERNS = {
    'abstract': [r'abstract'],
    'introduction': [r'introduction', r'intro\b'],
    'related_work': [r'related\s*work', r'background', r'literature\s*review', r'prior\s*work'],
    'methods': [r'method', r'approach', r'model', r'framework', r'architecture', r'technique',
                r'algorithm', r'implementation', r'system\s*design', r'proposed'],
    'experiments': [r'experiment', r'setup', r'setting', r'dataset', r'data\s*collection',
                    r'benchmark', r'baseline'],
    'results': [r'result', r'evaluation', r'performance', r'analysis', r'finding',
                r'comparison', r'ablation', r'discussion'],
    'conclusion': [r'conclusion', r'summary', r'future\s*work', r'limitation'],
    'acknowledgements': [r'acknowledge?ment'],
    'appendix': [r'appendix', r'supplement'],
    'references': [r'reference', r'bibliography'],
}


def categorize_section(section_title: str) -> str:
    """
    Categorize a section title into a standard category.

    Args:
        section_title: The section header text

    Returns:
        Category name or 'other' if no match
    """
    title_lower = section_title.lower().strip()

    for category, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title_lower):
                return category

    return 'other'


def parse_sections(text: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Parse markdown text into sections.

    Args:
        text: Full markdown text

    Returns:
        Dictionary mapping category to list of (section_title, section_content) tuples
    """
    sections = defaultdict(list)

    # Split by section headers (## or #)
    # Pattern matches markdown headers
    header_pattern = r'^(#{1,3})\s+(.+?)$'

    lines = text.split('\n')
    current_section = 'preamble'
    current_content = []
    current_title = ''

    for line in lines:
        match = re.match(header_pattern, line)
        if match:
            # Save previous section
            if current_content:
                category = categorize_section(current_title) if current_title else 'other'
                content_text = '\n'.join(current_content)
                sections[category].append((current_title, content_text))

            # Start new section
            current_title = match.group(2)
            current_content = []
        else:
            current_content.append(line)

    # Don't forget the last section
    if current_content:
        category = categorize_section(current_title) if current_title else 'other'
        content_text = '\n'.join(current_content)
        sections[category].append((current_title, content_text))

    return dict(sections)


def search_chatgpt_in_text(text: str) -> int:
    """
    Search for 'chatgpt' in text (case-insensitive).

    Args:
        text: Text to search

    Returns:
        Number of matches
    """
    # Case-insensitive search for 'chatgpt' with word boundaries
    pattern = r'\bchatgpt\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return len(matches)


def process_file(md_path: str) -> Dict:
    """
    Process a single markdown file.

    Args:
        md_path: Path to markdown file

    Returns:
        Dictionary with results
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        return {
            'file': md_path,
            'error': str(e),
            'total_matches': 0,
            'section_matches': {}
        }

    # Parse into sections
    sections = parse_sections(text)

    # Search for chatgpt in each section category
    section_matches = {}
    total_matches = 0

    for category, section_list in sections.items():
        category_matches = 0
        for title, content in section_list:
            matches = search_chatgpt_in_text(content)
            category_matches += matches

        if category_matches > 0:
            section_matches[category] = category_matches
            total_matches += category_matches

    return {
        'file': md_path,
        'total_matches': total_matches,
        'section_matches': section_matches
    }


def find_markdown_files(directory: str) -> List[str]:
    """Find all markdown files in directory recursively."""
    md_files = []
    directory_path = Path(directory)

    if not directory_path.exists():
        print(f"Error: Directory {directory} does not exist")
        return md_files

    for md_file in directory_path.rglob('*.md'):
        md_files.append(str(md_file))

    return sorted(md_files)


def save_results_csv(results: List[Dict], output_file: str, all_categories: List[str]):
    """Save results to CSV with section breakdown."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        header = ['File', 'Total Matches'] + [f'{cat}_matches' for cat in all_categories]
        writer.writerow(header)

        # Data rows
        for result in results:
            row = [
                result['file'],
                result['total_matches']
            ]
            for cat in all_categories:
                row.append(result['section_matches'].get(cat, 0))
            writer.writerow(row)

    print(f"Results saved to: {output_file}")


def save_summary_report(results: List[Dict], output_file: str, md_directory: str):
    """Save human-readable summary report."""
    # Aggregate statistics
    total_files = len(results)
    files_with_matches = sum(1 for r in results if r['total_matches'] > 0)
    total_matches = sum(r['total_matches'] for r in results)

    # Aggregate by section
    section_totals = defaultdict(int)
    for result in results:
        for cat, count in result['section_matches'].items():
            section_totals[cat] += count

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CHATGPT SECTION SEARCH REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Markdown Directory: {md_directory}\n")
        f.write(f"Search Term: ChatGPT (case-insensitive)\n\n")

        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total files searched: {total_files}\n")
        f.write(f"Files with ChatGPT mentions: {files_with_matches}\n")
        f.write(f"Total ChatGPT mentions: {total_matches}\n\n")

        f.write("=" * 80 + "\n")
        f.write("MATCHES BY SECTION\n")
        f.write("=" * 80 + "\n")

        # Sort by count descending
        for cat, count in sorted(section_totals.items(), key=lambda x: -x[1]):
            pct = (count / total_matches * 100) if total_matches > 0 else 0
            f.write(f"  {cat:20s}: {count:6d} ({pct:5.1f}%)\n")

        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("FILES WITH MATCHES (sorted by count)\n")
        f.write("=" * 80 + "\n\n")

        # Sort files by match count
        files_with_matches_list = [r for r in results if r['total_matches'] > 0]
        files_with_matches_list.sort(key=lambda x: -x['total_matches'])

        for result in files_with_matches_list[:100]:  # Top 100
            f.write(f"File: {result['file']}\n")
            f.write(f"  Total: {result['total_matches']}\n")
            for cat, count in sorted(result['section_matches'].items(), key=lambda x: -x[1]):
                f.write(f"    {cat}: {count}\n")
            f.write("\n")

        if len(files_with_matches_list) > 100:
            f.write(f"... and {len(files_with_matches_list) - 100} more files\n")

    print(f"Summary report saved to: {output_file}")


def main():
    # Configuration
    _NMI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MD_DIR = os.path.join(_NMI, "markdown")
    OUTPUT_DIR = os.path.join(_NMI, "data")

    num_workers = cpu_count()

    print("=" * 80)
    print("CHATGPT SECTION SEARCH")
    print("=" * 80)
    print(f"Markdown Directory: {MD_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Search Term: ChatGPT (case-insensitive)")
    print(f"Parallel workers: {num_workers}")
    print("=" * 80)
    print()

    # Find files
    print("Finding Markdown files...")
    md_files = find_markdown_files(MD_DIR)
    print(f"Found {len(md_files)} Markdown files")
    print()

    if not md_files:
        print("No files found. Exiting.")
        return

    # Process files in parallel
    print(f"Processing files with {num_workers} workers...")
    results = []

    with Pool(processes=num_workers) as pool:
        total = len(md_files)
        for i, result in enumerate(pool.imap_unordered(process_file, md_files, chunksize=50), 1):
            results.append(result)
            if i % 500 == 0 or i == total:
                print(f"  Progress: {i}/{total} ({100*i//total}%)")

    print()
    print(f"Completed processing {len(results)} files")
    print()

    # Determine all categories found
    all_categories = set()
    for result in results:
        all_categories.update(result['section_matches'].keys())
    all_categories = sorted(all_categories)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save results
    print("Saving results...")

    csv_file = os.path.join(OUTPUT_DIR, f'chatgpt_section_search_{timestamp}.csv')
    save_results_csv(results, csv_file, all_categories)

    json_file = os.path.join(OUTPUT_DIR, f'chatgpt_section_search_{timestamp}.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {json_file}")

    report_file = os.path.join(OUTPUT_DIR, f'chatgpt_section_report_{timestamp}.txt')
    save_summary_report(results, report_file, MD_DIR)

    # Print summary
    print()
    print("=" * 80)
    print("SEARCH COMPLETE")
    print("=" * 80)

    files_with_matches = sum(1 for r in results if r['total_matches'] > 0)
    total_matches = sum(r['total_matches'] for r in results)
    print(f"Files with ChatGPT mentions: {files_with_matches} / {len(results)}")
    print(f"Total ChatGPT mentions: {total_matches}")

    # Section breakdown
    section_totals = defaultdict(int)
    for result in results:
        for cat, count in result['section_matches'].items():
            section_totals[cat] += count

    print("\nMatches by section:")
    for cat, count in sorted(section_totals.items(), key=lambda x: -x[1]):
        pct = (count / total_matches * 100) if total_matches > 0 else 0
        print(f"  {cat:20s}: {count:6d} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
