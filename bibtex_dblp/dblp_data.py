class DblpSearchResults:
    """
    Results of one search in DBLP.
    """

    def __init__(self, json):
        result = json["result"]
        self.query = result["query"]
        status = result["status"]
        self.status_code = int(status["@code"])
        self.status_text = status["text"]
        hits = result["hits"]
        self.total_matches = int(hits["@total"])
        self.results = []
        if self.total_matches > 0:
            self.results = [DblpSearchResult(hit_json) for hit_json in hits["hit"]]


class DblpSearchResult:
    """
    One possible matched result of a search query in DBLP.
    """

    def __init__(self, json):
        self.score = json["@score"]
        self.publication = DblpPublication(json["info"])


class DblpPublication:
    """
    Publication in DBLP.
    """

    def __init__(self, json):
        self.title = json["title"]
        self.booktitle = json.get("booktitle")
        self.volume = json.get("volume")
        self.venue = json.get("venue")
        self.pages = json.get("pages")
        self.year = int(json.get("year"))
        self.type = json.get("type")
        self.key = json.get("key")
        self.doi = json.get("doi")
        self.ee = json.get("ee")
        self.url = json.get("url")
        self.authors = []
        authors = json.get("authors")
        if authors:
            authors = authors["author"]
            if isinstance(authors, list):
                self.authors = [DblpAuthor(author) for author in authors]
            else:
                self.authors = [DblpAuthor(authors)]

        # Possible additional fields:
        # sub_type, mdate, authors, editors, month, journal, number, chapter, isbn, crossref, publisher, school, citations, series

    def cite_key(self):
        return "DBLP:" + self.key

    def __str__(self):
        s = ", ".join([str(author) for author in self.authors])
        s += ":\n\t"
        s += self.title[:-1] if self.title.endswith(".") else self.title
        s += ", {}".format(self.venue) if self.venue else ""
        s += " ({})".format(self.volume) if self.volume else ""
        s += ", {}".format(self.year)
        if self.ee:
            s += "\n\t{}".format(self.ee)
        return s


class DblpAuthor:
    """
    Author in DBLP.
    """

    def __init__(self, json):
        self.name = json.get("text")
        self.pid = json.get("pid")

    def __str__(self):
        return self.name
