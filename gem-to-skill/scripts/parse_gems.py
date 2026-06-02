#!/usr/bin/env python3
"""Parse a Google Takeout Gemini Gems export into structured JSON.

The Takeout export (`gemini_gems_data.html`) is a single flat HTML file with one
repeating block per gem:

    <b>Name:</b>{name}<br>
    <b>Instructions:</b>{instructions}<br>
    <b>Files:</b><br>
    <a href="{url}">{filename}</a><br>
    ... (zero or more <a> links) ...

This script turns that into `gems.json`: a list of gems, each with its name,
instructions, and a classified list of knowledge files. Classification is purely
deterministic (host + file extension), so no model guessing is needed to decide
how hard a gem is to convert.

Stdlib only — runs under any Python 3, no third-party deps. That keeps the whole
meta-skill portable across runtimes and models.

Usage:
    python parse_gems.py <path-to-gemini_gems_data.html | dir> [-o gems.json]
    python parse_gems.py <...> --pretty      # human-readable summary to stdout
"""

import argparse
import html
import json
import os
import re
import sys
from urllib.parse import urlparse, parse_qs

# --- Tier definitions -------------------------------------------------------
# A gem's difficulty is the hardest tier among its files (or "simple" if none).
TIER_SIMPLE = "simple"               # instructions only, no knowledge files
TIER_DIRECT = "direct_download"      # public link, fetchable with curl
TIER_DRIVE = "drive_doc"             # Google Drive doc, needs auth/connector
TIER_IMAGE = "image_knowledge"       # image used as style reference (hardest)

# Ordering so we can pick the "hardest" tier for a gem.
TIER_RANK = {TIER_SIMPLE: 0, TIER_DIRECT: 1, TIER_DRIVE: 2, TIER_IMAGE: 3}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".svg"}

# Hosts that serve a direct, unauthenticated download (Takeout's own blob export).
DIRECT_HOSTS = ("contribution.usercontent.google.com",)


def _ext(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def classify_file(url: str, filename: str) -> str:
    """Decide the tier of a single knowledge file from its host + extension."""
    host = (urlparse(url).hostname or "").lower()
    ext = _ext(filename)

    # Direct download blobs from the Takeout export itself.
    if any(host.endswith(h) for h in DIRECT_HOSTS):
        # Even a direct image is fetchable, but its *use* is still as style
        # reference, so flag images as image_knowledge regardless of host.
        return TIER_IMAGE if ext in IMAGE_EXTS else TIER_DIRECT

    # Anything else (Drive, Photos, googleusercontent thumbnails): images are
    # the hardest case (style references), other docs need a Drive connector.
    if ext in IMAGE_EXTS:
        return TIER_IMAGE
    return TIER_DRIVE


def gem_tier(files: list) -> str:
    """A gem is as hard as its hardest file; instructions-only is simple."""
    if not files:
        return TIER_SIMPLE
    return max((f["tier"] for f in files), key=lambda t: TIER_RANK[t])


# --- Parsing ----------------------------------------------------------------
# The export has no per-gem wrapper element — gems are delimited only by the
# repeating "Name:" label. We normalize <br> to newlines, unescape entities,
# then split on the bold field labels.

_A_TAG = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def _strip_tags(fragment: str) -> str:
    return html.unescape(_TAG.sub("", fragment)).strip()


def parse_html(text: str) -> list:
    """Parse the raw export HTML into a list of gem dicts."""
    # Split into one chunk per gem on the "Name:" label.
    chunks = re.split(r"<b>\s*Name:\s*</b>", text, flags=re.IGNORECASE)[1:]
    gems = []
    for chunk in chunks:
        # Name is everything up to the Instructions label.
        m = re.search(r"(.*?)<b>\s*Instructions:\s*</b>(.*?)(?:<b>\s*Files:\s*</b>(.*))?$",
                      chunk, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            continue
        name = _strip_tags(m.group(1))
        instructions = _strip_tags(m.group(2))
        files_block = m.group(3) or ""

        files = []
        for url, label in _A_TAG.findall(files_block):
            url = html.unescape(url).strip()
            filename = _strip_tags(label) or _filename_from_url(url)
            host = (urlparse(url).hostname or "").lower()
            files.append({
                "filename": filename,
                "url": url,
                "host": host,
                "tier": classify_file(url, filename),
            })

        gems.append({
            "name": name,
            "instructions": instructions,
            "files": files,
            "tier": gem_tier(files),
        })
    return gems


def _filename_from_url(url: str) -> str:
    """Best-effort filename: prefer a `filename` query param, else URL path."""
    qs = parse_qs(urlparse(url).query)
    if "filename" in qs and qs["filename"]:
        return qs["filename"][0]
    path = urlparse(url).path
    return os.path.basename(path) or url


def find_export(path: str) -> str:
    """Resolve a file or directory to the gems HTML file."""
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for root, _dirs, names in os.walk(path):
            for n in names:
                if n == "gemini_gems_data.html":
                    return os.path.join(root, n)
    raise FileNotFoundError(f"Could not find gemini_gems_data.html under: {path}")


def summarize(gems: list) -> str:
    lines = [f"Found {len(gems)} gem(s):", ""]
    for g in gems:
        nfiles = len(g["files"])
        lines.append(f"  • {g['name']}  [{g['tier']}]  ({nfiles} file(s))")
        for f in g["files"]:
            lines.append(f"      - {f['filename']}  [{f['tier']}]  {f['host']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Parse Gemini Gems Takeout export into JSON.")
    ap.add_argument("path", help="Path to gemini_gems_data.html or a directory to search.")
    ap.add_argument("-o", "--output", help="Write JSON here (default: stdout).")
    ap.add_argument("--pretty", action="store_true", help="Print a human-readable summary instead of JSON.")
    args = ap.parse_args(argv)

    export = find_export(args.path)
    with open(export, encoding="utf-8") as fh:
        gems = parse_html(fh.read())

    if args.pretty:
        print(summarize(gems))
        return 0

    payload = json.dumps(gems, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(f"Wrote {len(gems)} gem(s) to {args.output}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
