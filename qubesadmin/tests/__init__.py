# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
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
# with this program; if not, see <http://www.gnu.org/licenses/>.
import subprocess
import traceback
import unittest

import io
from typing import Union, Mapping, Tuple

import qubesadmin
import qubesadmin.app


class TestVM(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.klass = 'TestVM'
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_power_state(self):
        return getattr(self, 'power_state', 'Running')

    def is_networked(self):
        return bool(getattr(self, 'netvm', False))

    def __str__(self):
        return self.name

    def __lt__(self, other):
        if isinstance(other, TestVM):
            return self.name < other.name
        return NotImplemented


class TestVMCollection(dict):
    def __iter__(self):
        return iter(self.values())

    get_blind = dict.get


class TestProcess(object):
    def __init__(self, input_callback=None, stdout=None, stderr=None, stdout_data=None):
        self.input_callback = input_callback
        self.got_any_input = False
        self.stdin = io.BytesIO()
        # don't let anyone close it, before we get the value
        self.stdin_close = self.stdin.close
        self.stdin.close = self.store_input
        self.stdin.flush = self.store_input
        if stdout == subprocess.PIPE or stdout == subprocess.DEVNULL \
                or stdout is None:
            self.stdout = io.BytesIO()
        else:
            self.stdout = stdout
        if stderr == subprocess.PIPE or stderr == subprocess.DEVNULL \
                or stderr is None:
            self.stderr = io.BytesIO()
        else:
            self.stderr = stderr
        if stdout_data:
            self.stdout.write(stdout_data)
            # Seek to head so that it can be read later
            try:
                self.stdout.seek(0)
            except io.UnsupportedOperation:
                # this can happen if (say) stdout is a pipe
                pass
        self.returncode = 0

    def store_input(self):
        value = self.stdin.getvalue()
        if (not self.got_any_input or value) and self.input_callback:
            self.input_callback(self.stdin.getvalue())
        self.got_any_input = True
        self.stdin.truncate(0)

    def communicate(self, input=None):
        if input is not None:
            self.stdin.write(input)
        self.stdin.close()
        self.stdin_close()
        return self.stdout.read(), self.stderr.read()

    def wait(self):
        self.stdin_close()
        return 0

    def poll(self):
        return self.returncode


class _AssertNotRaisesContext(object):
    """A context manager used to implement TestCase.assertNotRaises methods.

    Stolen from unittest and hacked. Regexp support stripped.
    """ # pylint: disable=too-few-public-methods

    def __init__(self, expected, test_case, expected_regexp=None):
        if expected_regexp is not None:
            raise NotImplementedError('expected_regexp is unsupported')

        self.expected = expected
        self.exception = None

        self.failureException = test_case.failureException

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            return True

        if issubclass(exc_type, self.expected):
            raise self.failureException(
                "{!r} raised, traceback:\n{!s}".format(
                    exc_value, ''.join(traceback.format_tb(tb))))
        else:
            # pass through
            return False


default_vm_properties = {
    "autostart": ("bool", True, "False"),
    "backup_timestamp": ("int", True, ""),
    "debug": ("bool", True, "False"),
    "default_user": ("str", True, "user"),
    "dns": ("str", True, "10.139.1.1 10.139.1.2"),
    "gateway": ("str", True, ""),
    "gateway6": ("str", True, ""),
    "icon": ("str", True, "appvm-green"),
    "include_in_backups": ("bool", True, "True"),
    "installed_by_rpm": ("bool", True, "False"),
    "ip": ("str", True, "10.137.0.2"),
    "ip6": ("str", True, ""),
    "kernel": ("str", True, "5.15.52-1.fc32"),
    "keyboard_layout": ("str", True, "us++"),
    "klass": ("str", True, "AppVM"),
    "label": ("label", False, "green"),
    "mac": ("str", True, "00:16:3e:5e:6c:00"),
    "maxmem": ("int", True, "4000"),
    "memory": ("int", True, "400"),
    "name": ("str", False, "testvm"),
    "provides_network": ("bool", True, "False"),
    "qid": ("int", False, "2"),
    "qrexec_timeout": ("int", True, "60"),
    "shutdown_timeout": ("int", True, "60"),
    "start_time": ("str", True, ""),
    "stubdom_mem": ("int", True, ""),
    "stubdom_xid": ("str", True, "-1"),
    "template_for_dispvms": ("bool", True, "False"),
    "updateable": ("bool", True, "False"),
    "uuid": ("str", False, "8fd73e95-a74b-4bf0-a87d-9978dbd1d8a4"),
    "vcpus": ("int", True, "2"),
    "virt_mode": ("str", True, "pvh"),
    "visible_gateway": ("str", True, "10.137.0.1"),
    "visible_gateway6": ("str", True, ""),
    "visible_ip": ("str", True, "10.137.0.2"),
    "visible_ip6": ("str", True, ""),
    "visible_netmask": ("str", True, "255.255.255.255"),
    "xid": ("str", True, "2"),
    "audiovm": ("vm", True, "dom0"),
    "default_dispvm": ("vm", False, "default-dvm"),
    "guivm": ("vm", True, "dom0"),
    "kernelopts": ("str", True, ""),
    "management_dispvm": ("vm", True, "default-mgmt-dvm"),
    "netvm": ("vm", False, "sys-firewall"),
    "template": ("vm", False, "fedora-36"),
}


class QubesTest(qubesadmin.app.QubesBase):
    expected_service_calls = None
    expected_calls = None
    actual_calls = None
    service_calls = None

    def __init__(self):
        super(QubesTest, self).__init__()
        #: expected Admin API calls and saved replies for them
        self.expected_calls = {}
        #: expected qrexec service calls and saved replies for them
        self.expected_service_calls = {}
        #: actual calls made
        self.actual_calls = []
        #: rpc service calls
        self.service_calls = []

    def add_expected_vm(self,
                        name: str,
                        klass: str,
                        properties: Mapping[str,
                                            Union[bool,
                                                  str,
                                                  int,
                                                  Tuple[str, bool, str]]],
                        features,
                        tags):
        """Generate expected_calls entries to get info about a VM

        :param name: name of the VM
        :param klass: class of the VM (AppVM, TemplateVM etc)
        :param properties: dict of properties; values can be either a value
            directly, or tuple of (type, is_default, value)
        :param features: dict of expected features - use 'None' as value for
            feature that will be checked but is not present
        :param tags: list of tags
        :return:
        """
        vm_list_call = ('dom0', 'admin.vm.List', None, None)
        vm_list = b'0\x00'
        if vm_list_call in self.expected_calls:
            vm_list = self.expected_calls[vm_list_call]
        vm_list += f'{name} class={klass} state=Halted\n'.encode()
        self.expected_calls[vm_list_call] = vm_list
        properties_getall = b"0\x00"
        combined_properties = default_vm_properties.copy()
        for prop, value in properties.items():
            if isinstance(value, tuple):
                combined_properties[prop] = value
            elif value is None:
                try:
                    del combined_properties[prop]
                except KeyError:
                    pass
            elif prop in combined_properties:
                combined_properties[prop][2] = str(value)
            else:
                raise KeyError(f"Unknown property '{prop}'")

        if klass in ("TemplateVM", "StandaloneVM"):
            del combined_properties["template"]

        for prop, value in combined_properties.items():
            prop_line = f"{prop} default={value[1]} type={value[0]} {value[2]}"
            properties_getall += (prop_line + "\n").encode()
            self.expected_calls[(name, "admin.vm.property.Get", prop, None)] = \
                b"0\x00" + prop_line.encode()

        self.expected_calls[(name, "admin.vm.feature.List", None, None)] = \
            ("0\x00" + "".join(f"{feature}\n" for feature in features)).encode()
        for feature, value in features:
            self.expected_calls[(name, "admin.vm.feature.Get", feature, None)] = \
                b"0\x00" + value.encode()

        self.expected_calls[(name, "admin.vm.tag.List", None, None)] = \
            ("0\x00" + "".join(f"{tag}\n" for tag in tags)).encode()
        for tag in tags:
            self.expected_calls[(name, "admin.vm.tag.Get", tag, None)] = \
                b"0\x001"

    def qubesd_call(self, dest, method, arg=None, payload=None,
            payload_stream=None):
        if payload_stream:
            payload = (payload or b'') + payload_stream.read()
        call_key = (dest, method, arg, payload)
        self.actual_calls.append(call_key)
        if call_key not in self.expected_calls:
            raise AssertionError('Unexpected call {!r}'.format(call_key))
        return_data = self.expected_calls[call_key]
        if isinstance(return_data, list):
            try:
                return_data = return_data.pop(0)
            except IndexError:
                raise AssertionError('Extra call {!r}'.format(call_key))
        return self._parse_qubesd_response(return_data)

    def run_service(self, dest, service, **kwargs):
        self.service_calls.append((dest, service, kwargs))
        call_key = (dest, service)
        # TODO: consider it as a future extension, as a replacement for
        #  checking app.service_calls later
        # if call_key not in self.expected_service_calls:
        #     raise AssertionError('Unexpected service call {!r}'.format(call_key))
        if call_key in self.expected_service_calls:
            kwargs = kwargs.copy()
            kwargs['stdout_data'] = self.expected_service_calls[call_key]
        return TestProcess(lambda input: self.service_calls.append((dest,
            service, input)),
            stdout=kwargs.get('stdout', None),
            stderr=kwargs.get('stderr', None),
            stdout_data=kwargs.get('stdout_data', None),
        )


class QubesTestCase(unittest.TestCase):
    def setUp(self):
        super(QubesTestCase, self).setUp()
        self.app = QubesTest()

    def assertAllCalled(self):
        self.assertEqual(
            set(self.app.expected_calls.keys()),
            set(self.app.actual_calls))
        # and also check if calls expected multiple times were called
        self.assertFalse([(call, ret)
            for call, ret in self.app.expected_calls.items() if
            isinstance(ret, list) and ret],
            'Some calls not called expected number of times')

    def assertNotRaises(self, excClass, callableObj=None, *args, **kwargs):
        """Fail if an exception of class excClass is raised
           by callableObj when invoked with arguments args and keyword
           arguments kwargs. If a different type of exception is
           raised, it will not be caught, and the test case will be
           deemed to have suffered an error, exactly as for an
           unexpected exception.

           If called with callableObj omitted or None, will return a
           context object used like this::

                with self.assertRaises(SomeException):
                    do_something()

           The context manager keeps a reference to the exception as
           the 'exception' attribute. This allows you to inspect the
           exception after the assertion::

               with self.assertRaises(SomeException) as cm:
                   do_something()
               the_exception = cm.exception
               self.assertEqual(the_exception.error_code, 3)
        """
        context = _AssertNotRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)
