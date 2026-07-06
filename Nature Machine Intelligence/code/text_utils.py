"""
Text processing utilities for keyword search.
Handles punctuation removal and text normalization.
"""
import re
import string


def remove_punctuation(text: str) -> str:
    """
    Remove all punctuation from text.

    Args:
        text: Input text string

    Returns:
        Text with all punctuation removed
    """
    if not text:
        return ""

    # Create translation table that maps all punctuation to None
    translator = str.maketrans('', '', string.punctuation)

    # Remove punctuation
    cleaned = text.translate(translator)

    return cleaned


def normalize_text(text: str, lowercase: bool = True, remove_punct: bool = True) -> str:
    """
    Normalize text for searching: remove punctuation, convert to lowercase, normalize whitespace.

    Args:
        text: Input text string
        lowercase: Convert to lowercase if True
        remove_punct: Remove punctuation if True

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Remove punctuation if requested
    if remove_punct:
        text = remove_punctuation(text)

    # Convert to lowercase if requested
    if lowercase:
        text = text.lower()

    # Normalize whitespace (collapse multiple spaces/newlines into single space)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def normalize_keyword(keyword: str, lowercase: bool = True, remove_punct: bool = True) -> str:
    """
    Normalize a keyword for searching.

    Args:
        keyword: Input keyword string
        lowercase: Convert to lowercase if True
        remove_punct: Remove punctuation if True

    Returns:
        Normalized keyword
    """
    return normalize_text(keyword, lowercase=lowercase, remove_punct=remove_punct)


def load_keywords_from_file(file_path: str, lowercase: bool = True, remove_punct: bool = True) -> list:
    """
    Load keywords from a file and normalize them.
    Each line in the file should contain one keyword.

    Args:
        file_path: Path to the keywords file
        lowercase: Convert keywords to lowercase if True
        remove_punct: Remove punctuation from keywords if True

    Returns:
        List of normalized keywords
    """
    keywords = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                keyword = line.strip()
                if keyword and not keyword.startswith('#'):  # Skip empty lines and comments
                    normalized = normalize_keyword(keyword, lowercase=lowercase, remove_punct=remove_punct)
                    if normalized:  # Only add non-empty normalized keywords
                        keywords.append(normalized)
    except FileNotFoundError:
        print(f"Error: Keywords file not found at {file_path}")
        raise
    except Exception as e:
        print(f"Error loading keywords from {file_path}: {e}")
        raise

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords
