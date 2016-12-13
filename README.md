The `debugpanel` project provides a script to interact with the LOCKSS daemon's
DebugPanel servlet programmatically.

Pre-Requisites
==============

* Python 2 invocable as `python2`. If you do not have a `python2` executable:

  * Create a `bin` directory in your home directory if necessary:
    `mkdir $HOME/bin`
  
  * Add `$HOME/bin` to your `PATH` if necessary (check with `echo $PATH`)
  
  * Create a `python2` symbolic link to a Python 2 interpreter in `$HOME/bin`:
    `ln -s /path/to/python $HOME/bin/python2`

Installation
============

* Clone this Git repository in a working directory `$WORKDIR`:
  `cd $WORKDIR && git clone https://gitlab.lockss.org/lockss/debugpanel`

* Recommended:

  * Create a `bin` directory in your home directory if necessary:
    `mkdir $HOME/bin`
  
  * Add `$HOME/bin` to your `PATH` if necessary (check with `echo $PATH`)
  
  * Create a symbolic link to `$WORKDIR/debugpanel/debugpanel` in `$HOME/bin`:
    `ln -s $WORKDIR/debugpanel/debugpanel $HOME/bin`

  * Invoke as `debugpanel`.

* Alternatively:
 
  * Invoke as `$WORKDIR/debugpanel/debugpanel` directly.

Usage
=====

`debugpanel --help` displays a summary of commands and options.

`debugpanel --tutorial` displays a usage tutorial.

Upgrade
=======

Pull from Git in `$WORKDIR/debugpanel`:
`cd $WORKDIR/debugpanel && git pull`

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