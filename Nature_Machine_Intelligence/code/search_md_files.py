#!/usr/bin/env python3
"""
Main script for searching keywords in Markdown files.
Removes punctuation from both keywords and markdown content before searching.
Excludes references section but keeps appendix and acknowledgements.
"""
import os
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List
from multiprocessing import Pool, cpu_count
from functools import partial
from text_utils import load_keywords_from_file
from md_processor import search_keywords_in_markdown


def find_markdown_files(directory: str) -> List[str]:
    """
    Find all Markdown files in a directory (including subdirectories).

    Args:
        directory: Directory path to search

    Returns:
        List of paths to Markdown files
    """
    md_files = []
    directory_path = Path(directory)

    if not directory_path.exists():
        print(f"Error: Directory {directory} does not exist")
        return md_files

    # Find all .md files recursively
    for md_file in directory_path.rglob('*.md'):
        md_files.append(str(md_file))

    return sorted(md_files)


def save_results_csv(results: List[dict], output_file: str):
    """
    Save search results to CSV file.

    Args:
        results: List of search result dictionaries
        output_file: Path to output CSV file
    """
    if not results:
        print("No results to save")
        return

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'File',
            'Unique Keywords Found',
            'Total Matches',
            'Text Length',
            'Keywords Matched',
            'Match Details'
        ])

        # Write data
        for result in results:
            keywords_matched = ', '.join([m['keyword'] for m in result['matches']])
            match_details = '; '.join([f"{m['keyword']}: {m['count']}" for m in result['matches']])

            writer.writerow([
                result['file'],
                result['unique_keywords_found'],
                result['match_count'],
                result['text_length'],
                keywords_matched,
                match_details
            ])

    print(f"Results saved to: {output_file}")


def save_results_json(results: List[dict], output_file: str):
    """
    Save search results to JSON file.

    Args:
        results: List of search result dictionaries
        output_file: Path to output JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_file}")


def save_summary_report(results: List[dict], keywords: List[str], output_file: str,
                        md_directory: str, keywords_file: str):
    """
    Save a human-readable summary report.

    Args:
        results: List of search result dictionaries
        keywords: List of keywords searched
        output_file: Path to output text file
        md_directory: Directory that was searched
        keywords_file: Keywords file that was used
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("MARKDOWN KEYWORD SEARCH REPORT\n")
        f.write("=" * 80 + "\n\n")

        # Metadata
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Markdown Directory: {md_directory}\n")
        f.write(f"Keywords File: {keywords_file}\n")
        f.write(f"Total Keywords: {len(keywords)}\n")
        f.write(f"Total Markdown Files: {len(results)}\n\n")

        # Summary statistics
        files_with_matches = sum(1 for r in results if r['match_count'] > 0)
        total_matches = sum(r['match_count'] for r in results)
        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Files with matches: {files_with_matches} / {len(results)}\n")
        f.write(f"Total keyword matches: {total_matches}\n\n")

        # Keyword frequency breakdown
        keyword_counts = {}
        for result in results:
            for match in result['matches']:
                kw = match['keyword']
                keyword_counts[kw] = keyword_counts.get(kw, 0) + match['count']

        if keyword_counts:
            f.write("=" * 80 + "\n")
            f.write("KEYWORD FREQUENCY (sorted by count)\n")
            f.write("=" * 80 + "\n")
            for kw, count in sorted(keyword_counts.items(), key=lambda x: -x[1]):
                f.write(f"  {kw}: {count}\n")
            f.write("\n")

        # Detailed results
        f.write("=" * 80 + "\n")
        f.write("DETAILED RESULTS (files with matches only)\n")
        f.write("=" * 80 + "\n\n")

        for result in results:
            if result['match_count'] > 0:
                f.write(f"File: {result['file']}\n")
                f.write(f"  Unique keywords found: {result['unique_keywords_found']}\n")
                f.write(f"  Total matches: {result['match_count']}\n")
                f.write(f"  Matches:\n")
                for match in result['matches']:
                    f.write(f"    - {match['keyword']}: {match['count']}\n")
                f.write("\n")

        # Files without matches
        files_without_matches = [r for r in results if r['match_count'] == 0]
        if files_without_matches:
            f.write("=" * 80 + "\n")
            f.write(f"FILES WITHOUT MATCHES ({len(files_without_matches)} files)\n")
            f.write("=" * 80 + "\n\n")
            for result in files_without_matches:
                f.write(f"  - {result['file']}\n")

    print(f"Summary report saved to: {output_file}")


def process_single_file(md_file: str, keywords: List[str], lowercase: bool, remove_punct: bool) -> dict:
    """
    Process a single Markdown file (for multiprocessing).

    Args:
        md_file: Path to Markdown file
        keywords: List of keywords to search
        lowercase: Convert to lowercase if True
        remove_punct: Remove punctuation if True

    Returns:
        Search results dictionary
    """
    return search_keywords_in_markdown(md_file, keywords, lowercase=lowercase, remove_punct=remove_punct)


def search_markdown_directory(md_directory: str, keywords_file: str, output_dir: str,
                              lowercase: bool = True, remove_punct: bool = True, num_workers: int = None):
    """
    Search all Markdown files in a directory for keywords using parallel processing.

    Args:
        md_directory: Directory containing Markdown files
        keywords_file: File containing keywords (one per line)
        output_dir: Directory to save results
        lowercase: Convert to lowercase if True
        remove_punct: Remove punctuation if True
        num_workers: Number of parallel workers (default: CPU count)
    """
    # Determine number of workers
    if num_workers is None:
        num_workers = cpu_count()

    print("=" * 80)
    print("MARKDOWN KEYWORD SEARCH")
    print("=" * 80)
    print(f"Markdown Directory: {md_directory}")
    print(f"Keywords File: {keywords_file}")
    print(f"Output Directory: {output_dir}")
    print(f"Case-insensitive: {lowercase}")
    print(f"Remove punctuation: {remove_punct}")
    print(f"Parallel workers: {num_workers}")
    print("=" * 80)
    print()

    # Load keywords
    print("Loading keywords...")
    keywords = load_keywords_from_file(keywords_file, lowercase=lowercase, remove_punct=remove_punct)
    print(f"Loaded {len(keywords)} keywords")
    print()

    # Find Markdown files
    print("Finding Markdown files...")
    md_files = find_markdown_files(md_directory)
    print(f"Found {len(md_files)} Markdown files")
    print()

    if not md_files:
        print("No Markdown files found. Exiting.")
        return

    # Search Markdown files in parallel
    print(f"Searching Markdown files using {num_workers} parallel workers...")
    print("This may take a while for large datasets...")
    print()

    # Create partial function with fixed parameters
    process_func = partial(process_single_file, keywords=keywords, lowercase=lowercase, remove_punct=remove_punct)

    # Use multiprocessing pool
    results = []
    with Pool(processes=num_workers) as pool:
        # Process files and show progress
        total_files = len(md_files)
        for i, result in enumerate(pool.imap_unordered(process_func, md_files, chunksize=10), 1):
            results.append(result)
            if i % 100 == 0 or i == total_files:
                print(f"  Progress: {i}/{total_files} files processed ({100*i//total_files}%)")

    print()
    print(f"Completed processing {len(results)} files")
    print()

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate timestamp for output files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save results
    print("Saving results...")

    # CSV output
    csv_file = os.path.join(output_dir, f'search_results_{timestamp}.csv')
    save_results_csv(results, csv_file)

    # JSON output (optional)
    json_file = os.path.join(output_dir, f'search_results_{timestamp}.json')
    save_results_json(results, json_file)

    # Summary report
    report_file = os.path.join(output_dir, f'search_report_{timestamp}.txt')
    save_summary_report(results, keywords, report_file, md_directory, keywords_file)

    print()
    print("=" * 80)
    print("SEARCH COMPLETE")
    print("=" * 80)

    # Print summary
    files_with_matches = sum(1 for r in results if r['match_count'] > 0)
    total_matches = sum(r['match_count'] for r in results)
    print(f"Files with matches: {files_with_matches} / {len(results)}")
    print(f"Total keyword matches: {total_matches}")


if __name__ == "__main__":
    import sys

    # Default configuration
    _NMI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_MD_DIR = os.path.join(_NMI, "markdown")
    DEFAULT_KEYWORDS_FILE = os.path.join(_NMI, "keywords", "keywords_union.txt")
    DEFAULT_OUTPUT_DIR = os.path.join(_NMI, "data")

    # Parse command line arguments
    if len(sys.argv) > 1:
        md_directory = sys.argv[1]
    else:
        md_directory = DEFAULT_MD_DIR

    if len(sys.argv) > 2:
        keywords_file = sys.argv[2]
    else:
        keywords_file = DEFAULT_KEYWORDS_FILE

    if len(sys.argv) > 3:
        output_dir = sys.argv[3]
    else:
        output_dir = DEFAULT_OUTPUT_DIR

    # Run search
    try:
        search_markdown_directory(
            md_directory=md_directory,
            keywords_file=keywords_file,
            output_dir=output_dir,
            lowercase=True,
            remove_punct=True
        )
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
