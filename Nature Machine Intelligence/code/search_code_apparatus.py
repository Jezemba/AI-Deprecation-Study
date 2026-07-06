#!/usr/bin/env python3
"""
GitHub-repo-analysis equivalent for the NMI supplementary CODE bundles.

Treats each article's extracted code as one "repo": walks every ASCII-readable
file and searches for the 248 model identifiers, using the SAME engine as the
paper's repo analysis (search_recovered_repos.py): chardet-based text detection,
substring matching, o1/o3/o4 disambiguation, and substring-dedup of matches.

Output: results_MachineIntelligence/code_apparatus_search.csv (one row/article)
"""
import csv, os, re, sys
from pathlib import Path
import chardet

CODE_ROOT = "/home/aipexws3/Jessica/Dataset_Ghost/PDFs/MachineIntelligenceSupplementaryCode/code_apparatus"
KEYWORDS_FILE = "/home/aipexws3/Jessica/GhostAI/PDFAnalysis/results_MachineIntelligence/keywords_union.txt"
OUT = "/home/aipexws3/Jessica/GhostAI/PDFAnalysis/results_MachineIntelligence/code_apparatus_search.csv"

# ---- engine copied verbatim from search_recovered_repos.py ----
EXCLUDE_STANDALONE = {'o1', 'o3', 'o4'}
VALID_O1_O3_PATTERNS = [
    r'o1[\-_]?preview', r'o1[\-_]?mini', r'o1[\-_]?pro', r'o1[\-_]?20\d{6}',
    r'o3[\-_]?mini', r'o3[\-_]?pro', r'o3[\-_]?20\d{6}', r'o4[\-_]?mini',
]
BINARY_EXT = {
    '.exe', '.dll', '.so', '.dylib', '.bin', '.dat',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
    '.mp3', '.mp4', '.avi', '.mov', '.wav',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.pyc', '.pyo', '.class', '.o', '.obj',
    '.woff', '.woff2', '.ttf', '.eot',
    '.pkl', '.pickle', '.npy', '.npz',
}


def is_text_file(p: Path) -> bool:
    if p.suffix.lower() == '.pdf' or p.suffix.lower() in BINARY_EXT:
        return False
    try:
        with open(p, 'rb') as f:
            chunk = f.read(8192)
        if not chunk or b'\x00' in chunk:
            return False
        return chardet.detect(chunk)['encoding'] is not None
    except Exception:
        return False


def read_text_file(p: Path):
    try:
        with open(p, 'rb') as f:
            raw = f.read()
        enc = chardet.detect(raw)['encoding'] or 'utf-8'
        return raw.decode(enc, errors='ignore')
    except Exception:
        return None


def is_valid_o1_o3_match(text, start, kw):
    ctx = text[max(0, start-5):min(len(text), start+len(kw)+20)].lower()
    return any(re.search(p, ctx) for p in VALID_O1_O3_PATTERNS)


def find_keywords_in_text(text, keywords):
    tl = text.lower()
    matched = set()
    for kw in keywords:
        k = kw.lower()
        if k in EXCLUDE_STANDALONE:
            for m in re.finditer(r'\b' + re.escape(k) + r'\b', tl):
                if is_valid_o1_o3_match(tl, m.start(), k):
                    matched.add(kw); break
        else:
            if k in tl:
                matched.add(kw)
    longest = set()
    for kw in matched:
        if not any(kw != o and kw.lower() in o.lower() for o in matched):
            longest.add(kw)
    return longest


def count_occurrences(text, kw):
    return text.lower().count(kw.lower())


def load_keywords():
    kws = []
    with open(KEYWORDS_FILE) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith('#'):
                kws.append(s)
    return kws


def search_bundle(bundle_dir, keywords):
    """Walk one article's code dir; return (matched_keywords, occ_by_kw, n_text, n_total)."""
    matched = set()
    occ = {}
    n_text = n_total = 0
    for root, _, files in os.walk(bundle_dir):
        for fn in files:
            p = Path(root) / fn
            n_total += 1
            if not is_text_file(p):
                continue
            txt = read_text_file(p)
            if not txt:
                continue
            n_text += 1
            found = find_keywords_in_text(txt, keywords)
            for kw in found:
                matched.add(kw)
                occ[kw] = occ.get(kw, 0) + count_occurrences(txt, kw)
    return matched, occ, n_text, n_total


def main():
    keywords = load_keywords()
    print(f"Loaded {len(keywords)} keywords")
    rows = []
    # code_apparatus/<year>/<article_id>/  (search the article dir = all its bundles)
    for year in sorted(os.listdir(CODE_ROOT)):
        ydir = os.path.join(CODE_ROOT, year)
        if not os.path.isdir(ydir):
            continue
        for art in sorted(os.listdir(ydir)):
            adir = os.path.join(ydir, art)
            if not os.path.isdir(adir):
                continue
            matched, occ, n_text, n_total = search_bundle(adir, keywords)
            total_occ = sum(occ.values())
            rows.append({
                'year': year, 'article_id': art,
                'files_total': n_total, 'files_text_searched': n_text,
                'unique_keywords': len(matched),
                'total_occurrences': total_occ,
                'keywords_found': ','.join(sorted(matched)),
                'match_details': '; '.join(f"{k}:{occ[k]}" for k in sorted(occ, key=lambda x: -occ[x])),
                'has_keywords': len(matched) > 0,
            })
            tag = f"{len(matched)} kw" if matched else "-"
            print(f"  {year}/{art}: {n_text}/{n_total} text files, {tag}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    nwith = sum(1 for r in rows if r['has_keywords'])
    print(f"\n{nwith}/{len(rows)} code bundles contain >=1 model keyword")
    print(f"[saved] {OUT}")


if __name__ == "__main__":
    main()
