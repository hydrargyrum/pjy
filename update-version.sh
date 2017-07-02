#!/bin/sh -e

version=$1
re='[0-9]\+\.[0-9]\+\.[0-9]\+\(-[\0-9a-z.]\+\)\?'

if [ -z "$version" ]
then
    echo usage: $0 VERSION
    exit 1
fi

cd $(dirname "$0")
for f in $(git ls-files)
do
    sed -i -e "\
        /\$version/ { \
            s/$re/$version/; \
            n; \
            s/$re/$version/; \
            n; \
            s/$re/$version/; \
        }" $f
done
