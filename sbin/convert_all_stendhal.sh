#!/bin/bash
if [ $# -lt 2 ]
    then
        echo $#
        echo "Usage: ./convert_all_stendhal.sh PATH/TO/STENDHAL/FOLDER iteration_name"
        exit 1
fi
iteration="${@: -1}"
argc=$(($# - 1))
for ((i = 0 ; i < argc ; i++)); do
    python sbin/book_from_stendhal.py "$1" $iteration | python sbin/book_html_from_json.py
    echo "Converted: '$1' to html"
    shift
done