#!/bin/sh
find tests ! -type d | while read file; do
  python Parser.py $file >/dev/null
  if [ "$?" -eq "0" ]; then
    echo "Successful: $file"
  fi
  if [ "$?" -ne "0" ]; then
    echo "Broken test ($?): $file"
  fi
done 
