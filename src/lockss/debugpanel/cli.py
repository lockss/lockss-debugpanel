#!/usr/bin/env python3

# Copyright (c) 2000-2023, Board of Trustees of Leland Stanford Jr. University
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import argparse
import base64
import concurrent.futures
import getpass
import os
from pathlib import Path, PurePath
import sys
import traceback
import urllib.error
import urllib.request

import tabulate

import lockss.debugpanel


def _path(purepath_or_string):
    if not issubclass(type(purepath_or_string), PurePath):
        purepath_or_string = Path(purepath_or_string)
    return purepath_or_string.expanduser().resolve()


def _file_lines(path):
    f = None
    try:
        f = open(_path(path), 'r') if path != '-' else sys.stdin
        return [line for line in [line.partition('#')[0].strip() for line in f] if len(line) > 0]
    finally:
        if f is not None and path != '-':
            f.close()


def _do_per_auid(node, auid, action, auth, **kwargs):
    action_encoded = action.replace(" ", "%20")
    auid_encoded = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
    req = _make_request(node, f'action={action_encoded}&auid={auid_encoded}', auth, **kwargs)
    _execute_request(req)
    return True


def _do_per_node(node, action, auth):
    action_encoded = action.replace(" ", "%20")
    req = _make_request(node, f'action={action_encoded}', auth)
    _execute_request(req)
    return True


def _execute_request(req):
    try:
        return urllib.request.urlopen(req)
    except Exception as exc:
        raise Exception(exc).with_traceback(exc.__traceback__)


def _make_request(node, query, auth, **kwargs):
    for k, v in kwargs.items():
        query = f'{query}&{k}={v}'
    url = f'http://{node}/DebugPanel?{query}'
    req = urllib.request.Request(url, headers={'Authorization': f'Basic {auth}'})
    return req


class DebugPanelCli(object):

    PROG = 'debugpanel'

    DEFAULT_DEPTH = 123

    def __init__(self):
        super().__init__()
        self._args = None
        self._auids = None
        self._auth = None
        self._executor = None
        self._nodes = None
        self._parser = None
        self._subparsers = None

    def run(self):
        self._make_parser()
        self._args = self._parser.parse_args()
        if self._args.debug_cli:
            print(self._args)
        if self._args.fun is None:
            raise RuntimeError('internal error: dispatch is unset')
        if not callable(self._args.fun):
            raise RuntimeError('internal error: dispatch is not callable')
        self._args.fun()

    def _copyright(self):
        print(lockss.debugpanel.__copyright__)

    def _get_auids(self):
        if self._auids is None:
            self._auids = list()
            self._auids.extend(self._args.auid)
            for path in self._args.auids:
                self._nodes.extend(_file_lines(path))
            if len(self._auids) == 0:
                self._parser.error('list of AUIDs to process is empty')
        return self._auids

    def _get_nodes(self):
        if self._nodes is None:
            self._nodes = list()
            self._nodes.extend(self._args.remainder)
            self._nodes.extend(self._args.node)
            for path in self._args.nodes:
                self._nodes.extend(_file_lines(path))
            if len(self._nodes) == 0:
                self._parser.error('list of nodes to process is empty')
        return self._nodes

    def _initialize_auth(self):
        u = self._args.username or input('UI username: ')
        p = self._args.password or getpass.getpass('UI password: ')
        self._auth = base64.b64encode(f'{u}:{p}'.encode('utf-8')).decode('utf-8')

    def _initialize_executor(self):
        workers = self._args.pool_size if self._args.pool_size > 0 else None
        if self._args.process_pool:
            self._executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers)
        else:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

    def _license(self):
        print(lockss.debugpanel.__license__)

    def _make_option_debug_cli(self, container):
        container.add_argument('--debug-cli',
                               action='store_true',
                               help='print the result of parsing command line arguments')

    def _make_option_depth(self, container):
        container.add_argument('--depth', '-d',
                               type=int,
                               default=DebugPanelCli.DEFAULT_DEPTH,
                               help='depth of deep crawls (default: %(default)s)')

    def _make_option_verbose(self, container):
        container.add_argument('--verbose', '-v',
                               action='store_true',
                               help='print verbose output')

    def _make_options_auids(self, container):
        group = container.add_argument_group(title='AUID options')
        group.add_argument('--auid', '-a',
                           metavar='AUID',
                           action='append',
                           default=list(),
                           help='add %(metavar)s to the list of AUIDs to process')
        group.add_argument('--auids', '-A',
                           metavar='FILE',
                           action='append',
                           default=list(),
                           help='add the AUIDs in %(metavar)s to the list of AUIDs to process')

    def _make_options_job_pool(self, container):
        group = container.add_argument_group(title='job pool options')
        mutually_exclusive_group = group.add_mutually_exclusive_group()
        group.add_argument('--pool-size',
                           metavar='SIZE',
                           type=int,
                           default=os.cpu_count(),
                           help='nonzero size of job pool (default: %(default)s)')
        mutually_exclusive_group.add_argument('--process-pool',
                                              action='store_true',
                                              help='use a process pool')
        mutually_exclusive_group.add_argument('--thread-pool',
                                              action='store_true',
                                              help='use a thread pool (default)')

    def _make_options_nodes(self, container):
        group = container.add_argument_group(title='node arguments and options')
        group.add_argument('remainder',
                           metavar='HOST:PORT',
                           nargs='*',
                           help='node to process')
        group.add_argument('--node', '-n',
                           metavar='HOST:PORT',
                           action='append',
                           default=list(),
                           help='add %(metavar)s to the list of nodes to process')
        group.add_argument('--nodes', '-N',
                           metavar='FILE',
                           action='append',
                           default=list(),
                           help='add the nodes in %(metavar)s to the list of nodes to process')
        group.add_argument('--password', '-p',
                           metavar='PASS',
                           help='UI password (default: interactive prompt)')
        group.add_argument('--username', '-u',
                           metavar='USER',
                           help='UI username (default: interactive prompt)')

    def _make_option_output_format(self, container):
        container.add_argument('--output-format',
                               metavar='FMT',
                               choices=tabulate.tabulate_formats,
                               default='simple',
                               help='set tabular output format to %(metavar)s (default: %(default)s; choices: %(choices)s)')

    def _make_parser(self):
        self._parser = argparse.ArgumentParser(prog=DebugPanelCli.PROG)
        self._subparsers = self._parser.add_subparsers(title='commands',
                                                       description="Add --help to see the command's own help message",
                                                       dest='command',
                                                       required=True,
                                                       # With subparsers, metavar is also used as the heading of the column of subcommands
                                                       metavar='COMMAND',
                                                       # With subparsers, help is used as the heading of the column of subcommand descriptions
                                                       help='DESCRIPTION')
        self._make_option_debug_cli(self._parser)
        self._make_option_verbose(self._parser)
        self._make_parser_check_substance(self._subparsers)
        self._make_parser_copyright(self._subparsers)
        self._make_parser_crawl(self._subparsers)
        self._make_parser_crawl_plugins(self._subparsers)
        self._make_parser_deep_crawl(self._subparsers)
        self._make_parser_disable_indexing(self._subparsers)
        self._make_parser_license(self._subparsers)
        self._make_parser_poll(self._subparsers)
        self._make_parser_reindex_metadata(self._subparsers)
        self._make_parser_reload_config(self._subparsers)
        self._make_parser_usage(self._subparsers)
        self._make_parser_validate_files(self._subparsers)
        self._make_parser_version(self._subparsers)

    def _make_parser_check_substance(self, container):
        self._make_parser_per_auid(container,
                                   'check-substance', ['cs'],
                                   'Cause nodes to check the substance of AUs',
                                   'cause nodes to check the substance of AUs',
                                   lockss.debugpanel.check_substance)

    def _make_parser_copyright(self, container):
        parser = container.add_parser('copyright',
                                      description='Show copyright and exit',
                                      help='show copyright and exit')
        parser.set_defaults(fun=self._copyright)

    def _make_parser_crawl(self, container):
        self._make_parser_per_auid(container,
                                   'crawl', ['cr'],
                                   'Cause nodes to crawl AUs',
                                   'cause nodes to crawl AUs',
                                   lockss.debugpanel.crawl)

    def _make_parser_crawl_plugins(self, container):
        self._make_parser_per_node(container,
                                   'crawl-plugins', ['cp'],
                                   'Cause nodes to crawl plugins',
                                   'cause nodes to crawl plugins',
                                   lockss.debugpanel.crawl_plugins)

    def _make_parser_deep_crawl(self, container):
        parser = self._make_parser_per_auid(container,
                                            'deep-crawl', ['dc'],
                                            'Cause nodes to crawl AUs, with depth',
                                            'cause nodes to crawl AUs, with depth',
                                            lockss.debugpanel.deep_crawl)
        self._make_option_depth(parser)

    def _make_parser_disable_indexing(self, container):
        parser = self._make_parser_per_auid(container,
                                            'disable-indexing', ['di'],
                                            'Cause nodes to disable metadata indexing of AUs',
                                            'cause nodes to disable metadata indexing of AUs',
                                            lockss.debugpanel.disable_indexing)

    def _make_parser_license(self, container):
        parser = container.add_parser('license',
                                      description='Show license and exit',
                                      help='show license and exit')
        parser.set_defaults(fun=self._license)

    def _make_parser_per_auid(self, container, option, aliases, description, help, target):
        parser = container.add_parser(option, aliases=aliases,
                                      description=description,
                                      help=help)
        parser.set_defaults(fun=self._per_auid)
        parser.set_defaults(target=target)
        self._make_option_output_format(parser)
        self._make_options_nodes(parser)
        self._make_options_auids(parser)
        self._make_options_job_pool(parser)
        return parser

    def _make_parser_per_node(self, container, option, aliases, description, help, target):
        parser = container.add_parser(option, aliases=aliases,
                                      description=description,
                                      help=help)
        parser.set_defaults(fun=self._per_host)
        parser.set_defaults(target=target)
        self._make_option_output_format(parser)
        self._make_options_nodes(parser)
        self._make_options_job_pool(parser)

    def _make_parser_poll(self, container):
        self._make_parser_per_auid(container,
                                   'poll', ['po'],
                                   'Cause nodes to poll AUs',
                                   'cause nodes to poll AUs',
                                   lockss.debugpanel.poll)

    def _make_parser_reindex_metadata(self, container):
        parser = self._make_parser_per_auid(container,
                                            'reindex-metadata', ['ri'],
                                            'Cause nodes to reindex the metadata of AUs',
                                            'cause nodes to reindex the metadata of AUs',
                                            lockss.debugpanel.reindex_metadata)

    def _make_parser_reload_config(self, container):
        self._make_parser_per_node(container,
                                   'reload-config', ['rc'],
                                   'Cause nodes to reload their configuration',
                                   'cause nodes to reload their configuration',
                                   lockss.debugpanel.reload_config)

    def _make_parser_usage(self, container):
        parser = container.add_parser('usage',
                                      description='Show detailed usage and exit',
                                      help='show detailed usage and exit')
        parser.set_defaults(fun=self._usage)

    def _make_parser_validate_files(self, container):
        self._make_parser_per_auid(container,
                                   'validate-files', ['vf'],
                                   'Cause nodes to run file validation on AUs',
                                   'Cause nodes to run file validation on AUs',
                                   lockss.debugpanel.validate_files)

    def _make_parser_version(self, container):
        parser = container.add_parser('version',
                                      description='Show version and exit',
                                      help='show version and exit')
        parser.set_defaults(fun=self._version)

    def _per_auid(self):
        self._initialize_auth()
        self._initialize_executor()
        if self._args.command in ['check-substance', 'cs']:
            action, kw = 'Check Substance', {}
        elif self._args.command in ['crawl', 'cr']:
            action, kw = 'Force Start Crawl', {}
        elif self._args.command in ['deep-crawl', 'dc']:
            action, kw = 'Force Deep Crawl', {'depth': self._args.depth}
        elif self._args.command in ['disable-indexing', 'di']:
            action, kw = 'Disable Indexing', {}
        elif self._args.command in ['poll', 'po']:
            action, kw = 'Start V3 Poll', {}
        elif self._args.command in ['reindex-metadata', 'ri']:
            action, kw = 'Force Reindex Metadata', {}
        elif self._args.command in ['validate-files', 'vf']:
            action, kw = 'Validate Files', {}
        else:
            raise RuntimeError(f'internal error: unknown command: {self._args.command}')
        futures = {self._executor.submit(_do_per_auid, node, auid, action, self._auth, **kw): (node, auid) for auid in self._get_auids() for node in self._get_nodes()}
        results = {}
        for future in concurrent.futures.as_completed(futures):
            k = futures[future]
            try:
                result = future.result() # Just returns True
                results[k] = 'Requested'
            except Exception as exc:
                if self._args.verbose:
                    traceback.print_exc()
                results[k] = exc
        # Output
        print(tabulate.tabulate([[auid] + [results[(node, auid)] for node in self._get_nodes()] for auid in self._get_auids()],
                                headers=[action] + self._get_nodes(),
                                tablefmt=self._args.output_format))

    def _per_host(self):
        self._initialize_auth()
        self._initialize_executor()
        if self._args.command in ['crawl-plugins', 'cp']:
            action = 'Crawl Plugins'
        elif self._args.command in ['reload-config', 'rc']:
            action = 'Reload Config'
        else:
            raise RuntimeError(f'internal error: unknown command: {self._args.command}')
        futures = {self._executor.submit(_do_per_node, node, action, self._auth): node for node in self._get_nodes()}
        results = {}
        for future in concurrent.futures.as_completed(futures):
            k = futures[future]
            try:
                result = future.result() # Just returns True
                results[k] = 'Requested'
            except Exception as exc:
                if self._args.verbose:
                    traceback.print_exc()
                results[k] = exc
        # Output
        print(tabulate.tabulate([[node, results[node]] for node in self._get_nodes()],
                                headers=['Node', action],
                                tablefmt=self._args.output_format))

    def _usage(self):
        self._parser.print_usage()
        print()
        uniq = set()
        for cmd, par in self._subparsers.choices.items():
            if par not in uniq:
                uniq.add(par)
                for s in par.format_usage().split('\n'):
                    usage = 'usage: '
                    print(f'{" " * len(usage)}{s[len(usage):]}' if s.startswith(usage) else s)

    def _version(self):
        print(lockss.debugpanel.__version__)


def main():
    DebugPanelCli().run()
