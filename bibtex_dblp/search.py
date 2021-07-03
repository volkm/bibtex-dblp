import re


def search_score(input_string, search_query):
    """
    Return a score indicating how good the given input matches the given search query.
    :param input_string: Input string.
    :param search_query: Search query. Spaces are interpreted as boolean AND. Uses prefix search.
    :return: Score in [0,1] indicating how good the input matches. 0 means no match, 1 means perfect match.
    """
    score = 0
    search_words = search_query.split()
    for word in search_words:
        if re.search(r"\b{}\b".format(word), input_string, re.IGNORECASE) is not None:
            score += 1
    return score / len(search_words)
