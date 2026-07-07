#!/usr/bin/env python3
"""
Extract and verify all results needed for the GhostAI research paper.
Reads CSVs and produces a comprehensive results report.
"""

import csv
import re
import os
from collections import Counter, defaultdict
from datetime import datetime

# ─── File paths ───
SEARCH_RESULTS = "<results>/search_results_20260126_164130.csv"
ABSTRACT_TITLE  = "<results>/abstract_title_search_20260126_165046.csv"
CHATGPT_SECTION = "<results>/chatgpt_section_search_20260126_164546.csv"
CLASSIFICATION  = "<results>/classification_detailed_20260126_181325.csv"
GITHUB_COMBINED = "<results>/github_keywords_combined_20260212_135804.csv"
DEPRECATIONS    = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.pardir, "Supplementary", "keywords", "deprecation_registry.csv")
OUTPUT_FILE     = "<results>/EXTRACTED_RESULTS.md"

# ─── Exact vs Base model name lists from update_keywords.txt ───
EXACT_MODELS = {
    # OpenAI exact
    "babbage-002", "chatgpt-4o-latest", "codex-mini-latest",
    "computer-use-preview-2025-03-11", "dall-e-2", "dall-e-3",
    "davinci-002", "gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-instruct", "gpt-4-0125-preview", "gpt-4-0314",
    "gpt-4-0613", "gpt-4-1106-vision-preview", "gpt-4-turbo-2024-04-09",
    "gpt-4.1-2025-04-14", "gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14",
    "gpt-4.5-preview-2025-02-27", "gpt-4o-2024-05-13", "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20", "gpt-4o-audio-preview-2024-10-01",
    "gpt-4o-audio-preview-2024-12-17", "gpt-4o-audio-preview-2025-06-03",
    "gpt-4o-mini-2024-07-18", "gpt-4o-mini-audio-preview-2024-12-17",
    "gpt-4o-mini-realtime-preview-2024-12-17",
    "gpt-4o-mini-search-preview-2025-03-11", "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts", "gpt-4o-realtime-preview-2024-10-01",
    "gpt-4o-realtime-preview-2024-12-17", "gpt-4o-realtime-preview-2025-06-03",
    "gpt-4o-search-preview-2025-03-11", "gpt-4o-transcribe",
    "gpt-4o-transcribe-diarize", "gpt-5-2025-08-07", "gpt-5-chat-latest",
    "gpt-5.1-chat-latest", "gpt-5-codex", "gpt-5-codex-mini",
    "gpt-5-mini-2025-08-07", "gpt-5-nano-2025-08-07", "gpt-5-pro-2025-10-06",
    "gpt-5.2-2025-12-11", "gpt-5.2-pro-2025-12-11", "gpt-audio-2025-08-28",
    "gpt-audio-mini-2025-10-06", "gpt-image-1", "gpt-image-1-mini",
    "gpt-realtime-2025-08-28", "gpt-realtime-mini-2025-10-06",
    "o1-2024-12-17", "o1-mini-2024-09-12", "o1-preview-2024-09-12",
    "o1-pro-2025-03-19", "o3-2025-04-16", "o3-deep-research-2025-06-26",
    "o3-mini-2025-01-31", "o3-pro-2025-06-10", "o4-mini-2025-04-16",
    "o4-mini-deep-research-2025-06-26", "omni-moderation-2024-09-26",
    "sora-2", "sora-2-pro", "text-embedding-3-large", "text-embedding-3-small",
    "text-embedding-ada-002", "text-moderation-007", "tts-1", "tts-1-hd", "whisper-1",
    # Anthropic exact
    "claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219",
    "claude-opus-4-20250514", "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307", "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001", "claude-opus-4-1-20250805",
    "claude-3-opus-20240229", "claude-opus-4-5-20251101",
    # Gemini exact
    "gemini-2.0-flash-001", "gemini-2.0-flash-lite-001",
}

BASE_MODELS = {
    # OpenAI base
    "gpt-5.1-chat-latest", "gpt-5.2", "gpt-5.2-pro", "gpt-5-codex-mini",
    "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro", "gpt-4.1",
    "sora-2", "sora-2-pro", "o3-deep-research", "o4-mini-deep-research",
    "gpt-image-1", "gpt-image-1-mini", "dall-e-3", "gpt-4o-mini-tts",
    "gpt-4o-transcribe", "gpt-4o-mini-transcribe", "gpt-realtime",
    "gpt-audio", "gpt-realtime-mini", "gpt-audio-mini", "gpt-5-chat-latest",
    "chatgpt-4o-latest", "gpt-5-codex", "o3-pro", "o3", "o4-mini",
    "gpt-4.1-mini", "gpt-4.1-nano", "o1-pro", "computer-use-preview",
    "gpt-4o-mini-search-preview", "gpt-4o-search-preview", "gpt-4.5-preview",
    "o3-mini", "gpt-4o-mini-audio-preview", "gpt-4o-mini-realtime-preview",
    "o1", "omni-moderation-latest", "o1-mini", "o1-preview", "gpt-4o",
    "gpt-4o-audio-preview", "gpt-4o-mini", "gpt-4o-realtime-preview",
    "gpt-4-turbo", "babbage-002", "codex-mini-latest", "dall-e-2",
    "davinci-002", "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview",
    "gpt-4o-transcribe-diarize", "text-embedding-3-large",
    "text-embedding-3-small", "text-embedding-ada-002",
    "text-moderation-latest", "text-moderation-stable", "tts-1", "tts-1-hd", "whisper-1",
    # Anthropic base
    "claude-sonnet-4-0", "claude-3-7-sonnet-latest", "claude-opus-4-0",
    "claude-3-5-haiku-latest", "claude-sonnet-4-5", "claude-haiku-4-5",
    "claude-opus-4-1",
    # Gemini base
    "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-image",
    "gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash",
    "gemini-embedding-001", "text-embedding-005", "text-embedding-004",
    "text-multilingual-embedding-002", "multimodalembedding@001",
}

# ─── Deprecated model names (from Deprecations.csv, only actual model names) ───
DEPRECATED_MODELS_LIST = [
    "chatgpt-4o-latest", "codex-mini-latest", "dall-e-2", "dall-e-3",
    "gpt-4-0314", "gpt-4-1106-preview", "gpt-4-0125-preview",
    "gpt-3.5-turbo-instruct", "babbage-002", "davinci-002", "gpt-3.5-turbo-1106",
    "gpt-4o-realtime-preview", "gpt-4o-realtime-preview-2025-06-03",
    "gpt-4o-realtime-preview-2024-12-17", "gpt-4o-mini-realtime-preview",
    "gpt-4o-audio-preview", "gpt-4o-mini-audio-preview",
    "gpt-4o-realtime-preview-2024-10-01", "gpt-4o-audio-preview-2024-10-01",
    "text-moderation-007", "text-moderation-stable", "text-moderation-latest",
    "o1-preview", "o1-mini", "gpt-4.5-preview",
    "gpt-4-32k", "gpt-4-32k-0613", "gpt-4-32k-0314",
    "gpt-4-vision-preview", "gpt-4-1106-vision-preview",
    "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-0301",
    "text-ada-001", "text-babbage-001", "text-curie-001",
    "text-davinci-001", "text-davinci-002", "text-davinci-003",
    "code-davinci-002", "text-davinci-edit-001", "code-davinci-edit-001",
    "text-similarity-ada-001", "text-search-ada-doc-001",
    "text-search-ada-query-001", "code-search-ada-code-001",
    "code-search-ada-text-001", "text-similarity-babbage-001",
    "text-search-babbage-doc-001", "text-search-babbage-query-001",
    "code-search-babbage-code-001", "code-search-babbage-text-001",
    "text-similarity-curie-001", "text-search-curie-doc-001",
    "text-search-curie-query-001", "text-similarity-davinci-001",
    "text-search-davinci-doc-001", "text-search-davinci-query-001",
    "code-davinci-001", "code-cushman-002", "code-cushman-001",
    # Anthropic
    "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20240620", "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229", "claude-2.0", "claude-2.1",
    "claude-3-sonnet-20240229", "claude-1.0", "claude-1.1",
    "claude-1.2", "claude-1.3", "claude-instant-1.0",
    "claude-instant-1.1", "claude-instant-1.2",
    # Gemini
    "gemini-1.5-pro-001", "gemini-1.5-pro-002",
    "gemini-1.5-flash-001", "gemini-1.5-flash-002",
    "gemini-1.0-pro-001", "gemini-1.0-pro-002", "gemini-1.0-pro-vision-001",
    "text-bison", "chat-bison", "code-gecko",
    "textembedding-gecko@002", "textembedding-gecko@001",
    "textembedding-gecko@003", "textembedding-gecko-multilingual@001",
    "gpt-4-turbo-preview", "gpt-4-turbo-preview-completions",
]

# Also load the deprecation dates mapping
DEPRECATION_DATES = {}
ALREADY_DEPRECATED = set()  # Deprecated before today (2026-02-13)
FUTURE_DEPRECATED = set()   # Announced but not yet enacted


def load_deprecation_dates():
    """Load deprecation dates from CSV."""
    global DEPRECATION_DATES, ALREADY_DEPRECATED, FUTURE_DEPRECATED
    today = datetime(2026, 2, 13)
    with open(DEPRECATIONS, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row['Model / System'].strip()
            date_str = row['Shutdown date'].strip()
            # Skip API endpoints and non-model entries
            if model.startswith('/v1/') or model.startswith('OpenAI-Beta') or \
               model.startswith('Assistants') or model.startswith('New fine-tuning'):
                continue
            try:
                shutdown_date = datetime.strptime(date_str, '%m/%d/%Y')
                DEPRECATION_DATES[model] = shutdown_date
                if shutdown_date <= today:
                    ALREADY_DEPRECATED.add(model)
                else:
                    FUTURE_DEPRECATED.add(model)
            except ValueError:
                pass


def extract_venue_year(filepath):
    """Extract venue and year from file path."""
    # Pattern: .../output/venue_year/... or from paper_name column
    parts = filepath.replace('\\', '/').split('/')
    for part in parts:
        match = re.match(r'(aaai|neurips|iclr|icml)_(\d{4})', part, re.IGNORECASE)
        if match:
            return match.group(1).upper(), int(match.group(2))
    # Try from filename
    for part in parts:
        match = re.match(r'(AAAI|NeurIPS|ICLR|ICML)[_-](\d{4})', part)
        if match:
            return match.group(1).upper(), int(match.group(2))
    return "UNKNOWN", None


def extract_venue_year_from_papername(paper_name):
    """Extract venue and year from paper_name like AAAI_2022_21650_..."""
    match = re.match(r'(AAAI|NeurIPS|ICLR|ICML)[_-](\d{4})', paper_name, re.IGNORECASE)
    if match:
        return match.group(1).upper(), int(match.group(2))
    # Try alternate patterns like neurips_2025
    match = re.match(r'(aaai|neurips|iclr|icml)[_-](\d{4})', paper_name, re.IGNORECASE)
    if match:
        return match.group(1).upper(), int(match.group(2))
    return "UNKNOWN", None


def normalize_keyword(kw):
    """Normalize keyword for matching (remove hyphens, underscores, dots, lowercase)."""
    return re.sub(r'[-_\s@*.]', '', kw.lower())


def get_provider(keyword):
    """Determine provider from keyword. Handles both normalized and raw forms."""
    kw_lower = normalize_keyword(keyword)
    # Anthropic first (to not match 'claude' as openai)
    if kw_lower.startswith('claude'):
        return 'Anthropic'
    # Google
    google_prefixes = ['gemini', 'textbison', 'chatbison', 'codegecko',
                       'textembeddinggecko', 'palm', 'imagen', 'veo',
                       'embeddinggecko', 'gemma', 'lyria', 'multimodal']
    for prefix in google_prefixes:
        if kw_lower.startswith(prefix):
            return 'Google'
    # OpenAI
    openai_prefixes = ['gpt', 'o1', 'o3', 'o4', 'dall', 'textdavinci', 'textada',
                       'textbabbage', 'textcurie', 'codedavinci', 'codecushman',
                       'textembedding', 'textsearch', 'textsimilarity', 'codesearch',
                       'textmoderation', 'babbage', 'davinci', 'chatgpt', 'codex',
                       'whisper', 'tts', 'sora', 'omnimoderation', 'computeruse',
                       'gptimage', 'gptaudio', 'gptrealtime']
    for prefix in openai_prefixes:
        if kw_lower.startswith(prefix):
            return 'OpenAI'
    return 'Other'


def main():
    load_deprecation_dates()
    output_lines = []

    def out(line=""):
        output_lines.append(line)
        print(line)

    out("=" * 80)
    out("GHOSTAI RESEARCH - COMPLETE EXTRACTED RESULTS")
    out(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out("=" * 80)

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 1: Model Name Extraction Results
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 1: MODEL NAME EXTRACTION RESULTS")
    out("=" * 80)

    total_files = 0
    files_with_matches = 0
    total_matches = 0
    keyword_counter = Counter()  # keyword -> total occurrences
    keyword_file_counter = Counter()  # keyword -> number of files
    year_files = defaultdict(int)  # year -> total files
    year_match_files = defaultdict(int)  # year -> files with matches
    year_matches = defaultdict(int)  # year -> total matches
    venue_files = defaultdict(int)
    venue_match_files = defaultdict(int)
    venue_matches = defaultdict(int)
    provider_matches = Counter()
    provider_files = defaultdict(set)  # provider -> set of files

    # Track per-file keywords for deprecation and exact/base analysis later
    file_keywords_map = {}  # filepath -> list of keywords
    file_venue_year = {}  # filepath -> (venue, year)

    with open(SEARCH_RESULTS, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_files += 1
            filepath = row['File']
            unique_kw = int(row['Unique Keywords Found'])
            matches = int(row['Total Matches'])
            keywords_str = row.get('Keywords Matched', '').strip()

            venue, year = extract_venue_year(filepath)
            file_venue_year[filepath] = (venue, year)

            if year:
                year_files[year] += 1
            venue_files[venue] += 1

            if unique_kw > 0 and matches > 0:
                files_with_matches += 1
                total_matches += matches

                if year:
                    year_match_files[year] += 1
                    year_matches[year] += matches
                venue_match_files[venue] += 1
                venue_matches[venue] += matches

                # Parse keywords
                if keywords_str:
                    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                    file_keywords_map[filepath] = keywords
                    for kw in keywords:
                        keyword_file_counter[kw] += 1
                        provider = get_provider(kw)
                        provider_files[provider].add(filepath)

                    # Parse match details for per-keyword counts
                    # Format: "keyword1: count1; keyword2: count2"
                    match_details = row.get('Match Details', '').strip()
                    if match_details:
                        for part in match_details.split(';'):
                            part = part.strip()
                            if ':' in part:
                                kw_part, count_part = part.rsplit(':', 1)
                                kw_part = kw_part.strip()
                                try:
                                    count = int(count_part.strip())
                                    keyword_counter[kw_part] += count
                                    provider = get_provider(kw_part)
                                    provider_matches[provider] += count
                                except ValueError:
                                    pass

    pct = (files_with_matches / total_files * 100) if total_files else 0
    out(f"\nFiles processed: {total_files:,}")
    out(f"Files with matches: {files_with_matches:,} / {total_files:,} ({pct:.1f}%)")
    out(f"Total keyword matches: {total_matches:,}")

    out("\n--- Top 30 Model Names by Occurrence Count ---")
    for kw, count in keyword_counter.most_common(30):
        file_count = keyword_file_counter.get(kw, 0)
        out(f"  {kw}: {count:,} occurrences ({file_count:,} files)")

    out("\n--- Top 30 Model Names by File Count ---")
    for kw, count in keyword_file_counter.most_common(30):
        occ = keyword_counter.get(kw, 0)
        out(f"  {kw}: {count:,} files ({occ:,} occurrences)")

    out("\n--- Breakdown by Provider ---")
    for provider in ['OpenAI', 'Anthropic', 'Google', 'Other']:
        match_count = provider_matches.get(provider, 0)
        file_count = len(provider_files.get(provider, set()))
        out(f"  {provider}: {match_count:,} occurrences, {file_count:,} files")

    out("\n--- Breakdown by Year ---")
    for year in sorted(year_files.keys()):
        total_y = year_files[year]
        match_y = year_match_files.get(year, 0)
        matches_y = year_matches.get(year, 0)
        pct_y = (match_y / total_y * 100) if total_y else 0
        out(f"  {year}: {match_y:,} / {total_y:,} files ({pct_y:.1f}%), {matches_y:,} total matches")

    out("\n--- Breakdown by Conference ---")
    for venue in sorted(venue_files.keys()):
        if venue == "UNKNOWN":
            continue
        total_v = venue_files[venue]
        match_v = venue_match_files.get(venue, 0)
        matches_v = venue_matches.get(venue, 0)
        pct_v = (match_v / total_v * 100) if total_v else 0
        out(f"  {venue}: {match_v:,} / {total_v:,} files ({pct_v:.1f}%), {matches_v:,} total matches")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 2: Broad LLM Engagement Search Results
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 2: BROAD LLM ENGAGEMENT SEARCH RESULTS")
    out("=" * 80)

    broad_total = 0
    broad_matches_files = 0
    broad_total_matches = 0
    broad_kw_counter = Counter()
    broad_kw_file_counter = Counter()

    with open(ABSTRACT_TITLE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            broad_total += 1
            unique_kw = int(row['Unique Keywords Found'])
            matches = int(row['Total Matches'])
            if unique_kw > 0 and matches > 0:
                broad_matches_files += 1
                broad_total_matches += matches
                all_kw = row.get('All Keywords Matched', '').strip()
                if all_kw:
                    for kw in all_kw.split(','):
                        kw = kw.strip()
                        if kw:
                            broad_kw_file_counter[kw] += 1

                # Title Matches and Abstract Matches are keyword name strings, not counts
                # The total count is in Total Matches

    pct_broad = (broad_matches_files / broad_total * 100) if broad_total else 0
    out(f"\nFiles with matches: {broad_matches_files:,} / {broad_total:,} ({pct_broad:.1f}%)")
    out(f"Total keyword matches: {broad_total_matches:,}")

    out("\n--- Top Keywords by File Count ---")
    for kw, count in broad_kw_file_counter.most_common(30):
        out(f"  {kw}: {count:,} files")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 3: Usage Context Classification Results
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 3: USAGE CONTEXT CLASSIFICATION RESULTS")
    out("=" * 80)

    class_counter = Counter()
    class_by_year = defaultdict(Counter)
    class_total = 0
    class_file_keywords = {}  # for cross-referencing

    with open(CLASSIFICATION, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_total += 1
            classification = row.get('Overall_Classification', '').strip()
            class_counter[classification] += 1
            filepath = row.get('File', '')
            venue, year = extract_venue_year(filepath)
            if year:
                class_by_year[year][classification] += 1
            keywords_str = row.get('Keywords', '').strip()
            if keywords_str:
                class_file_keywords[filepath] = {
                    'classification': classification,
                    'keywords': [k.strip() for k in keywords_str.split(',') if k.strip()]
                }

    out(f"\nTotal classified papers: {class_total:,}")
    out("\n--- Classification Distribution ---")
    for cls, count in class_counter.most_common():
        pct = (count / class_total * 100) if class_total else 0
        out(f"  {cls}: {count:,} ({pct:.1f}%)")

    out("\n--- Classification by Year ---")
    for year in sorted(class_by_year.keys()):
        total_yr = sum(class_by_year[year].values())
        out(f"\n  {year} (n={total_yr:,}):")
        for cls, count in class_by_year[year].most_common():
            pct = (count / total_yr * 100) if total_yr else 0
            out(f"    {cls}: {count:,} ({pct:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 4: Repository Analysis Results
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 4: REPOSITORY ANALYSIS RESULTS")
    out("=" * 80)

    gh_total = 0
    gh_accessible = 0
    gh_with_keywords = 0
    gh_kw_counter = Counter()
    gh_year_counter = defaultdict(int)
    gh_year_kw = defaultdict(int)
    gh_papers_with_kw = set()  # paper names that have repo keywords
    gh_paper_keywords = {}  # paper -> keywords found in repo

    # Inaccessible repo tracking
    gh_inaccessible = 0
    gh_inacc_by_venue = Counter()
    gh_inacc_by_year = Counter()
    gh_total_by_venue = Counter()
    gh_total_by_year = Counter()
    gh_inacc_papers = set()  # paper names with inaccessible repos

    with open(GITHUB_COMBINED, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gh_total += 1
            paper_name = row.get('paper_name', '')
            venue = row.get('venue', '')
            year_str = row.get('year', 'UNKNOWN')
            accessible = row.get('accessibility', '').strip().lower() == 'true'
            has_kw = row.get('has_keywords', '').strip().lower() == 'true'
            kw_str = row.get('exact_keywords_found', '').strip()

            # Extract venue/year from paper_name since year column is often UNKNOWN
            pn_venue, pn_year = extract_venue_year_from_papername(paper_name)
            if pn_venue != "UNKNOWN":
                venue = pn_venue
            if pn_year:
                year_str = str(pn_year)

            gh_total_by_venue[venue] += 1
            try:
                yr = int(year_str)
                gh_total_by_year[yr] += 1
            except ValueError:
                pass

            if accessible:
                gh_accessible += 1
            else:
                gh_inaccessible += 1
                gh_inacc_by_venue[venue] += 1
                gh_inacc_papers.add(paper_name)
                try:
                    yr = int(year_str)
                    gh_inacc_by_year[yr] += 1
                except ValueError:
                    pass

            if has_kw:
                gh_with_keywords += 1
                gh_papers_with_kw.add(paper_name)
                if kw_str:
                    kws = [k.strip() for k in kw_str.split(',') if k.strip()]
                    gh_paper_keywords[paper_name] = kws
                    for kw in kws:
                        gh_kw_counter[kw] += 1

            try:
                yr = int(year_str)
                gh_year_counter[yr] += 1
                if has_kw:
                    gh_year_kw[yr] += 1
            except ValueError:
                gh_year_counter['UNKNOWN'] += 1

    out(f"\nTotal repo entries: {gh_total:,}")
    out(f"Accessible repos: {gh_accessible:,}")
    out(f"Repos with confirmed keywords (after filtering): {gh_with_keywords:,}")

    out("\n--- Top 20 Keywords Found in Repos ---")
    for kw, count in gh_kw_counter.most_common(20):
        out(f"  {kw}: {count:,}")

    # Check: repos with model references NOT found in paper text
    # Build a set of papers with PDF keyword matches
    pdf_papers_with_kw = set()
    for filepath in file_keywords_map:
        # Extract paper name from filepath
        basename = os.path.basename(filepath).replace('.md', '')
        pdf_papers_with_kw.add(basename)

    repo_only_papers = []
    for paper_name in gh_papers_with_kw:
        if paper_name not in pdf_papers_with_kw:
            repo_only_papers.append(paper_name)

    out(f"\nRepos with model keywords NOT found in paper text: {len(repo_only_papers):,}")
    out("  (These are papers where the repo search found model usage not mentioned in the paper)")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 4b: Inaccessible Repository Analysis
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 4b: INACCESSIBLE REPOSITORY ANALYSIS")
    out("=" * 80)

    pct_inacc = (gh_inaccessible / gh_total * 100) if gh_total else 0
    out(f"\nTotal repos with reported GitHub links: {gh_total:,}")
    out(f"Accessible repos: {gh_accessible:,} ({gh_accessible/gh_total*100:.1f}%)")
    out(f"Inaccessible repos: {gh_inaccessible:,} ({pct_inacc:.1f}%)")

    out(f"\n--- Inaccessible Repos by Conference ---")
    for venue in ['AAAI', 'ICLR', 'ICML', 'NEURIPS']:
        total_v = gh_total_by_venue.get(venue, 0)
        inacc_v = gh_inacc_by_venue.get(venue, 0)
        if total_v > 0:
            pct_v = (inacc_v / total_v * 100)
            out(f"  {venue}: {inacc_v:,} / {total_v:,} ({pct_v:.1f}%)")

    out(f"\n--- Inaccessible Repos by Year ---")
    for year in sorted(gh_total_by_year.keys()):
        total_y = gh_total_by_year[year]
        inacc_y = gh_inacc_by_year.get(year, 0)
        pct_y = (inacc_y / total_y * 100) if total_y else 0
        out(f"  {year}: {inacc_y:,} / {total_y:,} ({pct_y:.1f}%)")

    # How many inaccessible repos had model keywords in the paper text?
    inacc_with_paper_kw = gh_inacc_papers & pdf_papers_with_kw
    inacc_without_paper_kw = gh_inacc_papers - pdf_papers_with_kw
    out(f"\n--- Inaccessible Repos + Paper Model Keywords ---")
    out(f"Inaccessible repos where paper text HAD model keywords: {len(inacc_with_paper_kw):,}")
    out(f"Inaccessible repos where paper text had NO model keywords: {len(inacc_without_paper_kw):,}")
    out(f"  (Papers with both inaccessible repos AND model keywords face compounded reproducibility risk)")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 5: Deprecation Cross-Referencing Results
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 5: DEPRECATION CROSS-REFERENCING RESULTS")
    out("=" * 80)

    # Build a normalized lookup for deprecated models
    deprecated_normalized = {}
    for model in ALREADY_DEPRECATED:
        deprecated_normalized[normalize_keyword(model)] = model
    future_deprecated_normalized = {}
    for model in FUTURE_DEPRECATED:
        future_deprecated_normalized[normalize_keyword(model)] = model

    # Also add common deprecated names not in the CSV but in the search keywords
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
    for m in additional_deprecated:
        deprecated_normalized[normalize_keyword(m)] = m

    # Count papers referencing deprecated models
    deprecated_keywords_found = Counter()  # deprecated keyword -> count of files
    papers_with_deprecated = set()
    papers_deprecated_by_year = defaultdict(set)
    papers_deprecated_by_classification = Counter()
    papers_deprecated_by_provider = defaultdict(set)

    papers_with_future_deprecated = set()

    for filepath, keywords in file_keywords_map.items():
        venue, year = file_venue_year.get(filepath, ("UNKNOWN", None))
        has_deprecated = False
        has_future_deprecated = False
        for kw in keywords:
            kw_norm = normalize_keyword(kw)
            if kw_norm in deprecated_normalized:
                has_deprecated = True
                deprecated_keywords_found[kw] += 1
                provider = get_provider(kw)
                papers_deprecated_by_provider[provider].add(filepath)
            elif kw_norm in future_deprecated_normalized:
                has_future_deprecated = True

        if has_deprecated:
            papers_with_deprecated.add(filepath)
            if year:
                papers_deprecated_by_year[year].add(filepath)
            # Get classification
            if filepath in class_file_keywords:
                cls = class_file_keywords[filepath]['classification']
                papers_deprecated_by_classification[cls] += 1

        if has_future_deprecated and not has_deprecated:
            papers_with_future_deprecated.add(filepath)

    # Count unique deprecated model names found
    unique_deprecated_found = len(deprecated_keywords_found)

    out(f"\nUnique deprecated model names found in papers: {unique_deprecated_found}")
    out(f"Papers referencing at least one deprecated model: {len(papers_with_deprecated):,} / {files_with_matches:,}")

    out(f"\n--- Top Deprecated Models Found ---")
    for kw, count in deprecated_keywords_found.most_common(20):
        shutdown = DEPRECATION_DATES.get(kw, None)
        date_str = shutdown.strftime('%Y-%m-%d') if shutdown else "already shutdown"
        out(f"  {kw}: {count:,} papers (shutdown: {date_str})")

    out(f"\n--- Papers with Deprecated Models by Year ---")
    for year in sorted(papers_deprecated_by_year.keys()):
        total_yr = year_match_files.get(year, 0)
        dep_yr = len(papers_deprecated_by_year[year])
        pct = (dep_yr / total_yr * 100) if total_yr else 0
        out(f"  {year}: {dep_yr:,} / {total_yr:,} matched papers ({pct:.1f}%)")

    out(f"\n--- Papers with Deprecated Models by Classification ---")
    for cls, count in papers_deprecated_by_classification.most_common():
        out(f"  {cls}: {count:,}")

    out(f"\n--- Papers with Deprecated Models by Provider ---")
    for provider in ['OpenAI', 'Anthropic', 'Google', 'Other']:
        count = len(papers_deprecated_by_provider.get(provider, set()))
        if count > 0:
            pct = (count / len(papers_with_deprecated) * 100) if papers_with_deprecated else 0
            out(f"  {provider}: {count:,} papers ({pct:.1f}%)")

    out(f"\n--- Future Deprecation Impact ---")
    out(f"Papers referencing models with announced future shutdown: {len(papers_with_future_deprecated):,}")
    out(f"  (These papers will become additionally affected)")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 6: Underreporting Analysis (ChatGPT)
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 6: UNDERREPORTING ANALYSIS RESULTS (ChatGPT)")
    out("=" * 80)

    chatgpt_total_files = 0
    chatgpt_files_with_matches = 0
    chatgpt_total_matches = 0
    section_totals = Counter()
    chatgpt_files_set = set()
    chatgpt_by_year = defaultdict(int)
    chatgpt_by_year_total = defaultdict(int)

    with open(CHATGPT_SECTION, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            chatgpt_total_files += 1
            filepath = row['File']
            matches = int(row['Total Matches'])
            venue, year = extract_venue_year(filepath)

            if year:
                chatgpt_by_year_total[year] += 1

            if matches > 0:
                chatgpt_files_with_matches += 1
                chatgpt_total_matches += matches
                chatgpt_files_set.add(filepath)

                if year:
                    chatgpt_by_year[year] += 1

                # Section breakdown
                for section in ['abstract_matches', 'acknowledgements_matches',
                                'appendix_matches', 'conclusion_matches',
                                'experiments_matches', 'introduction_matches',
                                'methods_matches', 'other_matches',
                                'references_matches', 'related_work_matches',
                                'results_matches']:
                    val = int(row.get(section, 0) or 0)
                    if val > 0:
                        section_totals[section.replace('_matches', '')] += val

    pct_chatgpt = (chatgpt_files_with_matches / chatgpt_total_files * 100) if chatgpt_total_files else 0
    out(f"\nFiles with ChatGPT mentions: {chatgpt_files_with_matches:,} / {chatgpt_total_files:,} ({pct_chatgpt:.1f}%)")
    out(f"Total ChatGPT mentions: {chatgpt_total_matches:,}")

    out("\n--- ChatGPT Mentions by Section ---")
    for section, count in section_totals.most_common():
        pct = (count / chatgpt_total_matches * 100) if chatgpt_total_matches else 0
        out(f"  {section}: {count:,} ({pct:.1f}%)")

    # How many ChatGPT papers also appear in model-specific papers?
    chatgpt_basenames = set()
    for fp in chatgpt_files_set:
        chatgpt_basenames.add(fp)

    chatgpt_also_specific = chatgpt_files_set & set(file_keywords_map.keys())
    chatgpt_only = chatgpt_files_set - set(file_keywords_map.keys())

    out(f"\n--- ChatGPT + Specific Model Overlap ---")
    out(f"ChatGPT papers that ALSO have specific model names: {len(chatgpt_also_specific):,}")
    out(f"ChatGPT papers with NO specific model named (ChatGPT-only): {len(chatgpt_only):,}")

    out(f"\n--- ChatGPT Mentions by Year ---")
    for year in sorted(chatgpt_by_year.keys()):
        total_yr = chatgpt_by_year_total.get(year, 0)
        chatgpt_yr = chatgpt_by_year.get(year, 0)
        pct = (chatgpt_yr / total_yr * 100) if total_yr else 0
        out(f"  {year}: {chatgpt_yr:,} / {total_yr:,} papers ({pct:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 7: Combined / Summary Numbers
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 7: COMBINED / SUMMARY NUMBERS")
    out("=" * 80)

    # Papers that are non-reproducible: deprecated models + ChatGPT-only
    non_reproducible = papers_with_deprecated | chatgpt_only
    out(f"\nTotal papers with deprecated model references: {len(papers_with_deprecated):,}")
    out(f"Total ChatGPT-only papers (no specific model): {len(chatgpt_only):,}")
    out(f"Combined non-reproducible papers: {len(non_reproducible):,}")
    out(f"  (Out of {total_files:,} total papers = {len(non_reproducible)/total_files*100:.1f}%)")

    # Year-over-year trend
    out(f"\n--- Non-Reproducibility Trend by Year ---")
    for year in sorted(set(list(year_files.keys()) + list(chatgpt_by_year.keys()))):
        if not isinstance(year, int):
            continue
        total_yr = year_files.get(year, 0)
        dep_yr = len(papers_deprecated_by_year.get(year, set()))
        # ChatGPT-only by year
        chatgpt_only_yr = 0
        for fp in chatgpt_only:
            v, y = extract_venue_year(fp)
            if y == year:
                chatgpt_only_yr += 1
        combined_yr = dep_yr + chatgpt_only_yr
        pct = (combined_yr / total_yr * 100) if total_yr else 0
        out(f"  {year}: {combined_yr:,} / {total_yr:,} ({pct:.1f}%) [deprecated: {dep_yr:,}, ChatGPT-only: {chatgpt_only_yr:,}]")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 8: Exact Names vs Base Model Names
    # ═══════════════════════════════════════════════════════════════════
    out("\n" + "=" * 80)
    out("SECTION 8: EXACT NAMES vs BASE MODEL NAMES")
    out("=" * 80)

    exact_norm = {normalize_keyword(m) for m in EXACT_MODELS}
    base_norm = {normalize_keyword(m) for m in BASE_MODELS}

    papers_with_exact = set()
    papers_with_base_only = set()
    papers_exact_and_base = set()
    exact_kw_counter = Counter()
    base_kw_counter = Counter()

    for filepath, keywords in file_keywords_map.items():
        has_exact = False
        has_base = False
        for kw in keywords:
            kw_norm = normalize_keyword(kw)
            if kw_norm in exact_norm:
                has_exact = True
                exact_kw_counter[kw] += 1
            elif kw_norm in base_norm:
                has_base = True
                base_kw_counter[kw] += 1

        if has_exact and has_base:
            papers_exact_and_base.add(filepath)
            papers_with_exact.add(filepath)
        elif has_exact:
            papers_with_exact.add(filepath)
        elif has_base:
            papers_with_base_only.add(filepath)

    out(f"\nPapers using exact/versioned model names: {len(papers_with_exact):,}")
    out(f"Papers using ONLY base model names (no exact version): {len(papers_with_base_only):,}")
    out(f"Papers using both exact and base names: {len(papers_exact_and_base):,}")

    # Categorize remaining papers (those with keywords but not in exact or base)
    papers_with_kw = set(file_keywords_map.keys())
    papers_neither = papers_with_kw - papers_with_exact - papers_with_base_only
    out(f"Papers with model names not in exact/base lists: {len(papers_neither):,}")
    out(f"  (These use deprecated-era model names like older codex, davinci, etc.)")

    out(f"\n--- Top Exact Model Names Found ---")
    for kw, count in exact_kw_counter.most_common(15):
        out(f"  {kw}: {count:,} papers")

    out(f"\n--- Top Base Model Names Found ---")
    for kw, count in base_kw_counter.most_common(15):
        out(f"  {kw}: {count:,} papers")

    # By year
    out(f"\n--- Exact vs Base Model Usage by Year ---")
    exact_by_year = defaultdict(int)
    base_by_year = defaultdict(int)
    for fp in papers_with_exact:
        v, y = file_venue_year.get(fp, ("UNKNOWN", None))
        if y:
            exact_by_year[y] += 1
    for fp in papers_with_base_only:
        v, y = file_venue_year.get(fp, ("UNKNOWN", None))
        if y:
            base_by_year[y] += 1

    for year in sorted(set(list(exact_by_year.keys()) + list(base_by_year.keys()))):
        exact_yr = exact_by_year.get(year, 0)
        base_yr = base_by_year.get(year, 0)
        total_yr = exact_yr + base_yr
        if total_yr > 0:
            exact_pct = (exact_yr / total_yr * 100)
            base_pct = (base_yr / total_yr * 100)
            out(f"  {year}: Exact: {exact_yr:,} ({exact_pct:.1f}%), Base-only: {base_yr:,} ({base_pct:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # Write output
    # ═══════════════════════════════════════════════════════════════════
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"\n\nResults saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
