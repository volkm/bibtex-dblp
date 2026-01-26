#!/usr/bin/env python
"""
Apply modifications on the bibtex entries.
"""

import argparse
import logging
from pathlib import Path
import re

import bibtex_dblp.database


def main():
    parser = argparse.ArgumentParser(description="Apply modifications on the bibtex file.")

    parser.add_argument("infile", help="Input bibtex file", type=Path)
    parser.add_argument("--out", "-o", help="Output bibtex file. If no output file is given, the input file will be overwritten.", type=Path, default=None)
    parser.add_argument("--no-escape", help="Disable escaping of underscores in URLs", action="store_true")
    parser.add_argument("--no-timestamp", help="Remove timestamp field (if present)", action="store_true")
    parser.add_argument("--no-biburl", help="Remove biburl field (if present)", action="store_true")
    parser.add_argument("--no-bibsource", help="Remove bibsource field (if present)", action="store_true")

    parser.add_argument("--verbose", "-v", help="print more output", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG if args.verbose else logging.INFO)

    outfile = args.infile if args.out is None else args.out

    bib = bibtex_dblp.database.load_from_file(args.infile)
    # Apply modifications
    bib = bibtex_dblp.database.modify_entries(
        bib, remove_escapes=args.no_escape, remove_timestamp=args.no_timestamp, remove_biburl=args.no_biburl, remove_bibsource=args.no_bibsource
    )
    bibtex_dblp.database.write_to_file(bib, outfile)
    if args.no_escape:
        # Need to manually remove escape characters which are automatically added again by pybtex to ensure LaTeX compatibility
        out_lines = []
        for line in outfile.read_text(encoding="utf-8").splitlines(keepends=True):
            # Detect start of a doi or url field
            if re.match(r"\s*(doi|url)\s*=", line, flags=re.IGNORECASE):
                # Remove backslash
                line = re.sub(r"\\_", r"_", line)
            out_lines.append(line)
        outfile.write_text("".join(out_lines), encoding="utf-8")

    logging.info("Written to {}".format(outfile))


if __name__ == "__main__":
    main()
