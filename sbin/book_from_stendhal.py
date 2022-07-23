'''
Converts a .stendhal file and prints them in JSON format.
Usage: python3 book_from_stendhal.py "path/to/my_book.stendhal" "Server name"
Output example:
{   "item_origin": "Devoted 3.0",
    "item_title": "The Navy Seal",
    "signee": "auxchar",
    "pages": [
        "What the fuck did you just fucking say about me, you little bitch?",
        "I\u2019ll have you know I graduated top of my class in the Navy Seals, and I\u2019ve been involved in numerous secret raids on Al-Quaeda, and I have over 300 confirmed kills.",
        ...
        "I will shit fury all over you and you will drown in it. You\u2019re fucking dead, kiddo."
    ]
}

Created by Gjum
https://github.com/Gjum
'''

import sys
import json


def print_json_book_from_stendhal(fpath, item_origin):
    title = None
    author = None
    with open(fpath, "r") as file:
        while True:
            line = file.readline().strip()
            if line == "pages:":
                break
            elif line.startswith("title: "):
                title = line[len("title: "):]
            elif line.startswith("author: "):
                author = line[len("author: "):]
        rem = "\n" + file.read()
        pages = rem.split("\n#- ")

    book = {
        'item_origin': item_origin,
        'item_title': title,
        'signee': author,
        'pages': [json.dumps({"text": page}) for page in pages if page.strip()],
    }
    print(json.dumps(book, separators=(',', ':')))


if __name__ == "__main__":
    fpath = sys.argv[1]
    item_origin = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
    print_json_book_from_stendhal(fpath, item_origin)
