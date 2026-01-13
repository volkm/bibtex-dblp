#!/usr/bin/env python
"""
Import entry from DBLP according to given search input.
"""

import argparse
import logging
import pyperclip
from pathlib import Path

import bibtex_dblp.database
import bibtex_dblp.dblp_api
import bibtex_dblp.io
from bibtex_dblp.dblp_api import BibFormat, DblpSession


def main():
    parser = argparse.ArgumentParser(description="Import entry from DBLP according to given search input from cli.")

    parser.add_argument(
        "--query", "-q", help="The query to search for the publication. If none is given the query is obtained from CLI input.", type=str, default=None
    )
    parser.add_argument(
        "--bib",
        "-b",
        help="Bibtex file where the imported entry will be appended. If no bibtex file is given, the bibtex is printed to the CLI.",
        type=Path,
        default=None,
    )
    parser.add_argument("--format", "-f", help="DBLP format type to convert into.", type=BibFormat, choices=list(BibFormat), default=BibFormat.condensed)
    parser.add_argument("--max-results", help="Maximal number of search results to display.", type=int, default=30)
    parser.add_argument("--sleep-time", "-t", help="Sleep time (in seconds) between requests. Can prevent errors with too many requests)", type=int, default=5)

    parser.add_argument("--verbose", "-v", help="print more output", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG if args.verbose else logging.INFO)
    max_search_results = args.max_results

    bib = None
    if args.bib is not None:
        # Load bibliography
        bib = bibtex_dblp.database.load_from_file(args.bib)

    if args.query:
        search_words = args.query
    else:
        search_words = bibtex_dblp.io.get_user_input("Give the publication title to search for: ")

    if not search_words:
        print("No search terms. Cancelled.")
        exit(1)

    # Search for publications
    if bib is not None:
        # Check if publication already exists
        bib_result = bibtex_dblp.database.search(bib, search_words)
        if bib_result:
            print("The bibliography already contains the following matches:")
            for i in range(len(bib_result)):
                print("({})\t{}".format(i + 1, bibtex_dblp.database.print_entry(bib_result[i][0])))
            select = bibtex_dblp.io.get_user_number("Select the intended publication (0 to search online): ", 0, len(bib_result))
            if select > 0:
                selected_entry = bib_result[select - 1][0]
                pyperclip.copy(selected_entry.key)
                logging.info("Copied cite key '{}' to clipboard.".format(selected_entry.key))
                exit(0)

    session = DblpSession(wait_time=args.sleep_time)
    search_results = bibtex_dblp.dblp_api.search_publication(session, search_words, max_search_results=max_search_results)
    if search_results.total_matches == 0:
        print("The search returned no matches.")
        exit(1)

    print("The search returned {} matches:".format(search_results.total_matches))
    if search_results.total_matches > max_search_results:
        print("Displaying only the first {} matches.".format(max_search_results))
    for i in range(len(search_results.results)):
        result = search_results.results[i]
        print("({})\t{}".format(i + 1, result.publication))

    # Let user select correct publication
    select = bibtex_dblp.io.get_user_number("Select the intended publication (0 to abort): ", 0, search_results.total_matches)
    if select == 0:
        print("Cancelled.")
        exit(1)

    publication = search_results.results[select - 1].publication
    pub_bibtex = bibtex_dblp.dblp_api.get_bibtex(session, publication.key, bib_format=args.format)
    if args.bib:
        with open(args.bib, "a") as f:
            f.write(pub_bibtex)
        logging.info("Bibtex file appended to {}.".format(args.bib))
        pyperclip.copy(publication.cite_key())
        logging.info("Copied cite key '{}' to clipboard.".format(publication.cite_key()))
    else:
        pyperclip.copy(pub_bibtex)
        logging.info("Selected bibtex entry:\n{}".format(pub_bibtex))
        logging.info("Copied selected bibtex entry to clipboard.")


if __name__ == "__main__":
    main()
