import logging
import pybtex.database

import bibtex_dblp.dblp_api as dblp_api
import bibtex_dblp.search
from bibtex_dblp.config import BIB_FORMATS, CONDENSED, CROSSREF


def load_from_file(infile):
    """
    Load bibliography from file.
    :param infile: Path of input file.
    :return: Bibiliography in pybtex format.
    """
    return pybtex.database.parse_file(infile, bib_format="bibtex")


def write_to_file(bib, outfile):
    """
    Write bibliography to file.
    :param bib: Bibliography in pybtex format.
    :param outfile: Path of output file.
    """
    bib.to_file(outfile, bib_format="bibtex")


def parse_bibtex(bibtex):
    """
    Parse bibtex string into pybtex format.
    :param bibtex: String containing bibtex information.
    :return: Entry in pybtex format.
    """
    return pybtex.database.parse_string(bibtex, bib_format="bibtex")


def convert_dblp_entries(bib, bib_format=CONDENSED):
    """
    Convert bibtex entries according to DBLP bibtex format.
    :param bib: Bibliography in pybtex format.
    :param bib_format: Bibtex format of DBLP.
    :return: converted bibliography, number of changed entries
    """
    assert(bib_format in BIB_FORMATS)
    logging.debug("Convert to format '{}'".format(bib_format))
    no_changes = 0
    for entry_str, entry in bib.entries.items():
        # Check for id
        dblp_id = dblp_api.extract_dblp_id(entry)
        if dblp_id is not None:
            logging.debug("Found id '{}'".format(dblp_id))
            result_dblp = dblp_api.get_bibtex(dblp_id, bib_format=bib_format)
            data = parse_bibtex(result_dblp)
            assert len(data.entries) <= 2 if bib_format is CROSSREF else len(data.entries) == 1
            new_entry = data.entries[entry_str]
            # Set new format
            bib.entries[entry_str] = new_entry
            if bib_format is CROSSREF:
                # Possible second entry
                for key, entry in data.entries.items():
                    if key != entry_str:
                        if key not in bib.entries:
                            bib.entries[key] = entry
            logging.debug("Set new entry for '{}'".format(entry_str))
            no_changes += 1
    return bib, no_changes


def search(bib, search_string):
    """
    Search for string in bibliography.
    Only the fields 'author' and 'title' are checked.
    :param bib: Bibliography in pybtex format.
    :param search_string: String to search for.
    :return: List of possible matches of publications with their score.
    """
    results = []
    for _, entry in bib.entries.items():
        if 'author' in entry.persons:
            authors = entry.persons['author']
            author_names = " and ".join([str(author) for author in authors])
        else:
            author_names = ""
        inp = "{}:{}".format(author_names, entry.fields["title"])
        score = bibtex_dblp.search.search_score(inp, search_string)
        if score > 0.5:
            results.append((entry, score))
    results.sort(key=lambda tup: tup[1], reverse=True)
    return results


def print_entry(bib_entry):
    """
    Print pybtex entry.
    :param bib_entry: Pybtex entry.
    :return: String.
    """
    authors = ", ".join([str(author) for author in bib_entry.persons['author']])
    book = ""
    if 'booktitle' in bib_entry.fields:
        book = bib_entry.fields['booktitle']
    if 'volume' in bib_entry.fields:
        book += " ({})".format(bib_entry.fields['volume'])
    return "{}:\n\t{} {} {}".format(authors, bib_entry.fields['title'], book, bib_entry.fields['year'])
