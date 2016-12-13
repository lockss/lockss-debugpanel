The `debugpanel` project provides a script to interact with the LOCKSS daemon's
DebugPanel servlet programmatically.

Pre-Requisites
==============

* Python 2 invocable as `python2` (Python 2.7 recommended)

Installation
============

* Clone this Git repository
  (`git clone https://gitlab.lockss.org/lockss/debugpanel`) into a working
  directory `$WORKDIR`.

* Recommended:

  * Create a `bin` directory in your home directory `$HOME` and add it to your
    `PATH`.

  * Create a symbolic link to `$WORKDIR/debugpanel` in `$HOME/bin`.

  * Invoke as `debugpanel`.

* Alternatively, invoke `$WORKDIR/debugpanel` directly.

Usage
=====

`debugpanel --help` displays a summary of commands and options.

`debugpanel --tutorial` displays a usage tutorial.

Upgrade
=======

Pull from Git (`git pull`) in `$WORKDIR`.

`debugpanel --version` displays the current version number.

Files
=====

* `debugpanel.py`  
  The main implementation of this project.

* `debugpanel`  
  A Shell script that calls `debugpanel.py`.

License
=======

See the `LICENSE` file, or invoke `debugpanel --license` and
`debugpanel --copyright`.