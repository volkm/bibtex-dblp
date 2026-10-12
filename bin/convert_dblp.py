#!/usr/bin/env python
"""
Convert DBLP entries in a given bibliography according to the specific DBLP format (condensed, standard or crossref).
"""

import argparse
import logging
import requests
from pathlib import Path

import bibtex_dblp.database
import bibtex_dblp.dblp_api
from bibtex_dblp.dblp_api import BibFormat


def main():
    parser = argparse.ArgumentParser(description="Convert DBLP entries to specific format (condensed, standard, crossref).")

    parser.add_argument("infile", help="Input bibtex file", type=Path)
    parser.add_argument("--out", "-o", help="Output bibtex file. If no output file is given, the input file will be overwritten.", type=Path, default=None)
    parser.add_argument("--format", "-f", help="DBLP format type to convert into", type=BibFormat, choices=list(BibFormat), default=BibFormat.condensed)
    parser.add_argument("--sleep-time", "-t", help="Sleep time (in seconds) between requests. Can prevent errors with too many requests)", type=int, default=5)
    bibtex_dblp.dblp_api.add_auth_arguments(parser)

    parser.add_argument("--verbose", "-v", help="print more output", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG if args.verbose else logging.INFO)

    outfile = args.infile if args.out is None else args.out

    bib = bibtex_dblp.database.load_from_file(args.infile)
    session = bibtex_dblp.dblp_api.session_from_args(args)
    try:
        bib, no_changes = bibtex_dblp.database.convert_dblp_entries(session, bib, bib_format=args.format)
    except (requests.exceptions.HTTPError, bibtex_dblp.dblp_api.DblpApiError) as err:
        print("Conversion failed: {}".format(err))
        exit(1)
    logging.info("Updated {} entries (out of {}) from DBLP".format(no_changes, len(bib.entries)))
    bibtex_dblp.database.write_to_file(bib, outfile)
    logging.info("Written to {}".format(outfile))


if __name__ == "__main__":
    main()
