import json
import os
import re
import sys
import urllib3


source_names = {
    'civcraft_1': 'Civcraft 1.0',
    'civcraft_2': 'Civcraft 2.0',
    'civcraft_3': 'Civcraft 3.0',
    'devoted_2': 'Devoted 2.0',
    'devoted_3': 'Devoted 3.0',
    'civclassic_2': 'CivClassic 2.0',
}


def write_books_htmls_from_json():
    books_json = json.load(sys.stdin)
    for nr_book, book_json in enumerate(books_json):
        book_html = template_book(book_json)
        if not book_json.get('signed'):
            print('Skipping book, not signed. Entry', nr_book, file=sys.stderr)
            continue
        if not book_json.get('title'):
            print('Skipping book, no title. Entry', nr_book, file=sys.stderr)
            continue
        if not book_json.get('source'):
            raise Exception(f'No source in book. Entry {nr_book}')
        pagename = safe_string(book_json['signed'] + '_' + book_json['title'])
        dirname = safe_string(book_json['source'])
        os.makedirs(dirname, exist_ok=True)
        with open(f'{dirname}/{pagename}.html', 'w') as file_html:
            file_html.write(book_html)


re_formatting = re.compile(r'§[0-9a-zA-Z]')


def template_page(content, page_nr, pages_total):
    page_nr += 1
    # TODO formatting
    # for now, strip styles:
    content = re_formatting.sub('', content)
    return f'<div class="page">\
<a href="#page-{page_nr}" id="page-{page_nr}" class="page-indicator">\
Page {page_nr} of {pages_total}</a>\
<div class="page-content">{content}</div>\
</div>'


def template_book(book):
    pages_total = len(book['pages'])
    html_pages = '\n'.join(
        template_page(content, page_nr, pages_total)
        for page_nr, content in enumerate(book['pages'])
    )
    title = book['title']
    signed = book['signed']
    # TODO track original author separately; conditionally display only when known
    author = signed
    source = book['source']
    source_name = source_names[source.lower()]
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta http-equiv="X-UA-Compatible" content="ie=edge"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - by {author} - Civ Book Viewer</title>
    <link rel="stylesheet" href="../style.css">
    <meta property="og:type" content="object" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="Signed by {signed} on {source_name}. Read the full book here and discover more Civ books." />
    <meta property="og:site_name" content="Civ Book Viewer" />
    <meta property="og:url" content="https://gjum.github.io/CivBookViewer/" />
    <meta property="og:image" content="../img/CBTC.png" />
    <link rel="shortcut icon" href="../img/CBTC.png">
</head><body>
<a class="back-home" href="../index.html">Civ Book Viewer</a>
<h1>{title}</h1>
<div class="author">
    <a href="https://minecraft-statistic.net/en/player/{author}.html" target="_blank" rel="noopener noreferrer">
        <img class="author-face" src="https://www.mc-heads.net/avatar/{author}" alt="Face of {author}"></a>
    Signed by <a class="author-name" href="../index.html?search=:signed:{signed}">{signed}</a>
</div>
<div class="source">on <a class="source-server" href="../index.html?search=:server:{source}">{source_name}</a></div>
<div class="book">
{html_pages}
</div></body></html>'''


re_bad_url_chars = re.compile(r'[ \\%:/?&#\'\"\[\]<>()]+')


def safe_string(s):
    return re_bad_url_chars.sub('_', s)


if __name__ == "__main__":
    write_books_htmls_from_json()
