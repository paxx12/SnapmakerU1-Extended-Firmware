#!/bin/bash

set -e

cd "$(dirname "$0")/.."

cd docs

echo ">> Installing dependencies..."
bundle install

echo ">> Building Jekyll site..."
bundle exec jekyll build --destination ../_site

echo "[+] Build complete! Site generated in ../_site/"
