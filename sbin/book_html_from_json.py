import json
import os
import re
import sys

books_root = 'books'


def write_books_htmls_from_json_paths(source_paths):
    for path in source_paths:
        with open(path) as f:
            write_books_htmls_from_json(f)


def write_books_htmls_from_json(source_file):
    for line_nr, line in enumerate(source_file):
        line = line.strip()
        if not line:
            continue
        book_json = json.loads(line)
        if not book_json.get('signee'):
            print(f'Skipping unsigned book at line {line_nr} with {len(book_json["pages"])} pages'
                  + f' in {book_json["entry_source"]}', file=sys.stderr)
            continue
        if not book_json.get('item_title'):
            print(f'Skipping untitled book at line {line_nr} with {len(book_json["pages"])} pages'
                  + f' in {book_json["entry_source"]}', file=sys.stderr)
            continue
        if not book_json.get('entry_source'):
            raise Exception(f'No entry_source in book. Line {line_nr}')
        # not original author; transcription counts as its own edition
        signee = book_json["signee"]
        safe_title = safe_string(book_json["item_title"])
        dir_path = f'{books_root}/{signee}'
        page_path = f'{dir_path}/{safe_title}.html'
        # TODO check if exists, add suffix, prompt to check manually
        book_html = template_book(book_json)
        os.makedirs(dir_path, exist_ok=True)
        with open(page_path, 'w') as file_html:
            file_html.write(book_html)


re_formatting = re.compile(r'§([0-9a-fA-FklmnorKLMNOR])|[^§]+|§')


def template_page(content, page_nr, pages_total):
    page_nr += 1  # start at 1
    styled_content = ''
    # line breaks reset all formatting
    content_with_resets = content.replace('\n', '§r\n') + '\n'
    tags_to_close = 0  # number of </span> to insert at next §r
    for match in re_formatting.finditer(content_with_resets):
        fcode = match.group(1)
        if not fcode:
            # content segment
            styled_content += match.group(0)
        elif fcode.lower() == 'r':
            # reset segment
            styled_content += '</span>' * tags_to_close
            tags_to_close = 0
        else:
            # formatting segment
            styled_content += f'<span class="fmt{fcode.lower()}">'
            tags_to_close += 1
    styled_content = styled_content.rstrip()
    return f'<div class="page" id="page-{page_nr}">\
<a href="#page-{page_nr}" class="page-indicator">\
Page {page_nr} of {pages_total}</a>\
<div class="page-content">{styled_content}</div>\
</div>'


def template_book(book):
    pages_total = len(book['pages'])
    html_pages = '\n'.join(
        template_page(content, page_nr, pages_total)
        for page_nr, content in enumerate(book['pages'])
    )
    title = book['item_title']
    signee = book.get('signee')
    author = book.get('author')
    author_or_signee = book.get('author', signee)
    entry_source = book['entry_source']
    safe_source = entry_source.replace(' ', '_').replace('.0', '')

    head_img = '' if not author_or_signee else \
        f'<a href="https://minecraft-statistic.net/en/player/{author_or_signee}.html" \
target="_blank" rel="noopener noreferrer">\
<img class="author-face" src="https://www.mc-heads.net/avatar/{author_or_signee}" \
title="Face of {author_or_signee}" alt="Face of {author_or_signee}"></a>' \

    author_html = '' if not author else \
        f'<div class="author">Written by <a class="author-name" \
href="../../index.html?search=:author:{author}">{author}</a></div>'
    signee_html = '' if signee == author else \
        f'<div class="signee">Signed by <a class="signee-name" \
href="../../index.html?search=:signee:{signee}">{signee}</a></div>'

    return f'''<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta http-equiv="X-UA-Compatible" content="ie=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - by {author} - Civ Book Viewer</title>
    <link rel="stylesheet" href="../../style.css">
    <meta property="og:type" content="object" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="Signed by {signee} on {entry_source}. Read the full book here and discover more Civ books." />
    <meta property="og:site_name" content="Civ Book Viewer" />
    <meta property="og:url" content="https://gjum.github.io/CivBookViewer/" />
    <meta property="og:image" content="https://gjum.github.io/CivBookViewer/img/icon.png" />
    <link rel="shortcut icon" href="https://gjum.github.io/CivBookViewer/img/icon.png">
</head><body>
<a class="back-home" href="../../index.html">Civ Book Viewer</a>
<h1>{title}</h1>
{head_img}
{author_html}
{signee_html}
<div class="source">on <a class="source-server" href="../../index.html?search=:server:{safe_source}">{entry_source}</a></div>
<div class="book">
{html_pages}
</div>
<script defer src="../../book.js"></script>
</body></html>'''


re_bad_url_chars = re.compile(r'[ \\%:/?&#\'\"\[\]<>()]')


def safe_string(s):
    return re_bad_url_chars.sub('_', s)


if __name__ == "__main__":
    source_paths = sys.argv[1:] if len(sys.argv) > 1 else ['/dev/stdin']
    write_books_htmls_from_json_paths(source_paths)
