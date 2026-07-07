"""
Markdown file processing for keyword search.
Handles reading and extracting text from markdown files.
Excludes references/bibliography section to avoid false positives from citations.
Keeps appendix and acknowledgements sections.
"""
import re
from typing import Optional
from text_utils import normalize_text


# Compound models - if a keyword is found inside one of these, it's not a real match
# e.g., "gpt4" inside "minigpt4" is not a GPT-4 match
COMPOUND_MODELS = [
    'minigpt4', 'minigpt4v', 'minigpt4video',
    'instructgpt', 'visualgpt', 'videogpt',
    'codegpt', 'biogpt', 'meditron',
    'opengpt', 'nanogpt', 'cogpt',
    'chatgpt4', 'chatgptapi',
]


def read_markdown_file(md_path: str) -> Optional[str]:
    """
    Read markdown file and return its contents.

    Args:
        md_path: Path to markdown file

    Returns:
        File contents as string, or None if reading fails
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {md_path}: {e}")
        return None


def extract_text_excluding_references(text: str) -> str:
    """
    Extract text content from markdown, EXCLUDING references/bibliography section.
    Keeps appendix and acknowledgements sections.

    Args:
        text: Full markdown text

    Returns:
        Text content without references section
    """
    if not text:
        return ""

    # Split by lines for processing
    lines = text.split('\n')
    result_lines = []
    in_references = False

    # Common reference section headers (case-insensitive matching)
    reference_headers = [
        r'^#{1,6}\s*references?\s*$',
        r'^#{1,6}\s*bibliography\s*$',
        r'^#{1,6}\s*works?\s+cited\s*$',
        r'^#{1,6}\s*literature\s+cited\s*$',
        r'^\*{0,2}references?\*{0,2}\s*$',
        r'^\*{0,2}bibliography\*{0,2}\s*$',
    ]

    # Sections that should end the references section (these come after references typically)
    # We want to KEEP appendix and acknowledgements
    end_reference_headers = [
        r'^#{1,6}\s*appendix',
        r'^#{1,6}\s*acknowledgement',
        r'^#{1,6}\s*acknowledgment',
        r'^#{1,6}\s*supplementary',
        r'^#{1,6}\s*supplemental',
        r'^\*{0,2}appendix',
        r'^\*{0,2}acknowledgement',
        r'^\*{0,2}acknowledgment',
    ]

    # Also detect new major sections (##) that would end references
    major_section_pattern = r'^#{1,2}\s+[A-Z]'

    for line in lines:
        line_lower = line.lower().strip()

        # Check if we're entering a references section
        if not in_references:
            is_ref_header = any(re.match(pattern, line_lower) for pattern in reference_headers)
            if is_ref_header:
                in_references = True
                continue

        # Check if we're exiting references (entering appendix, acknowledgements, etc.)
        if in_references:
            is_end_ref = any(re.match(pattern, line_lower) for pattern in end_reference_headers)
            if is_end_ref:
                in_references = False
                result_lines.append(line)
                continue

            # Also check for new major section headers that aren't reference-related
            # This handles cases where there's no explicit appendix/acknowledgements
            if re.match(r'^#{1,2}\s+\w', line) and not any(
                keyword in line_lower for keyword in ['reference', 'bibliography', 'cited']
            ):
                in_references = False
                result_lines.append(line)
                continue

        # Add line if not in references section
        if not in_references:
            result_lines.append(line)

    return '\n'.join(result_lines)


def get_markdown_text(md_path: str, lowercase: bool = True, remove_punct: bool = True,
                      exclude_references: bool = True) -> str:
    """
    Get text from a markdown file and normalize it.

    Args:
        md_path: Path to markdown file
        lowercase: Convert to lowercase if True
        remove_punct: Remove punctuation if True
        exclude_references: Exclude references/bibliography section if True

    Returns:
        Normalized text from markdown file
    """
    raw_text = read_markdown_file(md_path)
    if raw_text is None:
        return ""

    if exclude_references:
        raw_text = extract_text_excluding_references(raw_text)

    normalized = normalize_text(raw_text, lowercase=lowercase, remove_punct=remove_punct)

    return normalized


def is_compound_model_match(keyword: str, text: str, match_pos: int) -> bool:
    """
    Check if a keyword match is actually part of a compound model name.
    e.g., "gpt4" inside "minigpt4" should not be counted.

    Args:
        keyword: The keyword that was matched
        text: The full text
        match_pos: Position of the match in text

    Returns:
        True if this is a compound model match (should be excluded)
    """
    # Get surrounding context (20 chars before and after)
    start = max(0, match_pos - 20)
    end = min(len(text), match_pos + len(keyword) + 20)
    context = text[start:end].lower()

    # Check if any compound model is in the context containing our keyword
    for compound in COMPOUND_MODELS:
        if compound in context and keyword in compound:
            return True

    return False


def search_keywords_in_markdown(md_path: str, keywords: list, lowercase: bool = True,
                                 remove_punct: bool = True, exclude_references: bool = True) -> dict:
    """
    Search for keywords in a markdown file using word boundary matching.
    Special handling for o1 and o3 to only match actual model names.
    Excludes references section and compound model matches.

    Args:
        md_path: Path to markdown file
        keywords: List of normalized keywords to search for
        lowercase: Convert text to lowercase if True
        remove_punct: Remove punctuation if True
        exclude_references: Exclude references/bibliography section if True

    Returns:
        Dictionary with search results:
        {
            'file': md_path,
            'matches': list of matched keywords,
            'match_count': total number of matches,
            'text_length': length of document text
        }
    """
    # Get normalized text from markdown (excluding references by default)
    text = get_markdown_text(md_path, lowercase=lowercase, remove_punct=remove_punct,
                             exclude_references=exclude_references)

    # Special patterns for o1 and o3 - only match when part of actual model names
    # After punctuation removal: "o1-preview" becomes "o1preview"
    # We want to match: o1preview, o1mini, o1pro, etc. but NOT standalone "o1"
    O1_O3_SUFFIXES = [
        'deepresearch', 'pro', 'mini', 'preview',  # Main variants
        '20250416', '20250626', '20250131', '20250610',  # o3 dates
        '20241217', '20240912', '20250319'  # o1 dates
    ]

    # Build pattern: o1(deepresearch|pro|mini|...) or o3(deepresearch|pro|mini|...)
    o1_pattern = r'\bo1(?:' + '|'.join(O1_O3_SUFFIXES) + r')\b'
    o3_pattern = r'\bo3(?:' + '|'.join(O1_O3_SUFFIXES) + r')\b'

    # Keywords that might be part of compound models
    COMPOUND_CHECK_KEYWORDS = {'gpt4', 'gpt3', 'gpt35', 'gpt'}

    # Search for each keyword
    matches = []
    match_count = 0

    for keyword in keywords:
        # Special handling for o1 and o3
        if keyword == 'o1':
            found_matches = list(re.finditer(o1_pattern, text))
        elif keyword == 'o3':
            found_matches = list(re.finditer(o3_pattern, text))
        else:
            # Use regex with word boundaries for all other keywords
            pattern = r'\b' + re.escape(keyword) + r'\b'
            found_matches = list(re.finditer(pattern, text))

        # Filter out compound model matches for relevant keywords
        if keyword in COMPOUND_CHECK_KEYWORDS:
            valid_matches = []
            for match in found_matches:
                if not is_compound_model_match(keyword, text, match.start()):
                    valid_matches.append(match)
            found_matches = valid_matches

        count = len(found_matches)

        if count > 0:
            matches.append({
                'keyword': keyword,
                'count': count
            })
            match_count += count

    return {
        'file': md_path,
        'matches': matches,
        'match_count': match_count,
        'unique_keywords_found': len(matches),
        'text_length': len(text)
    }
