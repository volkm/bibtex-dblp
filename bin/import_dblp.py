#!/usr/bin/env python
"""
Import entry from DBLP according to given search input.
"""

import argparse
import logging

import bibtex_dblp.config
import bibtex_dblp.io
import bibtex_dblp.dblp_api
from bibtex_dblp.dblp_api import BibFormat


def main():
    parser = argparse.ArgumentParser(description='Import entry from DBLP according to given search input from cli.')

    parser.add_argument('--query', '-q', help='The query to search for the publication. If none is given the query is obtained from CLI input.', type=str, default=None)
    parser.add_argument('--out', '-o', help='Output bibtex file where the imported entry will be appended. If no output file is given, the bibtex is printed to the CLI.', type=str,
                        default=None)
    parser.add_argument('--format', '-f', help='DBLP format type to convert into.', type=BibFormat, choices=list(BibFormat), default=BibFormat.condensed)
    parser.add_argument('--max-results', help="Maximal number of search results to display.", type=int, default=bibtex_dblp.config.MAX_SEARCH_RESULTS)

    parser.add_argument('--verbose', '-v', help='print more output', action="store_true")
    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG if args.verbose else logging.INFO)
    max_search_results = args.max_results

    if args.query:
        search_words = args.query
    else:
        search_words = bibtex_dblp.io.get_user_input("Give the publication title to search for: ")
    # Search for publications
    search_results = bibtex_dblp.dblp_api.search_publication(search_words, max_search_results=max_search_results)
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
    pub_bibtex = bibtex_dblp.dblp_api.get_bibtex(publication.key, bib_format=args.format)
    if args.out:
        with open(args.out, "a") as f:
            f.write(pub_bibtex)
        logging.info("Bibtex file appended to {}.".format(args.out))
    else:
        logging.info("Selected bibtex entry:\n")
        print(pub_bibtex)


if __name__ == "__main__":
    main()
