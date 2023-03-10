==========
Debugpanel
==========

.. |AUID| replace:: ``--auid/-a``
.. |AUIDS| replace:: ``--auids/-A``
.. |HELP| replace:: ``--help/-h``
.. |NODE| replace:: ``--node/-n``
.. |NODES| replace:: ``--nodes/-N``

Debugpanel is a tool to interact with the LOCKSS 1.x DebugPanel servlet.

**Latest release:** 0.5.0-dev5 (?)

-------------
Prerequisites
-------------

*  `Python <https://www.python.org/>`_ 3.7 or greater.

Prerequisites for development work only:

*  `Poetry <https://python-poetry.org/>`_ 1.4 or greater.

------------
Installation
------------

Debugpanel is available from the `Python Package Index <https://pypi.org/>`_ (PyPI) as ``lockss-debugpanel``: https://pypi.org/project/lockss-debugpanel

You can install it with ``pip``. To install it in a virtual environment, simply use::

   pip3 install lockss-debugpanel

To install it in your own non-root, non-virtual environment, use the ``--user`` option::

   pip3 install --user lockss-debugpanel

.. danger::

   Do not run ``pip3``/``pip`` as ``root``, with ``sudo`` or otherwise.

The installation process adds a ``debugpanel`` executable to the ``PATH``; you can check that the installation is functional by running ``debugpanel version`` or ``debugpanel --help``.

----------
Invocation
----------

Debugpanel is invoked at the command line as::

   debugpanel

or as a Python module::

   python3 -m lockss.debugpanel

Help messages and this document use ``debugpanel`` throughout, but the two invocation styles are interchangeable.

Debugpanel uses `Commands`_, in the style of programs like ``git``, ``dnf``/``yum``, ``apt``/``apt-get``, and the like. You can see the list of available `Commands`_ by invoking ``debugpanel --help``, and you can find a usage summary of all the `Commands`_ by invoking ``debugpanel usage``::

    usage: debugpanel [-h] [--debug-cli] [--verbose] COMMAND ...

           debugpanel check-substance [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                                      [--auid AUID] [--auids FILE] [--pool-size SIZE] [--process-pool | --thread-pool]
                                      [HOST:PORT ...]

           debugpanel copyright [-h]

           debugpanel crawl [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                            [--auid AUID] [--auids FILE] [--pool-size SIZE] [--process-pool | --thread-pool]
                            [HOST:PORT ...]

           debugpanel crawl-plugins [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                                    [--pool-size SIZE] [--process-pool | --thread-pool]
                                    [HOST:PORT ...]

           debugpanel deep-crawl [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                                 [--auid AUID] [--auids FILE] [--pool-size SIZE] [--process-pool | --thread-pool] [--depth DEPTH]
                                 [HOST:PORT ...]

           debugpanel disable-indexing [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS]
                                       [--username USER] [--auid AUID] [--auids FILE] [--pool-size SIZE]
                                       [--process-pool | --thread-pool]
                                       [HOST:PORT ...]

           debugpanel license [-h]

           debugpanel poll [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                           [--auid AUID] [--auids FILE] [--pool-size SIZE] [--process-pool | --thread-pool]
                           [HOST:PORT ...]

           debugpanel reindex-metadata [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS]
                                       [--username USER] [--auid AUID] [--auids FILE] [--pool-size SIZE]
                                       [--process-pool | --thread-pool]
                                       [HOST:PORT ...]

           debugpanel reload-config [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                                    [--pool-size SIZE] [--process-pool | --thread-pool]
                                    [HOST:PORT ...]

           debugpanel usage [-h]

           debugpanel validate-files [-h] [--output-format FMT] [--node HOST:PORT] [--nodes FILE] [--password PASS] [--username USER]
                                     [--auid AUID] [--auids FILE] [--pool-size SIZE] [--process-pool | --thread-pool]
                                     [HOST:PORT ...]

           debugpanel version [-h]

-------------------
Per-Node Operations
-------------------

You can use Debugpanel `Commands`_ to get a set of LOCKSS nodes to reload their configuration (`reload-config`_ command) or crawl their plugins (`crawl-plugins`_ command).

Node Arguments and Options
==========================

Commands for `Per-Node Operations`_ expect references to one or more nodes in ``HOST:PORT`` format, for instance ``lockss.myuniversity.edu:8081``. The list of nodes to process is derived from:

*  The nodes listed as bare arguments to the command.

*  The nodes listed as |NODE| options.

*  The nodes found in the files listed as |NODES| options.

-----------------
Per-AU Operations
-----------------

You can use Debugpanel `Commands`_ to get a set of LOCKSS nodes to perform an operation on a set of AUs identified by AUID, namely crawling (`crawl`_ command), crawling with depth (`deep-crawl`_ command), polling (`poll`_ command), checking substance (`check-substance`_ command), validating files (`validate-files`_ command), reindexing metadata (`reindex-metadata`_ command), and disabling metadata indexing (`disable-indexing`_ command).

AUID Options
============

In addition to `Node Arguments and Options`_, commands for `Per-AU Operations`_ expect one or more AUIDs. The list of AUIDs to target is derived from:

*  The AUIDs listed as |AUID| options.

*  The AUIDs found in the files listed as |AUIDS| options.

--------
Commands
--------

The available commands are:

*  `check-substance`_ (cs):  cause nodes to check the substance of AUs
*  `copyright`_:             show copyright and exit
*  `crawl`_ (cr):            cause nodes to crawl AUs
*  `crawl-plugins`_ (cp):    cause nodes to crawl plugins
*  `deep-crawl`_ (dc):       cause nodes to crawl AUs, with depth
*  `disable-indexing`_ (di): cause nodes to disable metadata indexing of AUs
*  `license`_:               show license and exit
*  `poll`_ (po):             cause nodes to poll AUs
*  `reindex-metadata`_ (ri): cause nodes to reindex the metadata of AUs
*  `reload-config`_ (rc):    cause nodes to reload their configuration
*  `usage`_:                 show detailed usage and exit
*  `validate-files`_ (vf):   cause nodes to run file validation on AUs
*  `version`_:               show version and exit

Top-Level Command
=================

The top-level executable alone does not perform any action or default to a given command. It does define a few options, which you can see by invoking Debugpanel with the |HELP| option::

    usage: debugpanel [-h] [--debug-cli] [--verbose] COMMAND ...

    options:
      -h, --help            show this help message and exit
      --debug-cli           print the result of parsing command line arguments
      --verbose, -v         print verbose output

    commands:
      Add --help to see the command's own help message

      COMMAND               DESCRIPTION
        check-substance (cs)
                            cause nodes to check the substance of AUs
        copyright           show copyright and exit
        crawl (cr)          cause nodes to crawl AUs
        crawl-plugins (cp)  cause nodes to crawl plugins
        deep-crawl (dc)     cause nodes to crawl AUs, with depth
        disable-indexing (di)
                            cause nodes to disable metadata indexing of AUs
        license             show license and exit
        poll (po)           cause nodes to poll AUs
        reindex-metadata (ri)
                            cause nodes to reindex the metadata of AUs
        reload-config (rc)  cause nodes to reload their configuration
        usage               show detailed usage and exit
        validate-files (vf)
                            Cause nodes to run file validation on AUs
        version             show version and exit

.. _check-substance:

``check-substance`` (``cs``)
============================

The ``check-substance`` command is one of the `Per-AU Operations`_, used to cause nodes to check the substance of AUs. It has its own |HELP| option::

    usage: debugpanel check-substance [-h] [--output-format FMT]
                                      [--node HOST:PORT] [--nodes FILE]
                                      [--password PASS] [--username USER]
                                      [--auid AUID] [--auids FILE]
                                      [--pool-size SIZE]
                                      [--process-pool | --thread-pool]
                                      [HOST:PORT ...]

    Cause nodes to check the substance of AUs

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    AUID options:
      --auid AUID, -a AUID  add AUID to the list of AUIDs to process
      --auids FILE, -A FILE
                            add the AUIDs in FILE to the list of AUIDs to process

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _copyright:

``copyright``
=============

The ``copyright`` command displays the copyright notice for Debugpanel and exits.

.. _crawl:

``crawl`` (``cr``)
==================

The ``crawl`` command is one of the `Per-AU Operations`_, used to cause nodes to crawl AUs. It has its own |HELP| option::

    usage: debugpanel crawl-plugins [-h] [--output-format FMT] [--node HOST:PORT]
                                    [--nodes FILE] [--password PASS]
                                    [--username USER] [--pool-size SIZE]
                                    [--process-pool | --thread-pool]
                                    [HOST:PORT ...]

    Cause nodes to crawl plugins

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _crawl-plugins:

``crawl-plugins`` (``cp``)
==========================

The ``crawl-plugins`` command is one of the `Per-Node Operations`_, used to cause nodes to crawl their plugins. It has its own |HELP| option::

    usage: debugpanel crawl-plugins [-h] [--output-format FMT] [--node HOST:PORT]
                                    [--nodes FILE] [--password PASS]
                                    [--username USER] [--pool-size SIZE]
                                    [--process-pool | --thread-pool]
                                    [HOST:PORT ...]

    Cause nodes to crawl plugins

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _deep-crawl:

``deep-crawl`` (``dc``)
=======================

The ``deep-crawl`` command is one of the `Per-AU Operations`_, used to cause nodes to crawl AUs with depth. It has its own |HELP| option::

    usage: debugpanel deep-crawl [-h] [--output-format FMT] [--node HOST:PORT]
                                 [--nodes FILE] [--password PASS]
                                 [--username USER] [--auid AUID] [--auids FILE]
                                 [--pool-size SIZE]
                                 [--process-pool | --thread-pool] [--depth DEPTH]
                                 [HOST:PORT ...]

    Cause nodes to crawl AUs, with depth

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)
      --depth DEPTH, -d DEPTH
                            depth of deep crawls (default: 123)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    AUID options:
      --auid AUID, -a AUID  add AUID to the list of AUIDs to process
      --auids FILE, -A FILE
                            add the AUIDs in FILE to the list of AUIDs to process

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)


The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It has a unique option, ``--depth/-d``, which is an integer specifying the desired crawl depth.

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _disable-indexing:

``disable-indexing`` (``di``)
=============================

The ``disable-indexing`` command is one of the `Per-AU Operations`_, used to cause nodes to disable metadata indexing of AUs. It has its own |HELP| option::

    usage: debugpanel disable-indexing [-h] [--output-format FMT]
                                       [--node HOST:PORT] [--nodes FILE]
                                       [--password PASS] [--username USER]
                                       [--auid AUID] [--auids FILE]
                                       [--pool-size SIZE]
                                       [--process-pool | --thread-pool]
                                       [HOST:PORT ...]

    Cause nodes to disable metadata indexing of AUs

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    AUID options:
      --auid AUID, -a AUID  add AUID to the list of AUIDs to process
      --auids FILE, -A FILE
                            add the AUIDs in FILE to the list of AUIDs to process

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _license:

``license``
=============

The ``license`` command displays the license terms for Debugpanel and exits.

.. _poll:

``poll`` (``po``)
=================

The ``poll`` command is one of the `Per-AU Operations`_, used to cause nodes to poll AUs. It has its own |HELP| option::

    usage: debugpanel poll [-h] [--output-format FMT] [--node HOST:PORT]
                           [--nodes FILE] [--password PASS] [--username USER]
                           [--auid AUID] [--auids FILE] [--pool-size SIZE]
                           [--process-pool | --thread-pool]
                           [HOST:PORT ...]

    Cause nodes to poll AUs

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    AUID options:
      --auid AUID, -a AUID  add AUID to the list of AUIDs to process
      --auids FILE, -A FILE
                            add the AUIDs in FILE to the list of AUIDs to process

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _reindex-metadata:

``reindex-metadata`` (``ri``)
=============================

The ``reindex-metadata`` command is one of the `Per-AU Operations`_, used to cause nodes to reindex the metadata of AUs. It has its own |HELP| option::

    usage: debugpanel reindex-metadata [-h] [--output-format FMT]
                                       [--node HOST:PORT] [--nodes FILE]
                                       [--password PASS] [--username USER]
                                       [--auid AUID] [--auids FILE]
                                       [--pool-size SIZE]
                                       [--process-pool | --thread-pool]
                                       [HOST:PORT ...]

    Cause nodes to reindex the metadata of AUs

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    AUID options:
      --auid AUID, -a AUID  add AUID to the list of AUIDs to process
      --auids FILE, -A FILE
                            add the AUIDs in FILE to the list of AUIDs to process

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _reload-config:

``reload-config`` (``rc``)
==========================

The ``reload-config`` command is one of the `Per-Node Operations`_, used to cause nodes to reload their configuration. It has its own |HELP| option::

    usage: debugpanel reload-config [-h] [--output-format FMT] [--node HOST:PORT]
                                    [--nodes FILE] [--password PASS]
                                    [--username USER] [--pool-size SIZE]
                                    [--process-pool | --thread-pool]
                                    [HOST:PORT ...]

    Cause nodes to reload their configuration

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _usage:

``usage``
=========

The ``usage`` command displays the usage message of all the Debugpanel `Commands`_.

.. _validate-files:

``validate-files`` (``vf``)
=============================

The ``validate-files`` command is one of the `Per-AU Operations`_, used to cause nodes to reindex the metadata of AUs. It has its own |HELP| option::

    usage: debugpanel validate-files [-h] [--output-format FMT] [--node HOST:PORT]
                                     [--nodes FILE] [--password PASS]
                                     [--username USER] [--auid AUID]
                                     [--auids FILE] [--pool-size SIZE]
                                     [--process-pool | --thread-pool]
                                     [HOST:PORT ...]

    Cause nodes to run file validation on AUs

    options:
      -h, --help            show this help message and exit
      --output-format FMT   set tabular output format to FMT (default: simple;
                            choices: asciidoc, double_grid, double_outline,
                            fancy_grid, fancy_outline, github, grid, heavy_grid,
                            heavy_outline, html, jira, latex, latex_booktabs,
                            latex_longtable, latex_raw, mediawiki, mixed_grid,
                            mixed_outline, moinmoin, orgtbl, outline, pipe, plain,
                            presto, pretty, psql, rounded_grid, rounded_outline,
                            rst, simple, simple_grid, simple_outline, textile,
                            tsv, unsafehtml, youtrack)

    node arguments and options:
      HOST:PORT             node to process
      --node HOST:PORT, -n HOST:PORT
                            add HOST:PORT to the list of nodes to process
      --nodes FILE, -N FILE
                            add the nodes in FILE to the list of nodes to process
      --password PASS, -p PASS
                            UI password (default: interactive prompt)
      --username USER, -u USER
                            UI username (default: interactive prompt)

    AUID options:
      --auid AUID, -a AUID  add AUID to the list of AUIDs to process
      --auids FILE, -A FILE
                            add the AUIDs in FILE to the list of AUIDs to process

    job pool options:
      --pool-size SIZE      nonzero size of job pool (default: N)
      --process-pool        use a process pool
      --thread-pool         use a thread pool (default)

The command needs:

*  One or more nodes, from the `Node Arguments and Options`_ (bare arguments, |NODE| options, |NODES| options).

*  One or more AUIDs, from the `AUID Options`_ (|AUID| options, |AUIDS| options).

It also accepts `Common Options`_ for `Output Format Control`_ and `Job Pool Control`_.

.. _version:

``version``
===========

The ``version`` command displays the version number of Debugpanel and exits.

--------------
Common Options
--------------

Output Format Control
=====================

Debugpanel's tabular output is performed by the `tabulate <https://pypi.org/project/tabulate>`_ library through the ``--output-format`` option. See its PyPI page for a visual reference of the various output formats available. The **default** is ``simple``.

Job Pool Control
================

Debugpanel performs multiple operations (contacting multiple nodes and/or working on multiple AU requests per node) in parallel using a thread pool (``--thread-pool``, the default) or a process pool (``--process-pool``). You can change the size of the job pool with the ``--pool-size`` option, which accepts a nonzero integer. Note that the underlying implementation may limit the number of threads or processes despite a larger number at the command line. The default value depends on the system's CPU characteristics (represented in this document as "N"). Using ``--thread-pool --pool-size=1`` approximates no parallel processing.
