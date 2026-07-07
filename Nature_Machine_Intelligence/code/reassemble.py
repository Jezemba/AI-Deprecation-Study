#!/usr/bin/env python3
"""
Reassemble + verify + extract the NMI split archives using chunk_manifest.csv.

Handles the mess Google Drive makes:
  - parts named *.zip.partNNN that must be CONCATENATED (not unzipped) in order
  - parts possibly wrapped inside one or more outer Drive .zip downloads
  - nested zips inside the supplementary assets (extracted recursively)

Every chunk and every rebuilt archive is checked against the SHA-256 in
chunk_manifest.csv, so a corrupt/partial download is caught instead of
silently producing a broken extract.

Usage:
  reassemble.py --staging <dir-with-downloaded-parts> [--archives code|all|<name>]
                [--keep-zip] [--no-extract]

Default --archives is "code" (just NMI_code_only_2022_2025.zip, ~145 MB / 2 parts),
which is the code apparatus. Use "all" for the full per-year supplementary (~18 GB).
"""
import argparse, csv, hashlib, os, re, shutil, sys, zipfile
from collections import defaultdict

# canonical part name = everything up to and including .partNNN
# (Google Drive sometimes appends a spurious ".zip" to a part file)
PART_RE = re.compile(r"(.+\.zip\.part\d+)", re.IGNORECASE)


def canon_part(filename):
    m = PART_RE.match(filename)
    return m.group(1) if m else None

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(os.path.dirname(HERE), "data", "chunk_manifest.csv")
CODE_ARCHIVE = "NMI_code_only_2022_2025.zip"


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()


def load_manifest():
    archives = defaultdict(lambda: {"size": 0, "sha": "", "chunks": []})
    with open(MANIFEST) as f:
        for r in csv.DictReader(f):
            a = archives[r["archive_name"]]
            a["size"] = int(r["archive_size"])
            a["sha"] = r["archive_sha256"]
            a["chunks"].append({
                "name": r["chunk_name"],
                "order": int(r["reassembly_order"]),
                "size": int(r["chunk_size"]),
                "sha": r["chunk_sha256"],
            })
    for a in archives.values():
        a["chunks"].sort(key=lambda c: c["order"])
    return archives


def index_parts(staging):
    """Find every *.partNNN on disk under staging, unwrapping outer zips first."""
    # 1) unwrap any outer Drive zips that themselves contain part files
    for root, _, files in os.walk(staging):
        for fn in files:
            if fn.lower().endswith(".zip"):
                fp = os.path.join(root, fn)
                try:
                    with zipfile.ZipFile(fp) as z:
                        names = z.namelist()
                    if any(".part" in n.lower() for n in names):
                        dest = fp + "._unwrapped"
                        os.makedirs(dest, exist_ok=True)
                        with zipfile.ZipFile(fp) as z:
                            z.extractall(dest)
                        print(f"  unwrapped outer zip: {fn}")
                except zipfile.BadZipFile:
                    pass
    # 2) index all part files by CANONICAL name (tolerating a spurious .zip suffix)
    found = defaultdict(list)
    for root, _, files in os.walk(staging):
        for fn in files:
            c = canon_part(fn)
            if c:
                found[c].append(os.path.join(root, fn))
    return found


def recursive_unzip(top, depth=0):
    """Extract any .zip found under top, in place, recursively."""
    if depth > 8:
        return
    again = []
    for root, _, files in os.walk(top):
        for fn in files:
            if fn.lower().endswith(".zip"):
                fp = os.path.join(root, fn)
                out = fp[:-4] + "_extracted"
                try:
                    with zipfile.ZipFile(fp) as z:
                        os.makedirs(out, exist_ok=True)
                        z.extractall(out)
                    again.append(out)
                except zipfile.BadZipFile:
                    print(f"    [warn] bad nested zip, left as-is: {os.path.relpath(fp, top)}")
    for o in again:
        recursive_unzip(o, depth + 1)


def pick_part(c, parts_on_disk):
    """Return the on-disk path for chunk c (size match first, else first candidate)."""
    cands = parts_on_disk.get(c["name"], [])
    for p in cands:
        if os.path.getsize(p) == c["size"]:
            return p
    return cands[0] if cands else None


def rebuild(name, info, parts_on_disk, args):
    chunks = info["chunks"]
    resolved = {c["name"]: pick_part(c, parts_on_disk) for c in chunks}
    missing = [c["name"] for c in chunks if resolved[c["name"]] is None]
    if missing:
        print(f"[SKIP] {name}: missing {len(missing)}/{len(chunks)} parts, e.g. {missing[:2]}")
        return False
    print(f"[{name}] verifying {len(chunks)} parts...")
    for c in chunks:
        p = resolved[c["name"]]
        if os.path.getsize(p) != c["size"] or sha256(p) != c["sha"]:
            print(f"  [FAIL] checksum/size mismatch on {c['name']} — re-download this part")
            return False
    zip_path = os.path.join(args.staging, name)
    print(f"[{name}] concatenating -> {name}")
    with open(zip_path, "wb") as out:
        for c in chunks:
            with open(resolved[c["name"]], "rb") as fin:
                shutil.copyfileobj(fin, out, 1 << 22)
    print(f"[{name}] verifying rebuilt archive sha256...")
    if sha256(zip_path) != info["sha"]:
        print(f"  [FAIL] rebuilt archive sha mismatch — parts present but corrupt")
        return False
    print(f"  [OK] archive verified ({os.path.getsize(zip_path)/1e6:.0f} MB)")
    if not args.no_extract:
        dest = os.path.join(args.staging, name[:-4])
        os.makedirs(dest, exist_ok=True)
        print(f"[{name}] extracting -> {os.path.basename(dest)}/ (recursive)")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(dest)
        recursive_unzip(dest)
        if not args.keep_zip:
            os.remove(zip_path)
    print(f"[{name}] DONE\n")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", required=True, help="dir containing downloaded part files")
    ap.add_argument("--archives", default="code", help="'code' (default), 'all', or an archive name")
    ap.add_argument("--keep-zip", action="store_true", help="keep the rebuilt .zip after extracting")
    ap.add_argument("--no-extract", action="store_true", help="rebuild+verify only, don't unzip")
    args = ap.parse_args()

    archives = load_manifest()
    if args.archives == "code":
        wanted = [CODE_ARCHIVE]
    elif args.archives == "all":
        wanted = list(archives)
    else:
        wanted = [args.archives]

    print(f"Indexing parts under {args.staging} ...")
    parts = index_parts(args.staging)
    print(f"  found {len(parts)} part files on disk\n")

    ok = 0
    for name in wanted:
        if name not in archives:
            print(f"[SKIP] unknown archive: {name}")
            continue
        if rebuild(name, archives[name], parts, args):
            ok += 1
    print(f"Completed {ok}/{len(wanted)} archive(s). Output under {args.staging}")


if __name__ == "__main__":
    main()
