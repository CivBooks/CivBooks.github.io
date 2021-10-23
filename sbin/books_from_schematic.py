'''
Extracts books from a .schematic file and prints them in JSON format.
Installation: python3 -m pip install nbt
Usage: python3 books_from_schematic.py path/to/my.schematic Server Name
Output example:
{   "item_origin": "Devoted 3.0",
    "item_title": "The Navy Seal",
    "signee": "auxchar",
    "generation": "Original",
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
from nbt import nbt
from collections import namedtuple

unknown_te_ids = set()
unknown_item_ids = set()

novalue = namedtuple('novalue', 'value')(None)

generations = {
    0: 'Original',
    1: 'Copy',
    2: 'Copy of Copy',
    3: 'Tattered',
    None: None,
}


def print_json_books_from_schematic(fpath, item_origin):
    f = nbt.NBTFile(fpath)
    for te in f['TileEntities']:
        if 'Items' not in te:
            continue  # no container, or contents unknown
        # te_id = te['id'].value
        # if te_id not in ('minecraft:chest', 'minecraft:trapped_chest') \
        #         and te_id not in unknown_te_ids:
        #     unknown_te_ids.add(te_id)
        #     print('Ignoring unexpected block id:', te_id, file=sys.stderr)
        #     continue
        for stack in te['Items']:
            item_id = stack['id'].value
            # TODO shulker boxes items may contain more books
            if item_id not in ('minecraft:written_book', 'minecraft:writable_book') \
                    and item_id not in unknown_item_ids:
                unknown_item_ids.add(item_id)
                print('Ignoring unexpected item id:', item_id, file=sys.stderr)
                continue

            tag = stack.get('tag')
            book = {
                'item_origin': item_origin,
                'item_title': tag.get('title', novalue).value if tag else None,
                'signee': tag.get('author', novalue).value if tag else None,
                'generation': (generations[tag.get('generation', novalue).value]
                               if tag and 'generation' in tag else None),
                'pages': ([cleanup_page(page.value) for page in tag['pages']]
                          if tag and 'pages' in tag else []),
            }
            print(json.dumps(book, separators=(',', ':')))


# This schematic to json book extraction script was created by Gjum. github.com/Gjum


def cleanup_page(in_str):
    wrap_start, wrap_end = '{\"text\":\"', '\"}'
    if not in_str.startswith(wrap_start) or not in_str.endswith(wrap_end):
        return in_str
    # it's json
    j = json.loads(in_str)
    if len(j) > 1:
        print('Unknown keys in page JSON, keeping as JSON:',
              ' '.join(j.keys()), file=sys.stderr)
        return in_str
    return j['text']


if __name__ == "__main__":
    fpath = sys.argv[1]
    item_origin = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
    print_json_books_from_schematic(fpath, item_origin)
