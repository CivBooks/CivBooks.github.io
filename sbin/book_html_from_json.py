import json
import os
import re
import sys

books_root = 'books'

re_word = re.compile(r'[A-Za-z]+')

generation_order = {k: v for v, k in enumerate(
    'Original,Copy,Copy of Copy,Tattered'.split(','))}


def write_books_htmls_from_json_paths(source_paths):
    index = {}
    # f'{signee}/{safe_title}' -> book_json
    index_json_path = f'{books_root}/index.json'
    try:
        with open(index_json_path, 'r') as f:
            index = json.load(f)
    except Exception as e:
        print(f'Could not read {index_json_path}: {e}', file=sys.stderr)

    for path in source_paths:
        with open(path, 'r') as f:
            write_books_htmls_from_json(f, index)

    with open(index_json_path, 'w') as f:
        json.dump(index, f, separators=(',', ':'))


def write_books_htmls_from_json(source_file, books_index=None):
    for line_nr, line in enumerate(source_file):
        try:
            line = line.strip()
            if not line:
                continue
            book_json = json.loads(line)
            # TODO fake title from first couple words of the book
            if "-unsigned-" == (book_json.get('item_title') or "-unsigned-"):
                print(f'Skipping untitled book at line {line_nr} with {len(book_json["pages"])} pages'
                      + f' in {book_json["item_origin"]}', file=sys.stderr)
                continue

            index_book_json = {
                "item_origin": book_json["item_origin"],
                "item_title": book_json.get("item_title") or "-unsigned-",
                "signee": book_json.get("signee") or "-unsigned-",
                "generation": book_json.get("generation"),
                "page_count": len(book_json["pages"]),
                "word_count": len(list(re_word.finditer(''.join(book_json["pages"])))),
            }

            # not necessarily original author; transcription counts as its own edition
            signee = book_json.get("signee") or "-unsigned-"
            safe_title = safe_string(
                book_json.get("item_title") or "-unsigned-")
            dir_path = f'{books_root}/{signee}'
            page_path = f'{dir_path}/{safe_title}.html'

            # TODO check if exists, add suffix, prompt to check manually
            # TODO if 10 books in a window of 20 trigger an increment, abort
            write = True
            if os.path.isfile(page_path):
                warn_lines = []
                warn_lines.append(
                    f'Name collision at line {line_nr} "{book_json.get("item_title") or "-unsigned-"}"')
                write = False
                if books_index is not None:
                    prev = books_index[f"{signee}/{safe_title.lower()}"]
                    differing = []
                    for k, curr_val in index_book_json.items():
                        if curr_val != prev[k]:
                            differing.append(k)
                            warn_lines.append(
                                f'  {k}: mine={curr_val} prev={prev[k]}')
                    if differing == []:
                        # probably identical TODO compare full contents
                        write = False
                    elif prev['page_count'] < index_book_json['page_count']:
                        # prev is shorter; overwrite
                        write = True
                    elif prev['page_count'] > index_book_json['page_count']:
                        # prev is longer; leave alone
                        write = False
                    elif differing == ['generation']:
                        if generation_order[prev['generation']] > generation_order[index_book_json['generation']]:
                            # prev is worse; overwrite
                            write = True
                        else:  # prev is better; leave alone
                            write = False
                    else:
                        print(*warn_lines, sep='\n', file=sys.stderr)
                else:
                    print(*warn_lines, sep='\n', file=sys.stderr)

            os.makedirs(dir_path, exist_ok=True)
            if write:
                book_html = template_book(book_json)
                with open(page_path, 'w') as file_html:
                    file_html.write(book_html)
            if books_index is not None:
                books_index[f'{signee}/{safe_title.lower()}'] = index_book_json
        except Exception as e:
            print("Error in line", line_nr, file=sys.stderr)
            raise e


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
    title = book.get('item_title') or "-unsigned-"
    signee = book.get('signee') or "-unsigned-"
    author = book.get('author')
    author_or_signee = book.get('author') or signee
    item_origin = book['item_origin']
    safe_origin = item_origin.replace(' ', '_').replace('.0', '')

    head_img = '' if not author_or_signee else \
        f'<a href="https://minecraft-statistic.net/en/player/{author_or_signee}.html" \
target="_blank" rel="noopener noreferrer">\
<img class="author-face" src="https://www.mc-heads.net/avatar/{author_or_signee}" \
title="Face of {author_or_signee}" alt="Face of {author_or_signee}"></a>'

    author_html = '' if not author else \
        f'<div class="author">Written by <a class="author-name" \
href="../../?search=:author:{author}">{author}</a></div>'
    signee_html = '' if signee == author or signee == "-unsigned-" else \
        f'<div class="signee">Signed by <a class="signee-name" \
href="../../?search=:signee:{signee}">{signee}</a></div>'

    return f'''<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta http-equiv="X-UA-Compatible" content="ie=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - by {author_or_signee} - Civ Book Viewer</title>
    <link rel="stylesheet" href="../../style.css">
    <link rel="prefetch" href="../../font/Minecraft-Regular.otf">
    <meta property="og:type" content="object" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="Signed by {signee} on {item_origin}. Read the full book here and discover more Civ books." />
    <meta property="og:site_name" content="Civ Book Viewer" />
    <meta property="og:url" content="https://gjum.github.io/CivBookViewer/" />
    <meta property="og:image" content="https://gjum.github.io/CivBookViewer/img/icon.png" />
    <link rel="shortcut icon" href="https://gjum.github.io/CivBookViewer/img/icon.png">
</head><body>
<a class="back-home" href="../../">Civ Book Viewer</a>
<h1>{title}</h1>
{head_img}
{author_html}
{signee_html}
<div class="source">on <a class="source-server" href="../../?search=:server:{safe_origin}">{item_origin}</a></div>
<div class="book">
{html_pages}
</div>
<script defer src="../../book.js"></script>
</body></html>'''


re_bad_url_chars = re.compile(r'[ \\%:/?&#\'\"\[\]<>()]')


def safe_string(s):
    try:
        return re_bad_url_chars.sub('_', s)
    except Exception as e:
        print("Can't make string safe:", repr(s), file=sys.stderr)
        raise e


if __name__ == "__main__":
    source_paths = sys.argv[1:] if len(sys.argv) > 1 else ['/dev/stdin']
    write_books_htmls_from_json_paths(source_paths)
