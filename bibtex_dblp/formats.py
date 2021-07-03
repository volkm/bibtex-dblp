# DBLP bib-entry types
CONDENSED = "condensed"
STANDARD = "standard"
CROSSREF = "crossref"

BIB_FORMATS = [CONDENSED, STANDARD, CROSSREF]


def dblp_article_url_part(bib_format):
    """
    Get identifier of format for DBLP article urls.
    For example, bib1 in https://dblp.org/rec/bib1/journals/ir/BastMW08.bib
    :return:
    """
    assert bib_format in BIB_FORMATS
    if bib_format == CONDENSED:
        return "bib0"
    elif bib_format == STANDARD:
        return "bib1"
    elif bib_format == CROSSREF:
        return "bib2"


def dblp_author_url_part(bib_format):
    """
    Get identifier of format for DBLP author urls.
    For example, tb1 in https://dblp.org/pers/tb1/b/Bast:Hannah.bib
    :return:
    """
    assert bib_format in BIB_FORMATS
    if bib_format == CONDENSED:
        return "tb0"
    elif bib_format == STANDARD:
        return "tb1"
    elif bib_format == CROSSREF:
        return "tb2"
