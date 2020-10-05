The `debugpanel` project provides a script to interact with the LOCKSS daemon's
DebugPanel servlet programmatically.

Pre-Requisites
==============

*   Python 3 invocable as `python3` or `python`.

Installation
============

1.  Clone this Git repository into an installation directory `$INSTALLDIR`,
    for instance `$HOME/software`:
    
    ```
    cd $INSTALLDIR
    git clone git@code.stanford.edu:lockss/tools/debugpanel
    ```
    
    This creates a `debugpanel` directory in `$INSTALLDIR`, in which you will
    find the `debugpanel` shell script and the `debugpanel.py` Python script.

1.  Create a symbolic link to the `debugpanel` shell script (i.e.
    `$INSTALLDIR/debugpanel/debugpanel`) in a PATH directory `$BINDIR`, for
    example `$HOME/bin`:
    
    ```
    ln -s $INSTALLDIR/debugpanel/debugpanel $BINDIR
    ```

1.  `$BINDIR` must be on the PATH. For interactive command line use, this means
    that `$BINDIR` must appear in the semicolon-separated list displayed when
    you type `echo $PATH`. If it does not appear, you can alter your shell
    startup scripts to add it in all future shell sessions. For instance in a
    Bash environment, you can add this to `$HOME/.bashrc`:
    
    ```
    export PATH=$HOME/bin:$PATH
    ```
    
    For non-interactive enironments like `cron` jobs, be mindful that the PATH
    typically does not include much by default. You can add `$BINDIR` to the
    PATH seen by `cron`, or you can write `cron` jobs that explicitly invoke
    `debugpanel` by its full path (the expansion of `$BINDIR/debugpanel`).

Usage
=====

*   ```
    debugpanel --help
    ```

    Displays a summary of commands and options.

Upgrade
=======

Pull from Git (`git pull`) in `$INSTALLDIR/debugpanel`. Use
`debugpanel --version` to verify the version number after.

Files
=====

*   [`debugpanel`](debugpanel)

    The point of entry of this project.

*   [`debugpanel.py`](debugpanel.py)

    The Python implementation of this project.

License
=======

See the [LICENSE](LICENSE) file, or invoke `debugpanel --license` and
`debugpanel --copyright`.

