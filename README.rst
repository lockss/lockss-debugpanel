==========
Debugpanel
==========

.. |RELEASE| replace:: 0.8.0
.. |RELEASE_DATE| replace:: 2025-07-01

.. |AUID| replace:: ``--auid/-a``
.. |AUIDS| replace:: ``--auids/-A``
.. |HELP| replace:: ``--help/-h``
.. |NODE| replace:: ``--node/-n``
.. |NODES| replace:: ``--nodes/-N``

.. image:: https://assets.lockss.org/images/logos/debugpanel/debugpanel_128x128.png
   :alt: Debugpanel logo
   :align: right

Debugpanel is a library and command line tool to interact with the LOCKSS 1.x DebugPanel servlet.

:Latest release: |RELEASE| (|RELEASE_DATE|)
:Release notes: `<CHANGELOG.rst>`_
:License: `<LICENSE>`_

-----------------
Table of Contents
-----------------

*  `Quick Start`_

*  `Installation`_

*  `Overview`_

   *  `Per-Node Operations`_

   *  `Per-AU Operations`_

*  `Command Line Tool`_

   *  `Synopsis`_

   *  `Node Options`_

   *  `AUID Options`_

   *  `Commands`_

      *  `Top-Level Program`_

      *  `check-substance`_

      *  `copyright`_

      *  `crawl`_

      *  `crawl-plugins`_

      *  `deep-crawl`_

      *  `disable-indexing`_

      *  `license`_

      *  `poll`_

      *  `reindex-metadata`_

      *  `reload-config`_

      *  `validate-files`_

      *  `version`_

   *  `Output Format Options`_

   *  `Job Pool Options`_

*  `Library`_

-----------
Quick Start
-----------

::

    # Install with pipx
    pipx install lockss-debugpanel

    # Verify installation and discover all the commands
    debugpanel --help

    # Reload config on lockss1.example.edu:8081
    debugpanel reload-config -n lockss1.example.edu:8081

    # Crawl AUIDs from list.txt on lockss1.example.edu:8081 and lockss2.example.edu:8081
    # ...First alternative: each node gets a -n
    debugpanel crawl -A list.txt -n lockss1.example.edu:8081 -n lockss2.example.edu:8081

    # ...Second alternative: each -n can have more than argument
    debugpanel crawl -A list.txt -n lockss1.example.edu:8081 lockss2.example.edu:8081

------------
Installation
------------

Debugpanel is available from the `Python Package Index <https://pypi.org/>`_ (PyPI) as ``lockss-debugpanel`` (https://pypi.org/project/lockss-debugpanel).

*  To install Debugpanel in your own non-virtual environment, we recommend using ``pipx``::

       pipx install lockss-debugpanel

*  To install Debugpanel globally for every user, you can use ``pipx`` as ``root`` with the ``--global`` flag (provided you are running a recent enough ``pipx``)::

       pipx install --global lockss-debugpanel

*  To install Debugpanel in a Python virtual environment, simply use ``pip``::

       pip install lockss-debugpanel

The installation process adds a ``lockss.debugpanel`` Python `Library`_ and a ``debugpanel`` `Command Line Tool`_. You can check at the command line that the installation is functional by running ``debugpanel version`` or ``debugpanel --help``.

--------
Overview
--------

Per-Node Operations
===================

Some operations operate on one or more nodes.

========================= ================ ========
Operation                 Command          Function
========================= ================ ========
Crawl plugins             `crawl-plugins`_ ``crawl_plugins()``
Reload node configuration `reload-config`_ ``reload_config()``
========================= ================ ========

Per-AU Operations
=================

Some operation operate on one or more AUs on one or more nodes.

================================ =================== ========
Operation                        Command             Function
================================ =================== ========
Check substance of AUs           `check-substance`_  ``check_substance()``
Crawl AUs                        `crawl`_            ``crawl()``
Crawl AUs with depth             `deep-crawl`_       ``deep_crawl()``
Disable metadata indexing of AUs `disable-indexing`_ ``disable_indexing()``
Poll                             `poll`_             ``poll()``
Reindex AU metadata              `reindex-metadata`_ ``reindex_metadata()``
Validate AU files                `validate-files`_   ``validate_files()``
================================ =================== ========

-----------------
Command Line Tool
-----------------

Debugpanel is invoked at the command line as::

    debugpanel

or as a Python module::

    python -m lockss.debugpanel

Help messages and this document use ``debugpanel`` throughout, but the two invocation styles are interchangeable.

Synopsis
========

.. note::

   As of version 0.8.0, bare arguments are no longer allowed and treated as nodes; all nodes must be listed via the `Node Options`_ |NODE| and |NODES|.

.. note::

   As of version 0.8.0, the ``usage`` command no longer exists.

Debugpanel uses `Commands`_, in the style of programs like ``git``, ``dnf``/``yum``, ``apt``/``apt-get``, and the like. You can see the list of available `Commands`_ by invoking ``debugpanel --help``::

    Usage: debugpanel [-h]
                      {check-substance,copyright,cp,cr,crawl,crawl-plugins,cs,dc,deep-crawl,di,disable-indexing,license,po,poll,rc,reindex-metadata,reload-config,ri,validate-files,version,vf} ...

    Tool to interact with the LOCKSS 1.x DebugPanel servlet

    Commands:
      {check-substance,copyright,cp,cr,crawl,crawl-plugins,cs,dc,deep-crawl,di,disable-indexing,license,po,poll,rc,reindex-metadata,reload-config,ri,validate-files,version,vf}
        check-substance     cause nodes to check the substance of AUs
        copyright           print the copyright and exit
        cp                  synonym for: crawl-plugins
        cr                  synonym for: crawl
        crawl               cause nodes to crawl AUs
        crawl-plugins       cause nodes to crawl plugins
        cs                  synonym for: check-substance
        dc                  synonym for: deep-crawl
        deep-crawl          cause nodes to deeply crawl AUs
        di                  synonym for: disable-indexing
        disable-indexing    cause nodes to disable metadata indexing for AUs
        license             print the software license and exit
        po                  synonym for: poll
        poll                cause nodes to poll AUs
        rc                  synonym for: reload-config
        reindex-metadata    cause nodes to reindex the metadata of AUs
        reload-config       cause nodes to reload their configuration
        ri                  synonym for: reindex-metadata
        validate-files      cause nodes to validate the files of AUs
        version             print the version number and exit
        vf                  synonym for: validate-files

    Help:
      -h, --help            show this help message and exit

Node Options
============

.. note::

   As of version 0.8.0, bare arguments are no longer allowed and treated as nodes; all nodes must be listed via the `Node Options`_ |NODE| and |NODES|.

`Commands`_ for `Per-Node Operations`_ expect one or more node references in ``HOST:PORT`` format, for instance ``lockss.myuniversity.edu:8081``. The set of nodes to process is derived from:

*  The nodes listed as |NODE| options.

*  The nodes found in the files listed as |NODES| options.

Examples::

    debugpanel reload-config --node node1:8081 --node node2:8081 --node node3:8081 ... --thread-pool ...

    debugpanel reload-config -n node1:8081 -n node2:8081 -n node3:8081 ... --thread-pool ...

    debugpanel reload-config --node node1:8081 node2:8081 node3:8081 ... --thread-pool ...

    debugpanel reload-config -n node1:8081 node2:8081 node3:8081 ... --thread-pool ...

    debugpanel reload-config --nodes list1.txt --nodes list2.txt --nodes list3.txt ... --thread-pool ...

    debugpanel reload-config -N list1.txt -N list2.txt -N list3.txt ... --thread-pool ...

    debugpanel reload-config --nodes list1.txt list2.txt list3.txt ... --thread-pool ...

    debugpanel reload-config -N list1.txt list2.txt list3.txt ... --thread-pool ...

AUID Options
============

In addition to `Node Options`_, `Commands`_ for `Per-AU Operations`_ expect one or more AUIDs. The set of AUIDs to process is derived from:

*  The AUIDs listed as |AUID| options.

*  The AUIDs found in the files listed as |AUIDS| options.

Examples::

    debugpanel poll ... --auid auid1 --auids auid2 --auid auid3 ... --thread-pool ...

    debugpanel poll ... -a auid1 -a auid2 -a auid3 ... --thread-pool ...

    debugpanel poll ... --auid auid1 auid2 auid3 ... --thread-pool ...

    debugpanel poll ... -a auid1 auid2 auid3 ... --thread-pool ...

    debugpanel poll ... --auids list1.txt --auids list2.txt --auid list3.txt ... --thread-pool ...

    debugpanel poll ... -A list1.txt -A list2.txt -A list3.txt ... --thread-pool ...

    debugpanel poll ... --auids list1.txt list2.txt list3.txt ... --thread-pool ...

    debugpanel poll ... -A list1.txt list2.txt list3.txt ... --thread-pool ...

Commands
========

The available commands are:

=================== ============ =======
Command             Abbreviation Purpose
=================== ============ =======
`check-substance`_  cs           cause nodes to check the substance of AUs
`copyright`_                     print the copyright and exit
`crawl`_            cr           cause nodes to crawl AUs
`crawl-plugins`_    cp           cause nodes to crawl plugins
`deep-crawl`_       dc           cause nodes to deeply crawl AUs
`disable-indexing`_ di           cause nodes to disable metadata indexing for AUs
`license`_                       print the software license and exit
`poll`_             po           cause nodes to poll AUs
`reindex-metadata`_ ri           cause nodes to reindex the metadata of AUs
`reload-config`_    rc           cause nodes to reload their configuration
`validate-files`_   vf           cause nodes to validate the files of AUs
`version`_                       print the version number and exit
=================== ============ =======

Top-Level Program
-----------------

The top-level executable alone does not perform any action or default to a given command::

    $ debugpanel
    Usage: debugpanel [-h]
                      {check-substance,copyright,cp,cr,crawl,crawl-plugins,cs,dc,deep-crawl,di,disable-indexing,license,po,poll,rc,reindex-metadata,reload-config,ri,validate-files,version,vf} ...
    debugpanel: error: the following arguments are required: {check-substance,copyright,cp,cr,crawl,crawl-plugins,cs,dc,deep-crawl,di,disable-indexing,license,po,poll,rc,reindex-metadata,reload-config,ri,validate-files,version,vf}

.. _check-substance:

``check-substance`` (``cs``)
----------------------------

The ``check-substance`` (or alternatively ``cs``) command is one of the `Per-AU Operations`_, used to cause nodes to check the substance of AUs. It has its own |HELP| option::

    Usage: debugpanel check-substance [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME]
                                      [-a AUID [AUID ...]] [-A AUIDS [AUIDS ...]] [--pool-size POOL_SIZE] [--process-pool]
                                      [--thread-pool] [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _copyright:

``copyright``
-------------

The ``copyright`` command displays the copyright notice for Debugpanel and exits.

.. _crawl:

``crawl`` (``cr``)
------------------

The ``crawl`` (or alternatively ``cr``) command is one of the `Per-AU Operations`_, used to cause nodes to crawl AUs. It has its own |HELP| option::

    Usage: debugpanel crawl [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME] [-a AUID [AUID ...]]
                            [-A AUIDS [AUIDS ...]] [--pool-size POOL_SIZE] [--process-pool] [--thread-pool]
                            [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _crawl-plugins:

``crawl-plugins`` (``cp``)
--------------------------

The ``crawl-plugins`` (or alternatively ``cp``) command is one of the `Per-Node Operations`_, used to cause nodes to crawl their plugins. It has its own |HELP| option::

    Usage: debugpanel crawl-plugins [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME]
                                    [--pool-size POOL_SIZE] [--process-pool] [--thread-pool] [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _deep-crawl:

``deep-crawl`` (``dc``)
-----------------------

The ``deep-crawl`` (or alternatively ``dc``) command is one of the `Per-AU Operations`_, used to cause nodes to crawl AUs with depth. It has its own |HELP| option::

    Usage: debugpanel deep-crawl [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME] [-a AUID [AUID ...]]
                                 [-A AUIDS [AUIDS ...]] [-d DEPTH] [--pool-size POOL_SIZE] [--process-pool] [--thread-pool]
                                 [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      -d, --depth DEPTH     (deep crawl) set crawl depth (default: 123)
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It has a unique option, ``--depth/-d``, which is an strictly positive integer specifying the desired crawl depth.

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _disable-indexing:

``disable-indexing`` (``di``)
-----------------------------

The ``disable-indexing`` (or alternatively ``di``) command is one of the `Per-AU Operations`_, used to cause nodes to disable metadata indexing of AUs. It has its own |HELP| option::

    Usage: debugpanel disable-indexing [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME]
                                       [-a AUID [AUID ...]] [-A AUIDS [AUIDS ...]] [--pool-size POOL_SIZE] [--process-pool]
                                       [--thread-pool] [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. COMMENT PyPI won't accept an anchor here meaning the double backticks don't make it different

``license``
-----------

The ``license`` command displays the license terms for Debugpanel and exits.

.. _poll:

``poll`` (``po``)
-----------------

The ``poll`` (or alternatively ``po``) command is one of the `Per-AU Operations`_, used to cause nodes to poll AUs. It has its own |HELP| option::

    Usage: debugpanel poll [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME] [-a AUID [AUID ...]]
                           [-A AUIDS [AUIDS ...]] [--pool-size POOL_SIZE] [--process-pool] [--thread-pool]
                           [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _reindex-metadata:

``reindex-metadata`` (``ri``)
-----------------------------

The ``reindex-metadata`` command is one of the `Per-AU Operations`_, used to cause nodes to reindex the metadata of AUs. It has its own |HELP| option::

    Usage: debugpanel reindex-metadata [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME]
                                       [-a AUID [AUID ...]] [-A AUIDS [AUIDS ...]] [--pool-size POOL_SIZE] [--process-pool]
                                       [--thread-pool] [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _reload-config:

``reload-config`` (``rc``)
--------------------------

The ``reload-config`` (or alternatively ``rc``) command is one of the `Per-Node Operations`_, used to cause nodes to reload their configuration. It has its own |HELP| option::

    Usage: debugpanel reload-config [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME]
                                    [--pool-size POOL_SIZE] [--process-pool] [--thread-pool] [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _validate-files:

``validate-files`` (``vf``)
---------------------------

The ``validate-files`` (or alternatively ``vf``) command is one of the `Per-AU Operations`_, used to cause nodes to reindex the metadata of AUs. It has its own |HELP| option::

    Usage: debugpanel validate-files [-h] [-n NODE [NODE ...]] [-N NODES [NODES ...]] [-p PASSWORD] [-u USERNAME] [-a AUID [AUID ...]]
                                     [-A AUIDS [AUIDS ...]] [--pool-size POOL_SIZE] [--process-pool] [--thread-pool]
                                     [--output-format OUTPUT_FORMAT]

    Optional Arguments:
      -n, --node NODE [NODE ...]
                            (nodes) add one or more nodes to the set of nodes to process (default: [])
      -N, --nodes NODES [NODES ...]
                            (nodes) add the nodes listed in one or more files to the set of nodes to process (default: [])
      -p, --password PASSWORD
                            (nodes) UI password; interactive prompt if not specified (default: None)
      -u, --username USERNAME
                            (nodes) UI username; interactive prompt if not unspecified (default: None)
      -a, --auid AUID [AUID ...]
                            (AUIDs) add one or more AUIDs to the set of AUIDs to process (default: [])
      -A, --auids AUIDS [AUIDS ...]
                            (AUIDs) add the AUIDs listed in one or more files to the set of AUIDs to process (default: [])
      --pool-size POOL_SIZE
                            (job pool) set the job pool size (default: None)
      --process-pool        (job pool) use a process pool (default: False)
      --thread-pool         (job pool) use a thread pool (default: False)
      --output-format OUTPUT_FORMAT
                            set the output format; choices: asciidoc, double_grid, double_outline, fancy_grid, fancy_outline, github,
                            grid, heavy_grid, heavy_outline, html, jira, latex, latex_booktabs, latex_longtable, latex_raw, mediawiki,
                            mixed_grid, mixed_outline, moinmoin, orgtbl, outline, pipe, plain, presto, pretty, psql, rounded_grid,
                            rounded_outline, rst, simple, simple_grid, simple_outline, textile, tsv, unsafehtml, youtrack (default:
                            simple)

    Help:
      -h, --help            show this help message and exit

The command needs:

*  One or more nodes, from the `Node Options`_ (|NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Output Format Options`_ and `Job Pool Options`_.

.. _version:

``version``
-----------

The ``version`` command displays the version number of Debugpanel and exits.

Output Format Options
---------------------

Debugpanel's tabular output is performed by the `tabulate <https://pypi.org/project/tabulate>`_ library through the ``--output-format`` option. See its PyPI page for a visual reference of the various output formats available. The **default** is ``simple``.

Job Pool Options
----------------

Debugpanel performs multiple operations in parallel, contacting multiple nodes and/or working on multiple AU requests per node, using a thread pool (``--thread-pool``) or a process pool (``--process-pool``). If neither is specified, by default a thread pool is used. You can change the size of the job pool with the ``--pool-size`` option, which accepts a nonzero integer. Note that the underlying implementation may limit the number of threads or processes despite a larger number requested at the command line. The default value depends on the system's CPU characteristics (represented in this document as "N"). Using ``--thread-pool --pool-size=1`` approximates no parallel processing.

.. _Node:
.. _check_substance():
.. _crawl():
.. _crawl_plugins():
.. _deep_crawl():
.. _disable_indexing():
.. _poll():
.. _reindex_metadata():
.. _reload_config():
.. _validate_files():

-------
Library
-------

You can use Debugpanel as a Python library.

The ``lockss.debugpanel`` module's `Node`_ class can create a node object from a node reference (a string like ``host:8081``, ``http://host:8081``, ``http://host:8081/``, ``https://host:8081``, ``https://host:8081/``; no protocol defaults to ``http://``), a username, and a password.

.. note::

   The ``node()`` function is deprecated and will be removed in a future release.

This node object can be used as the argument to `crawl_plugins()`_ or `reload_config()`_.

It can also be used as the first argument to `check_substance()`_, `crawl()`_, `deep_crawl()`_, `disable_indexing()`_, `poll()`_, `reindex_metadata()`_, or `validate_files()`_, together with an AUID string as the second argument.

The `deep_crawl()`_ function has an optional third argument, ``depth``, for the crawl depth (whch defaults to ``lockss.debugpanel.DEFAULT_DEPTH``).

All operations return the modified ``http.client.HTTPResponse`` object from ``urllib.request.urlopen()`` (see https://docs.python.org/3.9/library/urllib.request.html#urllib.request.urlopen). A status code of 200 indicates that the request to the node was made successfully (but not much else; for example if there is no such AUID for an AUID operation, nothing happens).

Use of the module is illustrated in this example::

    from getpass import import getpass
    from lockss.debugpanel import Node, poll

    hostport: str = '...'
    username: str = input('Username: ')
    password: str = getpass.getpass('Password: ')
    node: Node = Node(hostport, username, password)
    auid: str = '...'

    try:
        resp = poll(node, auid)
        if resp.status == 200:
            print('Poll requested (200)')
        else:
            print(f'{resp.reason} ({resp.status})')
    except Exception as exc:
        print(f'Error: {exc!s}')

