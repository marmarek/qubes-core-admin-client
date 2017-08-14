#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2010-2015  Joanna Rutkowska <joanna@invisiblethingslab.com>
# Copyright (C) 2015       Wojtek Porczyk <woju@invisiblethingslab.com>
# Copyright (C) 2017 Marek Marczykowski-Górecki
#                               <marmarek@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

'''qvm-create tool'''

# TODO list available classes
# TODO list labels (maybe in qvm-prefs)
# TODO features, devices, tags

from __future__ import print_function

import argparse
import os
import sys

import qubesadmin
import qubesadmin.tools


parser = qubesadmin.tools.QubesArgumentParser()

parser.add_argument('--class', '-C', dest='cls',
    default='AppVM',
    help='specify the class of the new domain (default: %(default)s)')

parser.add_argument('--property', '--prop',
    action=qubesadmin.tools.PropertyAction,
    help='set domain\'s property, like "internal", "memory" or "vcpus"')

parser.add_argument('--pool', '-p',
                    action='append',
                    metavar='VOLUME_NAME=POOL_NAME',
                    help='specify the pool to use for a volume')

parser.add_argument('-P',
                    metavar='POOL_NAME',
                    dest='one_pool',
                    default='',
                    help='change all volume pools to specified pool')

parser.add_argument('--template', '-t',
    action=qubesadmin.tools.SinglePropertyAction,
    help='specify the TemplateVM to use')

parser.add_argument('--label', '-l',
    action=qubesadmin.tools.SinglePropertyAction,
    help='specify the label to use for the new domain'
        ' (e.g. red, yellow, green, ...)')

parser_root = parser.add_mutually_exclusive_group()
parser_root.add_argument('--root-copy-from', '-r', metavar='FILENAME',
    help='use provided root.img instead of default/empty one'
        ' (file will be COPIED)')
parser_root.add_argument('--root-move-from', '-R', metavar='FILENAME',
    help='use provided root.img instead of default/empty one'
        ' (file will be MOVED)')

# silently ignored
parser_root.add_argument('--no-root',
    action='store_true', default=False,
    help=argparse.SUPPRESS)

parser.add_argument('name', metavar='VMNAME',
    action=qubesadmin.tools.SinglePropertyAction,
    nargs='?',
    help='name of the domain to create')


def main(args=None, app=None):
    '''Main function of qvm-create tool'''
    args = parser.parse_args(args, app=app)

    pools = {}
    pool = None
    if hasattr(args, 'pool') and args.pool:
        for pool_vol in args.pool:
            try:
                volume_name, pool_name = pool_vol.split('=')
                pools[volume_name] = pool_name
            except ValueError:
                parser.error(
                    'Pool argument must be of form: -P volume_name=pool_name')
    if args.one_pool:
        pool = args.one_pool

    if 'label' not in args.properties:
        parser.error('--label option is mandatory')

    if 'name' not in args.properties:
        parser.error('VMNAME is mandatory')

    if args.root_copy_from and args.root_move_from:
        parser.error(
            'Only one of --root-copy-from and --root-move-from can be used')

    root_source_path = args.root_copy_from or args.root_move_from
    if root_source_path and not os.path.exists(root_source_path):
        parser.error(
            'File pointed by -root-copy-from/--root-move-from does not exist')

    try:
        args.app.get_label(args.properties['label'])
    except KeyError:
        parser.error('no such label: {!r}; available: {}'.format(
            args.properties['label'],
            ', '.join(repr(l.name) for l in args.app.labels)))

    try:
        args.app.get_vm_class(args.cls)
    except KeyError:
        parser.error('no such domain class: {!r}'.format(args.cls))

    try:
        vm = args.app.add_new_vm(args.cls,
            name=args.properties.pop('name'),
            label=args.properties.pop('label'),
            template=args.properties.pop('template', None),
            pool=pool,
            pools=pools)
    except qubesadmin.exc.QubesException as e:
        args.app.log.error('Error creating VM: {!s}'.format(e))
        return 1

    retcode = 0
    for prop, value in args.properties.items():
        try:
            setattr(vm, prop, value)
        except qubesadmin.exc.QubesException as e:
            args.app.log.error(
                'Error setting property {} (but VM created): {!s}'.
                format(prop, e))
            retcode = 2

    if root_source_path:
        try:
            with open(root_source_path, 'rb') as root_file:
                vm.volumes['root'].import_data(root_file)
            if args.root_move_from:
                os.unlink(root_source_path)
        except qubesadmin.exc.QubesException as e:
            args.app.log.error(
                'Error importing root volume (but VM created): {}'.
                format(e))
            retcode = 3

    return retcode


if __name__ == '__main__':
    sys.exit(main())
