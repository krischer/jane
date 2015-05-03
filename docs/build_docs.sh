#!/usr/bin/env bash
rm -rf site
mkdocs build
mv site ../src/jane/static/docs
