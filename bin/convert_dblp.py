#!/usr/bin/env python
"""
Convert DBLP entries in a given bibliography according to the specific DBLP format (condensed, standard or crossref).
"""

import argparse
import logging

import bibtex_dblp.database
from bibtex_dblp.dblp_api import BibFormat


def main():
    parser = argparse.ArgumentParser(description='Convert DBLP entries to specific format (condensed, standard, crossref).')

    parser.add_argument('infile', help='Input bibtex file', type=str)
    parser.add_argument('--out', '-o', help='Output bibtex file. If no output file is given, the input file will be overwritten.', type=str, default=None)
    parser.add_argument('--format', '-f', help='DBLP format type to convert into', type=BibFormat, choices=list(BibFormat), default=BibFormat.condensed)

    parser.add_argument('--verbose', '-v', help='print more output', action="store_true")
    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG if args.verbose else logging.INFO)

    outfile = args.infile if args.out is None else args.out

    bib = bibtex_dblp.database.load_from_file(args.infile)
    bib, no_changes = bibtex_dblp.database.convert_dblp_entries(bib, bib_format=args.format)
    logging.info("Updated {} entries (out of {}) from DBLP".format(no_changes, len(bib.entries)))
    bibtex_dblp.database.write_to_file(bib, outfile)
    logging.info("Written to {}".format(outfile))


if __name__ == "__main__":
    main()
