def nat_join(value, cnj="and"):
    """
    nat_join(['pierre', 'paul', 'jacques'])
    returns 'pierre, paul and jacques'
    """
    if isinstance(value, list):
        if len(value):
            return "".join(
                (', '.join([str(item) for item in value[0:-1]]), " %s %s" % (
                    cnj, str(value[-1])))) if len(value) > 1 else str(value[0])
        return ''
    else:
        return value


def clean_url(url):
    newurl = (
        url
        .replace(u"https://", "")
        .replace(u"http://", "")
        .replace(u"www.", "")
        .replace(u"\u2018", "'")
        .replace(u"\u2019", "'")
        .replace(u" ", "")
        .replace(u"\n", "")
    )
    return str(newurl)


def clean_title(title):
    newtitle = (
        title
        .replace(u"\u2018", "'")
        .replace(u"\u2019", "'")
        .encode("ascii", "ignore")
        .decode("utf8")
    )
    return newtitle
