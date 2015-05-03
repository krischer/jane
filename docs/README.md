## Building Jane's documentation

The docs are written using `mkdocs`. Install it with

```bash
$ pip install mkdocs
```

and execute the `build_docs.sh` script to build and copy the docs to Jane's
static site directory. The compiled docs are not in the repository so this
needs to be done each time the documentation is updated / Jane is installed.

When writing the docs, you can launch a live-reloading instance of `mkdocs`
with

```bash
$ mkdocs serve
```
