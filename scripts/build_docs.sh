#!/bin/bash
set -e

cd "$(dirname "$0")/.."

cd docs
if ! which github-pages > /dev/null; then
  echo "Installing github-pages gem..."
  gem install github-pages --version 232 --no-document
fi
github-pages build --verbose --destination ../_site
