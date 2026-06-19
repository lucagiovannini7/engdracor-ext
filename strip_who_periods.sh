#!/bin/bash
set -e

cd "$(dirname "$0")"

for f in tei/*.xml; do
    perl -i -pe '
        s{(<sp\b[^>]*\bwho=")([^"]*)(")}
         { my ($p,$v,$q)=($1,$2,$3); $v=~s/\.//g; $v=~s/ +/-/g; $p.$v.$q }ge
    ' "$f"
done

echo "Done: $(ls tei/*.xml | wc -l) files processed."
