import re

# from lxml import etree
import logging


import bibtex_dblp.dblp_data
import bibtex_dblp.search
from bibtex_dblp.database import print_entry


class DblpXml:
    """
    XML database for DBLP.
    """

    def __init__(self, dblp_path):
        """
        Create a DBLP XML database from a DBLP XML file.
        :param dblp_path: Path to DBLP XML file.
        """
        self.xml_path = dblp_path

        # Element types in DBLP
        self.types = {"article", "inproceedings", "proceedings", "book", "incollection", "phdthesis", "mastersthesis", "www", "person", "data"}

        # Feature types in DBLP
        self.features = {
            "address": "str",
            "author": "list",
            "booktitle": "str",
            "cdrom": "str",
            "chapter": "str",
            "cite": "list",
            "crossref": "str",
            "editor": "list",
            "ee": "list",
            "isbn": "str",
            "journal": "str",
            "month": "str",
            "note": "str",
            "number": "str",
            "pages": "str",
            "publisher": "str",
            "publnr": "str",
            "school": "str",
            "series": "str",
            "title": "str",
            "url": "str",
            "volume": "str",
            "year": "str",
        }

    def iterate(self, tags=None):
        """
        Return iterator filtering on given tags.
        """
        # Load XML
        try:
            return etree.iterparse(source=self.xml_path, tag=tags, dtd_validation=True, load_dtd=True)
        except IOError:
            logging.error('Failed to load file "{}".'.format(self.xml_path))
            return None

    @staticmethod
    def clear_element(element):
        """
        Free up memory after processing element.
        """
        element.clear()
        while element.getprevious() is not None:
            del element.getparent()[0]

    def extract_feature(self, elem, features, include_key=False):
        """Extract the value of each feature"""
        if include_key:
            attribs = {"key": [elem.attrib["key"]]}
        else:
            attribs = {}
        for feature in features:
            attribs[feature] = []
        for sub in elem:
            if sub.tag not in features:
                continue
            if sub.tag == "title":
                text = re.sub("<.*?>", "", etree.tostring(sub).decode("utf-8")) if sub.text is None else sub.text
            else:
                text = sub.text
            if text is not None and len(text) > 0:
                attribs[sub.tag] = attribs.get(sub.tag) + [text]
        return attribs

    def print_entry(self, elem, single_line=False):
        """
        Print XML entry.
        :param elem: XML entry.
        :return: String.
        """
        authors = []
        book = ""
        volume = ""
        title = ""
        year = ""
        for sub in elem:
            if sub.tag == "author":
                authors.append(sub.text)
            elif sub.tag == "organization":
                authors.append(sub.text)
            elif sub.tag == "booktitle":
                book = sub.text
            elif sub.tag == "volume":
                volume = " ({})".format(sub.text)
            elif sub.tag == "title":
                title = sub.text
            elif sub.tag == "year":
                year = sub.text

        if single_line:
            return "{}: {} {} {}".format(", ".join(authors), title, book + volume, year)
        else:
            return "{}:\n\t{} {} {}".format(", ".join(authors), title, book + volume, year)

    def convert_to_text(self, out_file):
        with open(out_file, "w") as f:
            i = 0
            for _, elem in self.iterate(tags=self.types):
                i += 1
                inp = self.print_entry(elem, single_line=True)
                key = elem.attrib["key"]
                f.write(key + "," + inp + "\n")
                if i % 10000 == 0:
                    print(i)


def search_publication(dblp_xml, pub_query, max_search_results):
    """
    Search for publication according to given query.
    :param dblp_xml: DBLP XML database.
    :param pub_query: Query for publication.
    :param max_search_results: Maximal number of search results to return.
    :return: Search results.
    """
    results = []
    i = 0
    for _, elem in dblp_xml.iterate(tags=dblp_xml.types):
        i += 1
        inp = dblp_xml.print_entry(elem)
        score = bibtex_dblp.search.search_score(inp, pub_query)
        if score > 0.5:
            results.append((inp, score))
        if i % 10000 == 0:
            print(i)
        dblp_xml.clear_element(elem)
        # if len(results) > 2:
        #    break

    results.sort(key=lambda tup: tup[1], reverse=True)
    return results[:max_search_results]


def search_publication_txt(txt, pub_query, max_search_results):
    """
    Search for publication according to given query.
    :param dblp_xml: DBLP XML database.
    :param pub_query: Query for publication.
    :param max_search_results: Maximal number of search results to return.
    :return: Search results.
    """
    results = []
    i = 0
    with open(txt, "r") as f:
        for _, line in enumerate(f):
            key, inp = line.split(",", 1)
            score = bibtex_dblp.search.search_score(inp, pub_query)
            if score > 0.5:
                results.append((inp, score))
            # if i % 10000 == 0:
            #    print(i)

    results.sort(key=lambda tup: tup[1], reverse=True)
    return results[:max_search_results]


if __name__ == "__main__":
    xml = DblpXml("dblp.xml")
    # xml.convert_to_text("dblp.txt")
    res = search_publication_txt("dblp.txt", "Matthias Volk Storm", 30)
    print("\n".join([r[0] for r in res]))

    # res = search_publication(xml, "Matthias Volk Storm", 30)
    # print("\n".join([r[0] for r in res]))
