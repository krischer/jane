#!/usr/bin/env bash
rm -rf site
mkdocs build
rm -rf ../src/jane/static/docs
mv site ../src/jane/static/docs
