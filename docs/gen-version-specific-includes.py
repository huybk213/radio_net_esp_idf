#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Python script to generate ReSTructured Text .inc snippets
# with version-based content for this IDF version

from __future__ import print_function
from __future__ import unicode_literals
from io import open
import subprocess
import os
import sys
import re

TEMPLATES = {
    "en": {
        "git-clone-bash": """
.. code-block:: bash

    cd ~/esp
    git clone %(clone_args)s--recursive https://github.com/espressif/esp-idf.git
        """,

        "git-clone-windows": """
.. code-block:: batch

    mkdir %%userprofile%%\\esp
    cd %%userprofile%%\\esp
    git clone %(clone_args)s--recursive https://github.com/espressif/esp-idf.git
            """,

        "git-clone-notes": {
            "template": """
.. note::

    %(extra_note)s

.. note::

    %(zipfile_note)s
""",
            "master": 'This command will clone the master branch, which has the latest development ("bleeding edge") '
            'version of ESP-IDF. It is fully functional and updated on weekly basis with the most recent features and bugfixes.',
            "branch": 'The ``git clone`` option ``-b %(clone_arg)s`` tells git to clone the %(ver_type)s in the ESP-IDF repository ``git clone`` '
            'corresponding to this version of the documentation.',
            "zipfile": {
                "stable": 'As a fallback, it is also possible to download a zip file of this stable release from the `Releases page`_. '
                          'Do not download the "Source code" zip file(s) generated automatically by GitHub, they do not work with ESP-IDF.',
                "unstable": 'GitHub\'s "Download zip file" feature does not work with ESP-IDF, a ``git clone`` is required. As a fallback, '
                            '`Stable version`_ can be installed without Git.'
            },  # zipfile
        },  # git-clone-notes
        "version-note": {
            "master": """
.. note::
     This is documentation for the master branch (latest version) of ESP-IDF. This version is under continual development.
     `Stable version`_ documentation is available, as well as other :doc:`/versions`.
""",
            "stable": """
.. note::
     This is documentation for stable version %s of ESP-IDF. Other :doc:`/versions` are also available.
""",
            "branch": """
.. note::
     This is documentation for %s ``%s`` of ESP-IDF. Other :doc:`/versions` are also available.
"""
        },  # version-note
    },  # en
    "zh_CN": {
        "git-clone-bash": """
.. code-block:: bash

    cd ~/esp
    git clone %(clone_args)s--recursive https://github.com/espressif/esp-idf.git
            """,

        "git-clone-windows": """
.. code-block:: batch

    mkdir %%userprofile%%\\esp
    cd %%userprofile%%\\esp
    git clone %(clone_args)s--recursive https://github.com/espressif/esp-idf.git
        """,

        "git-clone-notes": {
            "template": """
.. note::

    %(extra_note)s

.. note::

    %(zipfile_note)s
""",
            "master": '?????????????????? master ??????????????????????????? ESP-IDF ?????????????????????????????????????????????????????????????????????????????????????????????',
            "branch": '``git clone`` ????????? ``-b %(clone_arg)s`` ???????????? git ??? ESP-IDF ??????????????????????????????????????????????????????',
            "zipfile": {
                "stable": '??????????????????????????? `Releases page`_ ???????????????????????? zip ???????????????????????? GitHub ???????????????"?????????"??? zip ??????????????????????????? ESP-IDF???',
                "unstable": 'GitHub ???"?????? zip ??????"????????????????????? ESP-IDF????????????????????? ``git clone`` ????????????????????????????????????????????? Git ?????????????????? '
                            '`Stable version`_ ??? zip ???????????????'
            },  # zipfile
        },  # git-clone
        "version-note": {
            "master": """
.. note::
     ??????ESP-IDF master ???????????????????????????????????????????????????????????????????????? `Stable version`_ ??????????????????????????????????????? :doc:`/versions` ????????????
     This is documentation for the master branch (latest version) of ESP-IDF. This version is under continual development. `Stable version`_ documentation is '
     'available, as well as other :doc:`/versions`.
""",
            "stable": """
.. note::
     ??????ESP-IDF ???????????? %s ??????????????????????????????????????? :doc:`/versions` ????????????
""",
            "branch": """
.. note::
     ??????ESP-IDF %s ``%s`` ????????????????????????????????????????????? :doc:`/versions` ????????????
"""
        },  # version-note
    }  # zh_CN
}


def main():
    if len(sys.argv) != 3:
        print("Usage: gen-git-clone.py <language> <output file path>")
        sys.exit(1)

    language = sys.argv[1]
    out_dir = sys.argv[2]
    if not os.path.exists(out_dir):
        print("Creating directory %s" % out_dir)
        os.mkdir(out_dir)

    template = TEMPLATES[language]

    version, ver_type, is_stable = get_version()

    write_git_clone_inc_files(template, out_dir, version, ver_type, is_stable)
    write_version_note(template["version-note"], out_dir, version, ver_type, is_stable)
    print("Done")


def write_git_clone_inc_files(templates, out_dir, version, ver_type, is_stable):
    def out_file(basename):
            p = os.path.join(out_dir, "%s.inc" % basename)
            print("Writing %s..." % p)
            return p

    if version == "master":
        clone_args = ""
    else:
        clone_args = "-b %s " % version

    with open(out_file("git-clone-bash"), "w", encoding="utf-8") as f:
        f.write(templates["git-clone-bash"] % locals())

    with open(out_file("git-clone-windows"), "w", encoding="utf-8") as f:
        f.write(templates["git-clone-windows"] % locals())

    with open(out_file("git-clone-notes"), "w", encoding="utf-8") as f:
        template = templates["git-clone-notes"]

        zipfile = template["zipfile"]

        if version == "master":
            extra_note = template["master"]
            zipfile_note = zipfile["unstable"]
        else:
            extra_note = template["branch"] % {"clone_arg": version, "ver_type": ver_type}
            zipfile_note = zipfile["stable"] if is_stable else zipfile["unstable"]

        f.write(template["template"] % locals())

    print("Wrote git-clone-xxx.inc files")


def write_version_note(template, out_dir, version, ver_type, is_stable):
    if version == "master":
        content = template["master"]
    elif ver_type == "tag" and is_stable:
        content = template["stable"] % version
    else:
        content = template["branch"] % (ver_type, version)
    out_file = os.path.join(out_dir, "version-note.inc")
    with open(out_file, "w", encoding='utf-8') as f:
        f.write(content)
    print("%s written" % out_file)


def get_version():
    """
    Returns a tuple of (name of branch/tag, type branch/tag, is_stable)
    """
    # Trust what RTD says our version is, if it is set
    version = os.environ.get("READTHEDOCS_VERSION", None)
    if version == "latest":
        return ("master", "branch", False)

    # Otherwise, use git to look for a tag
    try:
        tag = subprocess.check_output(["git", "describe", "--tags", "--exact-match"]).strip()
        is_stable = re.match(r"v[0-9\.]+$", tag) is not None
        return (tag, "tag", is_stable)
    except subprocess.CalledProcessError:
        pass

    # No tag, look for a branch
    refs = subprocess.check_output(["git", "for-each-ref", "--points-at", "HEAD", "--format", "%(refname)"])
    print("refs:\n%s" % refs)
    refs = refs.split(b"\n")
    # Note: this looks for branches in 'origin' because GitLab CI doesn't check out a local branch
    branches = [r.replace(b"refs/remotes/origin/",b"").strip() for r in refs if r.startswith(b"refs/remotes/origin/")]
    if len(branches) == 0:
        # last resort, return the commit (may happen on Gitlab CI sometimes, unclear why)
        return (subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip(), "commit", False)
    if "master" in branches:
        return ("master", "branch", False)
    else:
        return (branches[0], "branch", False)  # take whatever the first branch is


if __name__ == "__main__":
    main()
