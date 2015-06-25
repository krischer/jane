# -*- coding: utf-8 -*-
# Author: Douglas Creager <dcreager@dcreager.net>
# This file is placed into the public domain.
#
# Modified by the ObsPy project and Jane.

# Calculates the current version number.  If possible, this is the
# output of “git describe”, modified to conform to the versioning
# scheme that setuptools uses.
import os
import inspect
from subprocess import Popen, PIPE

__all__ = ("get_git_version")


script_dir = os.path.abspath(os.path.dirname(inspect.getfile(
                                             inspect.currentframe())))
JANE_ROOT = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))


def call_git_describe(abbrev=4):
    try:
        p = Popen(['git', 'rev-parse', '--show-toplevel'],
                  cwd=JANE_ROOT, stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        path = p.stdout.readline().decode().strip()
        p.stdout.close()
    except:
        return None
    if os.path.normpath(path) != JANE_ROOT:
        return None
    try:
        p = Popen(['git', 'describe', '--dirty', '--abbrev=%d' % abbrev,
                   '--always', '--tags'],
                  cwd=JANE_ROOT, stdout=PIPE, stderr=PIPE)

        p.stderr.close()
        line = p.stdout.readline().decode()
        p.stdout.close()

        if "-" not in line and "." not in line:
            line = "0.0.0-g%s" % line
        return line.strip()
    except:
        return None


def get_git_version(abbrev=4):
    # First try to get the current version using “git describe”.
    version = call_git_describe(abbrev)

    # If we don't have anything, that's an error.
    if version is None:
        raise Exception

    # Finally, return the current version.
    return version


if __name__ == "__main__":
    print(get_git_version())
