============
denonavr-cli
============

denonavr-cli is a trivial CLI client for Denon AV receivers based
on the denonavr_ library.  Its biggest advantage is receiver
autodiscovery, so you don't have to specify the IP address.

When run without arguments, it scans the network for AVRs.  If it finds
exactly one, it displays its status::

    $ denonavr-cli
    Power: ON       Volume: -54.0 dB         Input: HEOS Music

Note that if there are more AVRs on the network, you need to specify
the host explicitly::

    $ denonavr-cli -H 192.168.1.6

After every call, the executable caches the host used, eliminating
the autodiscovery delay for subsequent commands (but ``-H`` always
overrides the cached value).  If the cached host is no longer
responding, it is discarded and autodiscovery is reenabled.  You can
also manually clear the cache via::

    $ denonavr-cli --host-cache=reset

To see the available commands and options::

    $ denonavr-cli --help

In general, commands without additional arguments print the current
status in a machine-readable format, e.g.::

    $ denonavr-cli volume
    -54.0

The commands that alter the state generally print the new value
after performing the action::

    $ denonavr-cli volume up 4
    -50.0


.. _denonavr: https://pypi.org/project/denonavr/
