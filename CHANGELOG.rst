=============
Release Notes
=============

------
0.10.0
------

Released: NOT YET RELEASED

Requires Python 3.10 or greater.

-----
0.9.0
-----

Released: 2026-03-18

Requires Python 3.10 or greater.

*  **Features**

   *  New command line infrastructure based on `Click Extra <https://kdeldycke.github.io/click-extra>`_, `Cloup <https://cloup.readthedocs.io/>`_ and `Click <https://click.palletsprojects.com/>`_, including expanded tabular output styles, progress bar, command sections and aliases.

   *  New ``--headings``//``--no-headings``, ``--progress``//``--no-progress`` output styles.

*  **Changes**

   *  The alias ``-u`` of ``--username`` and ``-p`` of ``--password`` are deprecated in favor of ``-U`` and ``-P`` respectively.

   *  ``--process-pool`` and ``--thread-pool`` are deprecated in favor of ``--pool-type=process-pool`` and ``--pool-type=thread-pool`` respectively.

   *  ``--output-format`` has been renamed to ``--table-format``/``-T``.

-----
0.8.2
-----

Released: 2026-02-03

Requires Python 3.9-3.13.

-----
0.8.1
-----

Released: 2025-08-13

*  **Bug Fixes**

   *  Fixed bug in the processing of ``--nodes`` and ``--auids`` options.

-----
0.8.0
-----

Released: 2025-07-01

*  **Features**

   *  Now using *lockss-pybasic* and *pydantic-argparse* internally.

*  **Changes**

   *  Bare arguments are no longer allowed and treated as node references; all node references must be specified via ``--node/-n`` or ``--nodes/-N`` options.

   *  The ``usage`` command has been removed.

-----
0.7.0
-----

Released: 2023-05-02

*  **Features**

   *  CLI improvements.

-----
0.6.1
-----

Released: 2023-03-16

*  **Bug Fixes**

   *  Files from ``--auids`` were appended to nodes.

-----
0.6.0
-----

Released: 2023-03-15

*  **Features**

   *  Now providing a Python library.

-----
0.5.0
-----

Released: 2023-03-10

*  **Features**

   *  Completely refactored to be in the package ``lockss.debugpanel``.

   *  Using Poetry to make uploadable to and installable from PyPI as `lockss-debugpanel <https://pypi.org/project/lockss-debugpanel>`_.

   *  Added the ``verify-files`` command.
