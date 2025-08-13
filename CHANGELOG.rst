=============
Release Notes
=============

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
