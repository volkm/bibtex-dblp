import logging

import pybtex.database

import bibtex_dblp.dblp_api as dblp_api
import bibtex_dblp.search
from bibtex_dblp.formats import BIB_FORMATS, CONDENSED, CROSSREF


def parse_bibtex(bibtex):
    """
    Parse bibtex string into pybtex format.
    :param bibtex: String containing bibtex information.
    :return: Entry in pybtex format.
    """
    d = pybtex.database.parse_string(bibtex, bib_format="bibtex")
    # DBLP escapes underscored (uses \_ instead of _).
    # This *seems* to be harmful when doi's and URLs are used with hyperref, so we remove \
    for e in d.entries.values():
        if "doi" in e.fields:
            e.fields["doi"] = e.fields["doi"].replace("\\_", "_")
        if "url" in e.fields:
            e.fields["url"] = e.fields["url"].replace("\\_", "_")
    return d


def convert_dblp_entries(bib, bib_format=CONDENSED):
    """
    Convert bibtex entries according to DBLP bibtex format.
    :param bib: Bibliography in pybtex format.
    :param bib_format: Bibtex format of DBLP.
    :return: converted bibliography, number of changed entries
    """
    assert bib_format in BIB_FORMATS
    logging.debug(f"Convert to format '{bib_format}'")
    no_changes = 0
    for entry_str, entry in bib.entries.items():
        # Check for id
        id = dblp_api.paper_id_from_entry(entry)
        if id.namespace is not None:
            logging.debug(f"Found id '{id.key()}'")
            result_dblp = dblp_api.get_bibtex(id, bib_format=bib_format)
            data = parse_bibtex(result_dblp)
            assert (
                len(data.entries) <= 2
                if bib_format is CROSSREF
                else len(data.entries) == 1
            )
            new_entry = data.entries.values()[0]
            retrieved_entry_key = new_entry.key
            new_entry.key = entry_str
            # Set new format
            bib.entries[entry_str] = new_entry
            if bib_format is CROSSREF:
                # Possible second entry
                for key, entry in data.entries.items():
                    if key != new_entry.key and key != retrieved_entry_key:
                        if key not in bib.entries:
                            bib.entries[key] = entry
            logging.debug(f"Set new entry for '{entry_str}'")
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
        if "author" in entry.persons:
            authors = entry.persons["author"]
            author_names = " and ".join([str(author) for author in authors])
        else:
            author_names = ""
        inp = "{}:{}".format(author_names, entry.fields["title"])
        score = bibtex_dblp.search.search_score(inp, search_string)
        if score > 0.5:
            results.append((entry, score))
    results.sort(key=lambda tup: tup[1], reverse=True)
    return results


def text_wrap(initial, text, line_length=90):
    """
    This tries to simlate in-field text wrapping used by DBLP.
    DBLP uses a more complex algorithm than a hard
    limit on the number of characters per line, but this is
    close.
    """
    words = text.split(" ")
    indentation = len(initial)
    actual_length = line_length - indentation
    lines = []
    line = ""
    for w in words:
        if len(line) == 0:
            line += w
        elif len(line) + 1 + len(w) <= actual_length:
            line += " " + w
        else:
            lines.append(line)
            line = w
    if len(line) > 0:
        lines.append(line)
    return initial + ("\n" + (" " * indentation)).join(lines)


def fieldstart_to_string(f, indentation=15):
    """
    Print start of a bibtex field. For example:
      author    = {
    :param String: Field name.
    :param Integer: Total number of characters in return string (will be padded with spaces before '=')
    :return: String.
    """
    return "  " + f + (" " * (indentation - len(f) - 6)) + " = {"


def persons_to_string(group, entry):
    text = fieldstart_to_string(group)
    sep = " and\n" + (" " * len(text))

    def names(p):
        return p.first_names + p.middle_names + p.prelast_names + p.last_names

    text += sep.join(" ".join(names(p)) for p in entry.persons[group])
    text += "}"
    return text


def entry_to_string(entry, bib_format="pybtex"):
    """
    Print bibtex entry in a DBLP-simulated format, or in pybtex standard format.
    :param entry: Pybtex entry.
    :param bib_format: One of BIB_FORMATS, or 'pybtex'.
    :return: String.
    """
    bib_format in BIB_FORMATS + ["pybtex"]
    if bib_format == "pybtex":
        authors = ", ".join([str(author) for author in entry.persons["author"]])
        book = ""
        if "booktitle" in entry.fields:
            book = entry.fields["booktitle"]
        if "volume" in entry.fields:
            book += " ({})".format(entry.fields["volume"])
        return "{}:\n\t{} {} {}".format(
            authors, entry.fields["title"], book, entry.fields["year"]
        )
    else:
        text = "@" + entry.type + "{" + entry.key + ",\n"
        lines = []
        for g in ["author", "editor"]:
            if g in entry.persons:
                lines.append(persons_to_string(g, entry))
        for f in entry.fields:
            initial = fieldstart_to_string(f)
            lines.append(text_wrap(initial, entry.fields[f]) + "}")
        text += ",\n".join(lines) + "\n}"
        return text


def bib_to_string(bib, bib_format="pybtex"):
    text_list = []
    for e in bib.entries.values():
        text_list.append(entry_to_string(e, bib_format=bib_format))
    return "\n\n".join(text_list)
