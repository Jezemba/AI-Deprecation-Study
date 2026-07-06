#!/usr/bin/env python3
"""
For the 947 (paper, already-deprecated-keyword) pairs that are not yet
labeled by the stratified audit, extract:
  - Combined_Windows  -- 50-words-before/50-words-after each occurrence
                         of the deprecated keyword in the paper, excluding
                         the references section.
  - Rich_Evidence     -- full text of the section(s) where the keyword
                         appeared, truncated to 1,500 words centered on
                         the first keyword occurrence per section.

Output: PDFAnalysis/results/deprecation_pairs_to_label.csv
"""
import csv
import os
import re
import string
import sys
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

UNIVERSE_CSV = "<results>/already_deprecated_pairs.csv"
AUDIT_CSV    = "<results>/stratified_sample_v1_final.csv"
OUT_CSV      = "<results>/deprecation_pairs_to_label.csv"

WINDOW_WORDS         = 50
MAX_WINDOWS_PER_PAIR = 8
MAX_SECTION_WORDS    = 1500


def norm(s):
    return re.sub(r'[-_\s@*.]', '', s.lower())

REFERENCE_HEADERS = [
    r'^#{1,6}\s*references?\s*$',
    r'^#{1,6}\s*bibliography\s*$',
    r'^#{1,6}\s*works?\s+cited\s*$',
]
END_REFERENCE_HEADERS = [
    r'^#{1,6}\s*appendix',
    r'^#{1,6}\s*acknowledgement',
    r'^#{1,6}\s*supplementary',
]
REF_PAT = re.compile('|'.join(REFERENCE_HEADERS), re.IGNORECASE)
END_REF_PAT = re.compile('|'.join(END_REFERENCE_HEADERS), re.IGNORECASE)

O1_O3_SUFFIXES = [
    'deepresearch', 'pro', 'mini', 'preview',
    '20250416', '20250626', '20250131', '20250610',
    '20241217', '20240912', '20250319',
]


def normalize_text(text):
    if not text:
        return ""
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = text.lower()
    return re.sub(r'\s+', ' ', text).strip()


def strip_references(text):
    out = []
    in_refs = False
    for line in text.split('\n'):
        if not in_refs and REF_PAT.match(line.strip()):
            in_refs = True
            continue
        if in_refs and (END_REF_PAT.match(line.strip()) or
                         re.match(r'^#{1,2}\s+[A-Z]', line.strip())):
            in_refs = False
        if not in_refs:
            out.append(line)
    return '\n'.join(out)


def parse_sections(text):
    sections = []
    current_heading = ''
    current_content = []
    for line in text.split('\n'):
        m = re.match(r'^(#{1,3})\s+(.+)$', line)
        if m:
            if current_content:
                sections.append((current_heading, '\n'.join(current_content)))
            current_heading = m.group(2).strip()
            current_content = []
        else:
            current_content.append(line)
    if current_content:
        sections.append((current_heading, '\n'.join(current_content)))
    return sections


def get_pattern(keyword):
    n = norm(keyword)
    if n == 'o1':
        return r'\bo1(?:' + '|'.join(O1_O3_SUFFIXES) + r')\b'
    if n == 'o3':
        return r'\bo3(?:' + '|'.join(O1_O3_SUFFIXES) + r')\b'
    return r'\b' + re.escape(n) + r'\b'


def keyword_centered_truncate(text, keyword, max_words):
    words = text.split()
    if len(words) <= max_words:
        return text
    kw = norm(keyword)
    for i, w in enumerate(words):
        if kw in re.sub(r'[^a-z0-9]', '', w.lower()):
            half = max_words // 2
            start = max(0, i - half)
            end = min(len(words), start + max_words)
            return ' '.join(words[start:end])
    return ' '.join(words[:max_words])


def get_title(text):
    for line in text.split('\n'):
        m = re.match(r'^#{1,2}\s+(.+)$', line)
        if m:
            return m.group(1).strip()[:120]
    return ""


def process_paper(md_path, keyword):
    """Return (title, combined_windows, sections_hit, rich_evidence, window_count)."""
    if not os.path.exists(md_path):
        return ('', '', '', '', 0)
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return ('', '', '', '', 0)

    title = get_title(text)
    text = strip_references(text)
    sections = parse_sections(text)

    pat = get_pattern(keyword)
    sections_with_hits = []   # list of (heading, full_section_content, [windows])
    for heading, content in sections:
        norm_text = normalize_text(content)
        words = norm_text.split()
        windows = []
        for m in re.finditer(pat, norm_text):
            wi = len(norm_text[:m.start()].split())
            start = max(0, wi - WINDOW_WORDS)
            end = min(len(words), wi + WINDOW_WORDS + 1)
            windows.append(' '.join(words[start:end]))
        if windows:
            sections_with_hits.append((heading.strip(), content, windows))

    if not sections_with_hits:
        return (title, '', '', '', 0)

    # Combined windows
    win_blocks = []
    n_windows = 0
    sections_hit = []
    for heading, _, windows in sections_with_hits:
        sections_hit.append(heading)
        for w in windows:
            n_windows += 1
            if n_windows > MAX_WINDOWS_PER_PAIR:
                break
            win_blocks.append(f"[Window {n_windows}] section: {heading}\n  {w}")
        if n_windows > MAX_WINDOWS_PER_PAIR:
            break

    combined = '\n\n'.join(win_blocks)
    sections_hit_str = ' | '.join(sections_hit)

    # Rich evidence: full sections, truncated to 1500 words centered on keyword
    rich_blocks = []
    for heading, content, _ in sections_with_hits:
        truncated = keyword_centered_truncate(content.strip(), keyword, MAX_SECTION_WORDS)
        rich_blocks.append(f"[Section: {heading}]\n{truncated}")
    rich = '\n\n'.join(rich_blocks)

    return (title, combined, sections_hit_str, rich, n_windows)


def main():
    # Universe: all 1,008 already-dep pairs
    universe = []
    with open(UNIVERSE_CSV) as f:
        for r in csv.DictReader(f):
            universe.append(r)
    print(f"Universe (already-deprecated pairs): {len(universe)}")

    # Subtract pairs already labeled by audit
    audit_labeled = {}
    with open(AUDIT_CSV) as f:
        for r in csv.DictReader(f):
            key = (r['File_Path'], norm(r['Sampled_Keyword']))
            audit_labeled[key] = {
                'Audit_Label':     r['Final_Label'],
                'Audit_Reasoning': r.get('Rich_Reasoning') or r.get('LLM_Reasoning', ''),
            }

    new_pairs = []
    reuse = []
    for r in universe:
        key = (r['File'], norm(r['Deprecated_Keyword']))
        if key in audit_labeled:
            r['Audit_Reusable'] = 'YES'
            r['Audit_Label']     = audit_labeled[key]['Audit_Label']
            r['Audit_Reasoning'] = audit_labeled[key]['Audit_Reasoning']
            reuse.append(r)
        else:
            r['Audit_Reusable'] = ''
            r['Audit_Label']     = ''
            r['Audit_Reasoning'] = ''
            new_pairs.append(r)

    print(f"  reusable from audit: {len(reuse)}")
    print(f"  new pairs to label:  {len(new_pairs)}")

    # Process each new pair: extract windows + rich evidence
    all_rows = []
    for i, r in enumerate(new_pairs, 1):
        if i % 100 == 0:
            print(f"  extracted {i}/{len(new_pairs)}")
        title, combined, sections_hit, rich, n_win = process_paper(
            r['File'], r['Deprecated_Keyword']
        )
        r['Paper_Title']       = title
        r['Combined_Windows']  = combined
        r['Sections_Hit']      = sections_hit
        r['Rich_Evidence']     = rich
        r['Window_Count']      = n_win
        r['Label']             = ''
        r['Reasoning']         = ''
        r['Reviewer']          = ''
        all_rows.append(r)

    # Also include reusable audit rows (so the output is the full 1,008-pair file)
    # but mark them as reused so we don't relabel.
    for r in reuse:
        # We still extract windows for these rows so reviewers can verify
        title, combined, sections_hit, rich, n_win = process_paper(
            r['File'], r['Deprecated_Keyword']
        )
        r['Paper_Title']       = title
        r['Combined_Windows']  = combined
        r['Sections_Hit']      = sections_hit
        r['Rich_Evidence']     = rich
        r['Window_Count']      = n_win
        r['Label']             = r.get('Audit_Label', '')
        r['Reasoning']         = r.get('Audit_Reasoning', '')
        r['Reviewer']          = 'audit_v1'
        all_rows.append(r)

    # Stable sort
    all_rows.sort(key=lambda x: (x['Year'], x['Venue'], x['Deprecated_Keyword'],
                                  x['File']))
    for i, r in enumerate(all_rows, start=1):
        r['Pair_ID'] = f"D{i:04d}"

    out_fields = [
        'Pair_ID', 'Paper_Title', 'Year', 'Venue', 'Deprecated_Keyword',
        'Sections_Hit', 'Window_Count',
        'Combined_Windows', 'Rich_Evidence',
        'Audit_Reusable', 'Audit_Label', 'Audit_Reasoning',
        'Label', 'Reasoning', 'Reviewer',
        'File',
    ]

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {OUT_CSV}")
    print(f"  Total pairs: {len(all_rows)}")
    print(f"  New (need labeling): {len(new_pairs)}")
    print(f"  Pre-labeled from audit: {len(reuse)}")

    # Stats on new pairs
    no_window = sum(1 for r in new_pairs if int(r.get('Window_Count', 0)) == 0)
    print(f"  New pairs with no extractable window: {no_window}")
    if word_counts := [int(r['Window_Count']) for r in new_pairs if int(r.get('Window_Count', 0)) > 0]:
        word_counts.sort()
        print(f"  Windows-per-pair distribution:")
        print(f"    median: {word_counts[len(word_counts)//2]}, "
              f"mean: {sum(word_counts)/len(word_counts):.1f}, "
              f"max: {word_counts[-1]}")


if __name__ == '__main__':
    main()
