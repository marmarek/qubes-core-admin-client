.. program:: qvm-volume

:program:`qvm-volume` -- Qubes volume and block device managment
================================================================

Synopsis
--------

| :command:`qvm-volume` *COMMAND* [-h] [--verbose] [--quiet] [options] [arguments]

Description
-----------

.. TODO Add description

Options
-------

.. option:: --help, -h

   Show help message and exit

.. option:: --verbose, -v

   Increase verbosity.

.. option:: --quiet, -q

   Decrease verbosity.

Commands
--------

list
^^^^

| :command:`qvm-volume list` [-h] [--verbose] [--quiet] [-p *POOL_NAME*] [-i] [*VMNAME* [*VMNAME* ...]]

List block devices. By default the internal devices are hidden. When the
stdout is connected to a TTY `qvm-volume list` will print a pretty table by
omitting redundant data. This behaviour is disabled when `--full` option is
passed or stdout is redirected to a pipe or file.

.. option:: -p, --pool

   list volumes from specified pool

.. option:: -i, --internal

   list internal devices

.. option:: --full

   print domain names

.. option:: --all

   List volumes from all qubes. You can use :option:`--exclude` to limit the
   qubes set. Don't forget — internal devices are hidden by default!

.. option:: --exclude

   Exclude the qube from :option:`--all`.

aliases: ls, l

extend
^^^^^^
| :command:`qvm-volume extend` [-h] [--verbose] [--quiet] *POOL_NAME:VOLUME_ID* *NEW_SIZE*

Extend the volume with *POOL_NAME:VOLUME_ID* TO *NEW_SIZE*

revert
^^^^^^

| :command:`qvm-volume revert` [-h] [--verbose] [--quiet] *POOL_NAME:VOLUME_ID*

Revert a volume to previous revision.

aliases: rv, r

Authors
-------

| Joanna Rutkowska <joanna at invisiblethingslab dot com>
| Rafal Wojtczuk <rafal at invisiblethingslab dot com>
| Marek Marczykowski <marmarek at invisiblethingslab dot com>
| Bahtiar `kalkin-` Gadimov <bahtiar at gadimov dot de>

.. vim: ts=3 sw=3 et tw=80
