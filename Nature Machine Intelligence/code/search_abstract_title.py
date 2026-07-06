#!/usr/bin/env python3
"""
Search for general LLM/VLM terms in abstract and title sections only of markdown files.
This helps identify papers that are generally about LLMs/VLMs.
"""
import os
import re
import csv
import json
import string
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from multiprocessing import Pool, cpu_count
from functools import partial


def remove_punctuation(text: str) -> str:
    """Remove all punctuation from text."""
    if not text:
        return ""
    translator = str.maketrans('', '', string.punctuation)
    return text.translate(translator)


def normalize_text(text: str, lowercase: bool = True, remove_punct: bool = True) -> str:
    """Normalize text for searching."""
    if not text:
        return ""
    if remove_punct:
        text = remove_punctuation(text)
    if lowercase:
        text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def load_keywords_from_file(file_path: str, lowercase: bool = True, remove_punct: bool = True) -> List[str]:
    """Load keywords from file and normalize them."""
    keywords = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            keyword = line.strip()
            if keyword and not keyword.startswith('#'):
                normalized = normalize_text(keyword, lowercase=lowercase, remove_punct=remove_punct)
                if normalized:
                    keywords.append(normalized)

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    return unique_keywords


def extract_title_and_abstract(text: str) -> Tuple[str, str]:
    """
    Extract title and abstract from markdown text.

    Args:
        text: Full markdown text

    Returns:
        Tuple of (title, abstract)
    """
    lines = text.split('\n')
    title = ""
    abstract = ""

    in_abstract = False
    abstract_lines = []

    for i, line in enumerate(lines):
        # Look for title (first ## header or # header)
        if not title:
            title_match = re.match(r'^#{1,2}\s+(.+)$', line)
            if title_match:
                title = title_match.group(1).strip()
                continue

        # Look for abstract section
        if re.match(r'^#{1,3}\s*abstract\s*$', line, re.IGNORECASE):
            in_abstract = True
            continue

        # If we're in abstract, collect lines until next section header
        if in_abstract:
            if re.match(r'^#{1,3}\s+', line):
                # Hit a new section, stop collecting abstract
                break
            abstract_lines.append(line)

    abstract = ' '.join(abstract_lines).strip()

    return title, abstract


def search_keywords_in_text(text: str, keywords: List[str]) -> List[Dict]:
    """
    Search for keywords in text using word boundary matching.

    Args:
        text: Normalized text to search
        keywords: List of normalized keywords

    Returns:
        List of match dictionaries with keyword and count
    """
    matches = []
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        found = re.findall(pattern, text)
        if found:
            matches.append({
                'keyword': keyword,
                'count': len(found)
            })
    return matches


def process_single_file(md_path: str, keywords: List[str], lowercase: bool = True,
                        remove_punct: bool = True) -> Dict:
    """
    Process a single markdown file for abstract/title search.

    Args:
        md_path: Path to markdown file
        keywords: List of keywords to search
        lowercase: Convert to lowercase if True
        remove_punct: Remove punctuation if True

    Returns:
        Dictionary with search results
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        return {
            'file': md_path,
            'has_title': False,
            'has_abstract': False,
            'title': '',
            'abstract': '',
            'title_matches': [],
            'abstract_matches': [],
            'matches': [],
            'match_count': 0,
            'unique_keywords_found': 0,
            'error': str(e)
        }

    # Extract title and abstract
    title_raw, abstract_raw = extract_title_and_abstract(text)

    # Normalize for searching
    title_normalized = normalize_text(title_raw, lowercase=lowercase, remove_punct=remove_punct)
    abstract_normalized = normalize_text(abstract_raw, lowercase=lowercase, remove_punct=remove_punct)

    # Search in title
    title_matches = search_keywords_in_text(title_normalized, keywords)
    title_keywords = [m['keyword'] for m in title_matches]

    # Search in abstract
    abstract_matches = search_keywords_in_text(abstract_normalized, keywords)
    abstract_keywords = [m['keyword'] for m in abstract_matches]

    # Combine matches (unique keywords across both)
    all_keywords = {}
    for m in title_matches + abstract_matches:
        kw = m['keyword']
        all_keywords[kw] = all_keywords.get(kw, 0) + m['count']

    combined_matches = [{'keyword': k, 'count': v} for k, v in all_keywords.items()]
    total_count = sum(m['count'] for m in combined_matches)

    # Truncate for preview
    title_preview = title_raw[:200] if title_raw else ''
    abstract_preview = abstract_raw[:500] if abstract_raw else ''

    return {
        'file': md_path,
        'has_title': bool(title_raw),
        'has_abstract': bool(abstract_raw),
        'title': title_preview,
        'abstract': abstract_preview,
        'title_matches': title_keywords,
        'abstract_matches': abstract_keywords,
        'matches': combined_matches,
        'match_count': total_count,
        'unique_keywords_found': len(combined_matches)
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


def save_results_csv(results: List[Dict], output_file: str):
    """Save search results to CSV file."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'File',
            'Has Title',
            'Has Abstract',
            'Unique Keywords Found',
            'Total Matches',
            'Title Matches',
            'Abstract Matches',
            'All Keywords Matched',
            'Title Preview',
            'Abstract Preview'
        ])

        for result in results:
            title_matches_str = ', '.join(result['title_matches']) if result['title_matches'] else ''
            abstract_matches_str = ', '.join(result['abstract_matches']) if result['abstract_matches'] else ''
            all_keywords_str = ', '.join([m['keyword'] for m in result['matches']])

            writer.writerow([
                result['file'],
                'Yes' if result['has_title'] else 'No',
                'Yes' if result['has_abstract'] else 'No',
                result['unique_keywords_found'],
                result['match_count'],
                title_matches_str,
                abstract_matches_str,
                all_keywords_str,
                result['title'],
                result['abstract']
            ])

    print(f"Results saved to: {output_file}")


def save_summary_report(results: List[Dict], keywords: List[str], output_file: str,
                        md_directory: str, keywords_file: str):
    """Save human-readable summary report."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("MARKDOWN ABSTRACT/TITLE KEYWORD SEARCH REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Markdown Directory: {md_directory}\n")
        f.write(f"Keywords File: {keywords_file}\n")
        f.write(f"Total Keywords: {len(keywords)}\n")
        f.write(f"Total Markdown Files: {len(results)}\n")
        f.write(f"Search Scope: Title and Abstract only\n\n")

        # Summary statistics
        files_with_matches = sum(1 for r in results if r['match_count'] > 0)
        files_with_title = sum(1 for r in results if r['has_title'])
        files_with_abstract = sum(1 for r in results if r['has_abstract'])
        total_matches = sum(r['match_count'] for r in results)

        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Files with matches: {files_with_matches} / {len(results)}\n")
        f.write(f"Files with title: {files_with_title} / {len(results)}\n")
        f.write(f"Files with abstract: {files_with_abstract} / {len(results)}\n")
        f.write(f"Total keyword matches: {total_matches}\n\n")

        # Top keywords found
        keyword_counts = {}
        for result in results:
            for match in result['matches']:
                kw = match['keyword']
                keyword_counts[kw] = keyword_counts.get(kw, 0) + match['count']

        if keyword_counts:
            f.write("=" * 80 + "\n")
            f.write("TOP KEYWORDS FOUND (by total occurrences)\n")
            f.write("=" * 80 + "\n")
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
            for kw, count in sorted_keywords[:30]:
                f.write(f"  {kw}: {count}\n")
            f.write("\n")

        # Files per keyword
        keyword_file_counts = {}
        for result in results:
            seen_kw = set()
            for match in result['matches']:
                kw = match['keyword']
                if kw not in seen_kw:
                    keyword_file_counts[kw] = keyword_file_counts.get(kw, 0) + 1
                    seen_kw.add(kw)

        if keyword_file_counts:
            f.write("=" * 80 + "\n")
            f.write("KEYWORDS BY NUMBER OF FILES\n")
            f.write("=" * 80 + "\n")
            sorted_by_files = sorted(keyword_file_counts.items(), key=lambda x: x[1], reverse=True)
            for kw, count in sorted_by_files[:30]:
                f.write(f"  {kw}: {count} files\n")
            f.write("\n")

        # Detailed results (top 100)
        f.write("=" * 80 + "\n")
        f.write("DETAILED RESULTS (top 100 by match count)\n")
        f.write("=" * 80 + "\n\n")

        matching_results = [r for r in results if r['match_count'] > 0]
        matching_results.sort(key=lambda x: -x['match_count'])

        for result in matching_results[:100]:
            f.write(f"File: {result['file']}\n")
            f.write(f"  Unique keywords: {result['unique_keywords_found']}, Total matches: {result['match_count']}\n")

            if result['title_matches']:
                f.write(f"  Keywords in title: {', '.join(result['title_matches'])}\n")
            if result['abstract_matches']:
                f.write(f"  Keywords in abstract: {', '.join(result['abstract_matches'])}\n")

            if result['title']:
                f.write(f"  Title: {result['title'][:100]}...\n")
            f.write("\n")

        if len(matching_results) > 100:
            f.write(f"... and {len(matching_results) - 100} more files with matches\n")

    print(f"Summary report saved to: {output_file}")


def main():
    # Configuration
    MD_DIR = "/home/aipexws3/Jessica/GhostAI/docling_extraction/output/MachineIntelligence"
    KEYWORDS_FILE = "/home/aipexws3/Jessica/GhostAI/Supplementary/keywords/general_llm_terms.txt"
    OUTPUT_DIR = "/home/aipexws3/Jessica/GhostAI/PDFAnalysis/results_MachineIntelligence"

    num_workers = cpu_count()

    print("=" * 80)
    print("MARKDOWN ABSTRACT/TITLE KEYWORD SEARCH")
    print("=" * 80)
    print(f"Markdown Directory: {MD_DIR}")
    print(f"Keywords File: {KEYWORDS_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Search Scope: Title and Abstract only")
    print(f"Parallel workers: {num_workers}")
    print("=" * 80)
    print()

    # Load keywords
    print("Loading keywords...")
    keywords = load_keywords_from_file(KEYWORDS_FILE)
    print(f"Loaded {len(keywords)} keywords")
    print()

    # Find files
    print("Finding Markdown files...")
    md_files = find_markdown_files(MD_DIR)
    print(f"Found {len(md_files)} Markdown files")
    print()

    if not md_files:
        print("No files found. Exiting.")
        return

    # Process files
    print(f"Searching Markdown files (abstract/title only) using {num_workers} parallel workers...")
    print()

    process_func = partial(process_single_file, keywords=keywords, lowercase=True, remove_punct=True)

    results = []
    with Pool(processes=num_workers) as pool:
        total = len(md_files)
        for i, result in enumerate(pool.imap_unordered(process_func, md_files, chunksize=50), 1):
            results.append(result)
            if i % 500 == 0 or i == total:
                print(f"  Progress: {i}/{total} ({100*i//total}%)")

    print()
    print(f"Completed processing {len(results)} files")
    print()

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save results
    print("Saving results...")

    csv_file = os.path.join(OUTPUT_DIR, f'abstract_title_search_{timestamp}.csv')
    save_results_csv(results, csv_file)

    json_file = os.path.join(OUTPUT_DIR, f'abstract_title_search_{timestamp}.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {json_file}")

    report_file = os.path.join(OUTPUT_DIR, f'abstract_title_report_{timestamp}.txt')
    save_summary_report(results, keywords, report_file, MD_DIR, KEYWORDS_FILE)

    # Print summary
    print()
    print("=" * 80)
    print("SEARCH COMPLETE")
    print("=" * 80)

    files_with_matches = sum(1 for r in results if r['match_count'] > 0)
    total_matches = sum(r['match_count'] for r in results)
    print(f"Files with matches: {files_with_matches} / {len(results)}")
    print(f"Total keyword matches: {total_matches}")
    print()
    print(f"These {files_with_matches} papers mention general LLM/VLM terms in their abstract or title")


if __name__ == "__main__":
    main()
