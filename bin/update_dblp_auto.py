#!/usr/bin/env python
"""
Import entry from DBLP according to given search input.
"""

import argparse
import logging
from copy import deepcopy

import requests
import time

import bibtex_dblp.config
import bibtex_dblp.database
import bibtex_dblp.dblp_api
import bibtex_dblp.io
from bibtex_dblp.dblp_api import BibFormat


def main():
    parser = argparse.ArgumentParser(description='Update entries in bibliography via DBLP.')

    parser.add_argument('infile', help='Input bibtex file', type=str)
    parser.add_argument('--out', '-o',
                        help='Output bibtex file. If no output file is given, the input file will be overwritten.',
                        type=str, default=None)
    parser.add_argument('--format', '-f', help='DBLP format type to convert into', type=BibFormat,
                        choices=list(BibFormat), default=BibFormat.condensed)
    parser.add_argument('--max-results', help="Maximal number of search results to display.", type=int,
                        default=bibtex_dblp.config.MAX_SEARCH_RESULTS)

    parser.add_argument('--verbose', '-v', help='print more output', action="store_true")
    parser.add_argument('--semiauto', '-a', help='enable semi-auto mode', action="store_true")

    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG if args.verbose else logging.INFO)
    outfile = args.infile if args.out is None else args.out
    bib_format = args.format
    max_search_results = args.max_results
    semiauto=args.semiauto;
    # Load bibliography
    bib = bibtex_dblp.database.load_from_file(args.infile)
    new_entries = deepcopy(bib.entries)
    missings=[];
    # Iterate over all entries
    no_changes = 0
    for entry_str, entry in bib.entries.items():
        if(semiauto):
            time.sleep(10);

        # Check for id
        dblp_id = bibtex_dblp.dblp_api.extract_dblp_id(entry)
        if dblp_id is not None:
            continue

        if 'author' in entry.persons:
            authors = ", ".join([str(author) for author in entry.persons['author']])
        else:
            authors = ""
        if 'title' in entry.fields:
            title = entry.fields['title']
        else:
            title = ""
        search_words = "{} {}".format(authors, title)
        logging.info("Search: {}".format(search_words))
        try:
            search_results = bibtex_dblp.dblp_api.search_publication(search_words,
                                                                     max_search_results=max_search_results);
            val_results=[];
            for r in range(len(search_results.results)):
                if str(search_results.results[r].publication).find("CoRR")==-1:
                    val_results.append(r+1);

        except requests.exceptions.HTTPError as err:
            logging.warning("Search request returned error {}. Skipped this entry.".format(err))
            continue
        if search_results.total_matches == 0:
            # Try once again with only the title
            logging.debug("Search: {}".format(title))
            try:
                search_results = bibtex_dblp.dblp_api.search_publication(title, max_search_results=max_search_results)
            except requests.exceptions.HTTPError as err:
                logging.warning("Search request returned error {}. Skipped this entry.".format(err))
                continue

            # No luck -> try next entry
            if search_results.total_matches == 0:
                print("The search returned no matches.");
                missings.append(entry.fields['title']);
                continue

        print("The search returned {} matches:".format(search_results.total_matches))
        if search_results.total_matches > max_search_results:
            print("Displaying only the first {} matches.".format(max_search_results))
        for i in range(len(search_results.results)):
            result = search_results.results[i]
            print("({})\t{}".format(i + 1, result.publication))
        if(semiauto):
            if(len(val_results)>1):
            # Let user select correct publication
                select = bibtex_dblp.io.get_user_number("Select the intended publication (0 to abort): ", 0,
                                                        search_results.total_matches)
            elif(len(val_results)==0):
                select=1;
            else:
                select=val_results[0];
        else:
             select = bibtex_dblp.io.get_user_number("Select the intended publication (0 to abort): ", 0,
                                                        search_results.total_matches);

        if select == 0:
            print("Cancelled.")
            continue

        publication = search_results.results[select - 1].publication
        result_dblp = bibtex_dblp.dblp_api.get_bibtex(publication.key, bib_format=bib_format)
        data = bibtex_dblp.database.parse_bibtex(result_dblp)
        assert len(data.entries) == 1

        # Update entries
        key = next(iter(data.entries))
        new_entries[entry_str] = data.entries[key]
        no_changes += 1
        logging.debug("Updated entry for '{}'".format(data.entries))
    # Set new entries
    bib.entries = new_entries

    # Write to file
    bibtex_dblp.database.write_to_file(bib, outfile)
    logging.info("Written to {}".format(outfile))


if __name__ == "__main__":
    main()
