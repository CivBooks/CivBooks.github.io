import json
import os
import re
import sys

books_root = 'books'

re_word = re.compile(r'[A-Za-z_0-9]+')
re_mc_name_with_fmt_codes = re.compile(r'[§A-Za-z_0-9]+')
re_all_dots = re.compile(r'^\.+$')
re_bad_url_chars = re.compile(r'[ \\%:/?&#\'\"\[\]<>()]')
re_format_code = re.compile(r'§[0-9a-fA-FklmnorKLMNOR]')
re_formatting = re.compile(r'§([0-9a-fA-FklmnorKLMNOR])|\n|[^§]+|§')
re_redundant_format_codes = re.compile(r'(§[0-9a-fA-FklmnorKLMNOR])+§r')


generation_order = {k: v for v, k in enumerate(
    'Original,Copy,Copy of Copy,Tattered'.split(','))}
generation_order.update({v: v for v in range(4)})
generation_order[None] = 99

color_code_from_name = {
    'black': '0',
    'dark_blue': '1',
    'dark_green': '2',
    'dark_aqua': '3',
    'dark_red': '4',
    'dark_purple': '5',
    'gold': '6',
    'gray': '7',
    'dark_gray': '8',
    'blue': '9',
    'green': 'a',
    'aqua': 'b',
    'red': 'c',
    'light_purple': 'd',
    'yellow': 'e',
    'white': 'f',
}


def write_books_htmls_from_json_paths(source_paths):
    # f'{safe_origin}/{signee}/{safe_title}'.lower() -> book_json
    index = {}
    index_json_path = f'{books_root}/metadata.json'
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


def write_books_htmls_from_json(source_file, books_metadata=None):
    for line_nr, line in enumerate(source_file):
        try:
            line = line.strip()
            if not line:
                continue
            book_json = json.loads(line)
            if not book_json.get('item_origin'):
                raise Exception(
                    f'No item_origin in book. Line {line_nr} {line}')
            if not book_json.get('item_title'):
                print(f'Skipping untitled book at line {line_nr} with {len(book_json["pages"])} pages'
                      + f' in {book_json["item_origin"]}', file=sys.stderr)
                continue
            if book_json.get('signee') in [None, '', ' ']:
                print(f'Skipping unsigned book at line {line_nr} with {len(book_json["pages"])} pages'
                      + f' in {book_json["item_origin"]}', file=sys.stderr)
                continue

            signee = book_json.get("signee") or "-unsigned-"
            if not re_mc_name_with_fmt_codes.match(signee):
                raise Exception(
                    f'Invalid signee "{signee}" in line {line_nr} {line}')

            book_json["clean_pages"] = cleanup_pages(book_json)

            book_json_metadata = {
                "item_origin": book_json["item_origin"],
                "item_title": book_json.get("item_title") or "-unsigned-",
                "signee": book_json.get("signee") or "-unsigned-",
                "generation": book_json.get("generation"),
                "page_count": len(book_json["pages"]),
                "word_count": len(list(re_word.finditer(' '.join(book_json["clean_pages"])))),
            }

            safe_title = make_safe_string(
                book_json.get("item_title") or "-unsigned-")
            safe_origin = make_safe_origin(book_json['item_origin'])
            dir_path = f'{books_root}/{safe_origin}/{signee}'
            page_path = f'{dir_path}/{safe_title}.html'
            index_key = f'{safe_origin}/{signee}/{safe_title}'.lower()

            # TODO check if exists, add suffix, prompt to check manually
            # TODO if 10 books in a window of 20 trigger an increment, abort
            write = True
            if os.path.isfile(page_path):
                warn_lines = []
                warn_lines.append(
                    f'Name collision at line {line_nr} "{book_json.get("item_title") or "-unsigned-"}"')
                write = False
                if books_metadata is not None:
                    prev = books_metadata[index_key]
                    differing = []
                    for k, curr_val in book_json_metadata.items():
                        if curr_val != prev[k]:
                            differing.append(k)
                            warn_lines.append(
                                f'  {k}: mine={curr_val} prev={prev[k]}')
                    if differing == []:
                        # probably identical TODO compare full contents
                        write = False
                    elif prev['page_count'] < book_json_metadata['page_count']:
                        # prev is shorter; overwrite
                        write = True
                    elif prev['page_count'] > book_json_metadata['page_count']:
                        # prev is longer; leave alone
                        write = False
                    elif differing == ['generation']:
                        if generation_order[prev['generation']] > generation_order[book_json_metadata['generation']]:
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
            if books_metadata is not None:
                books_metadata[index_key] = book_json_metadata
        except Exception as e:
            print("Error in line", line_nr, line.strip(), file=sys.stderr)
            raise e


def template_page(content, page_nr, page_count):
    page_nr += 1  # start at 1
    styled_content = ''
    # line breaks reset all formatting
    tags_to_close = 0  # number of </span> to insert at next §r
    for match in re_formatting.finditer(content):
        fullmatch = match.group(0)
        fcode = match.group(1)
        if not fcode and fullmatch != '\n':
            # content segment
            styled_content += fullmatch
        elif fullmatch == '\n':
            # newline reset
            styled_content += '</span>' * tags_to_close
            styled_content += '\n'
            tags_to_close = 0
        elif fcode.lower() == 'r':
            # reset segment
            styled_content += '</span>' * tags_to_close
            styled_content += f'<span class="fmtcode">§{fcode}</span>'
            tags_to_close = 0
        else:
            # formatting segment
            styled_content += f'<span class="fmt{fcode.lower()}">'
            styled_content += f'<span class="fmtcode">§{fcode}</span>'
            tags_to_close += 1
    styled_content = styled_content.rstrip()
    return f'<div class="page" id="page-{page_nr}">\
<a href="#page-{page_nr}" class="page-indicator">\
Page {page_nr} of {page_count}</a>\
<div class="page-content">{styled_content}</div>\
</div>'


def template_book(book):
    clean_pages = book['clean_pages']
    page_count = len(clean_pages)
    html_pages = '\n'.join(
        template_page(clean_page, page_nr, page_count)
        for page_nr, clean_page in enumerate(clean_pages)
    )
    title = book.get('item_title') or "-unsigned-"
    signee = book.get('signee') or "-unsigned-"
    content_author = book.get('content_author')
    author_or_signee = content_author or signee
    item_origin = book['item_origin']
    safe_origin = make_safe_origin(item_origin)

    description = f'Signed by {signee} on {item_origin}.' \
        + f" Read {'it' if page_count <= 1 else f'all {page_count} pages'} here and discover more Civ books."

    head_img = '' if not author_or_signee else \
        f'<a href="https://minecraft-statistic.net/en/player/{author_or_signee}.html" \
target="_blank" rel="noopener noreferrer">\
<img class="author-face" src="https://www.mc-heads.net/avatar/{author_or_signee}" \
title="Face of {author_or_signee}" alt="Face of {author_or_signee}"></a>'

    author_html = '' if not content_author else \
        f'<div class="author">Written by <a class="author-name" \
href="../../../?search=:author:{content_author}">{content_author}</a></div>'
    signee_html = '' if signee == content_author or signee == "-unsigned-" else \
        f'<div class="signee">Signed by <a class="signee-name" \
href="../../../?search=:signee:{signee}">{signee}</a></div>'

    return f'''<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta http-equiv="X-UA-Compatible" content="ie=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - by {author_or_signee} - Civ Books</title>
    <link rel="prefetch" href="../../../font/Minecraft-Regular.otf">
    <link rel="prefetch" href="../../../img/page.png">
    <link rel="stylesheet" href="../../../style.css">
    <meta property="og:type" content="object" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{description}" />
    <meta property="og:site_name" content="Civ Books" />
	<meta property="og:url" content="https://CivBooks.github.io/" />
	<meta property="og:image" content="https://CivBooks.github.io/img/icon.png" />
	<link rel="shortcut icon" href="../../../img/icon.png">
</head><body id="top">
<a href="../../../"><img src="../../../img/icon.png" width="48px" alt="Civ Books Logo" style="float: right" /></a>
<a class="back-home" href="../../../">Civ Books</a>
<h1>{title}</h1>
{head_img}
{author_html}
{signee_html}
<div class="source">on <a class="source-server" href="../../../?search=:server:{safe_origin}">{item_origin}</a></div>
<div class="book">
{html_pages}
</div>
<footer>
<p>Part of the <a href="https://github.com/CivBooks" target="_blank" rel="noopener noreferrer">Civ Books</a>
project by <a href="https://github.com/Gjum" target="_blank" rel="noopener noreferrer">Gjum</a>.
</p>
<a href="#top"><img src="../../../img/icon.png" width="64px" alt="Civ Books Logo" /></a>
</footer>
<script defer src="../../../book.js"></script>
</body></html>'''


def make_safe_string(s):
    try:
        s = re_format_code.sub('', re_bad_url_chars.sub('_', s))
        if re_all_dots.match(s):  # breaks urls
            s = s[:-1]+'_'
        return s
    except Exception as e:
        print("Can't make string safe:", repr(s), file=sys.stderr)
        raise e


def make_safe_origin(s):
    try:
        return s.replace(' ', '_').replace('.0', '')
    except Exception as e:
        print("Can't make origin safe:", repr(s), file=sys.stderr)
        raise e


def cleanup_pages(book_json):
    if 'pages' not in book_json:
        return []
    is_json = all((
        (page == ""
         or page.startswith('"') and page.endswith('"')
         or page.startswith('{"') and page.endswith('"}'))
        and not "\n" in page)
        for page in book_json["pages"])
    return [cleanup_page(page, is_json) for page in book_json["pages"]]


def cleanup_page(in_str, is_json):
    try:
        if not is_json:
            return in_str
        # it's json
        try:
            component = json.loads(in_str)
        except json.JSONDecodeError:
            # actually, it's just a regular page with weird quotes/escapes
            return in_str
        return str_from_chat_component(component)
    except Exception as e:
        print("Error:", e, "- Raw page:", in_str, file=sys.stderr)
        raise e


def str_from_chat_component(component):
    if isinstance(component, str):
        return component
    fmt_codes = ''
    if component.get('bold'):
        fmt_codes += '§l'
    if component.get('italic'):
        fmt_codes += '§o'
    if component.get('underlined'):
        fmt_codes += '§n'
    if component.get('strikethrough'):
        fmt_codes += '§m'
    if component.get('obfuscated'):
        fmt_codes += '§k'
    if component.get('color'):
        fmt_codes += '§'+color_code_from_name[component['color']]
    undo_fmt = '§r' if fmt_codes else ''
    return fmt_codes + component.get('text', '')\
        + ''.join(fmt_codes + str_from_chat_component(e) + undo_fmt
                  for e in component.get('extra', [])) \
        + undo_fmt


def remove_redundant_formatting(in_str):
    re_redundant_format_codes.sub('§r', in_str)  # TODO handle newlines
    # TODO remove_redundant_formatting
    return in_str


if __name__ == "__main__":
    source_paths = sys.argv[1:] if len(sys.argv) > 1 else ['/dev/stdin']
    write_books_htmls_from_json_paths(source_paths)
