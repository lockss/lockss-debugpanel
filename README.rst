==========
Debugpanel
==========

.. |RELEASE| replace:: 0.8.1
.. |RELEASE_DATE| replace:: 2025-08-13
.. |DEBUGPANEL| replace:: **Debugpanel**

.. image:: https://assets.lockss.org/images/logos/debugpanel/debugpanel_128x128.png
   :alt: Debugpanel logo
   :align: right

|DEBUGPANEL| is a library and command line tool to interact with the LOCKSS 1.x DebugPanel servlet.

:Latest release: |RELEASE| (|RELEASE_DATE|)
:Documentation: https://docs.lockss.org/en/latest/software/debugpanel
:Release notes: `CHANGELOG.rst <https://github.com/lockss/lockss-debugpanel/blob/main/CHANGELOG.rst>`_
:License: `LICENSE <https://github.com/lockss/lockss-debugpanel/blob/main/LICENSE>`_
:Repository: https://github.com/lockss/lockss-debugpanel
:Issues: https://github.com/lockss/lockss-debugpanel/issues

----

Quick Start::

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
