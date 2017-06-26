# encoding=utf-8
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2016 Marek Marczykowski-Górecki
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

'''qvm-firewall tool'''

import argparse
import sys
import itertools

import qubesadmin.exc
import qubesadmin.firewall
import qubesadmin.tools


class RuleAction(argparse.Action):
    # pylint: disable=too-few-public-methods
    '''Parser action for a single firewall rule. It accept syntax:
        - <action> [<dsthost> [<proto> [<dstports>|<icmptype>]]]
        - action=<action> [specialtarget=dns] [dsthost=<dsthost>]
          [proto=<proto>] [dstports=<dstports>] [icmptype=<icmptype>]

    Or a mix of them.
    '''
    def __call__(self, _parser, namespace, values, option_string=None):
        if not values:
            setattr(namespace, self.dest, None)
            return
        assumed_order = ['action', 'dsthost', 'proto', 'dstports', 'icmptype']
        allowed_opts = assumed_order + ['specialtarget', 'comment']
        kwargs = {}
        for opt in values:
            opt_elements = opt.split('=')
            if len(opt_elements) == 2:
                key, value = opt_elements
            elif len(opt_elements) == 1:
                key, value = assumed_order[0], opt
            else:
                raise argparse.ArgumentError(None,
                    'invalid rule description: {}'.format(opt))
            if key not in allowed_opts:
                raise argparse.ArgumentError(None,
                    'Invalid rule element: {}'.format(opt))
            kwargs[key] = value
            if key in assumed_order:
                assumed_order.remove(key)
            if key == 'proto' and value in ['tcp', 'udp']:
                assumed_order.remove('icmptype')
            elif key == 'proto' and value in ['icmp']:
                assumed_order.remove('dstports')
        rule = qubesadmin.firewall.Rule(None, **kwargs)
        setattr(namespace, self.dest, rule)

parser = qubesadmin.tools.QubesArgumentParser(vmname_nargs=1)

action = parser.add_subparsers(dest='command', help='action to perform')

action_add = action.add_parser('add', help='add rule')
action_add.add_argument('--before', type=int, default=None,
    help='Add rule before rule with given number, instead of at the end')
action_add.add_argument('rule', nargs='+', action=RuleAction,
    help='rule description')

action_del = action.add_parser('del', help='remove rule')
action_del.add_argument('--rule-no', dest='rule_no', type=int,
    action='store', help='rule number')
action_del.add_argument('rule', nargs='*', action=RuleAction,
    help='rule to be removed')

action_list = action.add_parser('list', help='list rules')

parser.add_argument('--reload', '-r', action='store_true',
    help='force reloading rules even when unchanged')

parser.add_argument('--raw', action='store_true',
    help='output rules as raw strings, instead of nice table')


def rules_list_table(vm):
    '''Print rules to stdout in human-readable form (table)

    :param vm: VM object
    :return: None
    '''
    header = ['NO', 'ACTION', 'HOST', 'PROTOCOL', 'PORT(S)',
        'SPECIAL TARGET', 'ICMP TYPE', 'COMMENT']
    rows = []
    for (rule, rule_no) in zip(vm.firewall.rules, itertools.count()):
        row = [str(x) if x is not None else '-' for x in [
            rule_no,
            rule.action,
            rule.dsthost,
            rule.proto,
            rule.dstports,
            rule.specialtarget,
            rule.icmptype,
            rule.comment,
        ]]
        rows.append(row)
    qubesadmin.tools.print_table([header] + rows)


def rules_list_raw(vm):
    '''Print rules in machine-readable form (as specified in Admin API)

    :param vm: VM object
    :return: None
    '''
    for rule in vm.firewall.rules:
        sys.stdout.write(rule.rule + '\n')


def rules_add(vm, args):
    '''Add a rule defined by args.rule'''
    if args.before is not None:
        vm.firewall.rules.insert(args.before, args.rule)
    else:
        vm.firewall.rules.append(args.rule)
    vm.firewall.save_rules()


def rules_del(vm, args):
    '''Delete a rule according to args.rule/args.rule_no'''
    if args.rule_no is not None:
        vm.firewall.rules.pop(args.rule_no)
    else:
        vm.firewall.rules.remove(args.rule)
    vm.firewall.save_rules()


def main(args=None, app=None):
    '''Main routine of :program:`qvm-firewall`.'''
    try:
        args = parser.parse_args(args, app=app)
        vm = args.domains[0]
        if args.command == 'add':
            rules_add(vm, args)
        elif args.command == 'del':
            rules_del(vm, args)
        elif args.command == 'list':
            if args.raw:
                rules_list_raw(vm)
            else:
                rules_list_table(vm)
            if args.reload:
                vm.firewall.reload()
    except qubesadmin.exc.QubesException as e:
        parser.print_error(str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
