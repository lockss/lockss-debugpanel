The `debugpanel` project provides a script to interact with the LOCKSS daemon's
DebugPanel servlet programmatically.

Pre-Requisites
==============

*   Python 2 invocable as `python2`. If you have a `python` executable but not a
    `python2` alias:

    *   For a single user: create `$HOME/bin` and add it to the `$PATH` if
        needed, then:

        ```
        ln -s /path/to/python2exec $HOME/bin/python2
        ```

    *   For all users (as root):

        ```
        ln -s /path/to/python2exec /usr/local/bin/python2
        ```

Installation
============

*   Clone this Git repository into an installation directory (`$INSTALLDIR`):

    *   For a single user, for instance where `$INSTALLDIR` is `$HOME/software`:

        ```
        cd $HOME/software
        git clone git@gitlab.lockss.org:lockss/debugpanel
        ```

    *   For all users (as root):

        ```
        cd /usr/local/share
        git clone git@gitlab.lockss.org:lockss/debugpanel
        ```

*   Create a symbolic link to `debugpanel`:

    *   For a single user, for instance where `$INSTALLDIR` is `$HOME/software`:
        create `$HOME/bin` and add it to the `$PATH` if needed, then:

        ```
        ln -s $HOME/software/debugpanel/debugpanel $HOME/bin/
        ```

    *   For all users (as root):

        ```
        ln -s /usr/local/share/debugpanel/debugpanel /usr/local/bin/
        ```

Usage
=====

*   ```
    debugpanel --help
    ```

    Displays a summary of commands and options.

*   ```
    debugpanel --tutorial
    ```

    Displays a usage tutorial.

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

