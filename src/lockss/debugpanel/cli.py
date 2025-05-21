#!/usr/bin/env python3

# Copyright (c) 2000-2025, Board of Trustees of Leland Stanford Jr. University
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
from collections.abc import Callable
import concurrent.futures
from getpass import getpass
import os
from pathlib import Path, PurePath
import sys
import traceback
from typing import Any, List, Literal, Optional
import urllib.error
import urllib.request

from pydantic.v1 import BaseModel, Field, FilePath, root_validator, validator
from pydantic.v1.types import PositiveInt
from pydantic_argparse import ArgumentParser
#import rich_argparse
#import tabulate

#from lockss.pybasic.cliutil import CopyrightCommand, LicenseCommand, VersionCommand, at_most_one
from .cliutil import BaseCli, Command, CopyrightCommand, LicenseCommand, StringCommand, VersionCommand, at_most_one
from lockss.pybasic.fileutil import file_lines, path
from lockss.debugpanel import __copyright__, __license__, __version__
from .app import DebugPanelApp, JobPool


def _do_per_auid(node_object, auid, target, **kwargs):
    pickled = bool(kwargs.get('pickled'))
    if pickled:
        try:
            ret = target(node_object, auid)
            return (ret.status, ret.reason)
        except Exception as exc:
            raise Exception(str(exc)).with_traceback(exc.__traceback__)
    else:
        ret = target(node_object)
        return (ret.status, ret)


def _do_per_node(node_object, target, **kwargs):
    pickled = bool(kwargs.get('pickled'))
    if pickled:
        try:
            ret = target(node_object)
            return (ret.status, ret.reason)
        except Exception as exc:
            raise Exception(str(exc)).with_traceback(exc.__traceback__)
    else:
        ret = target(node_object)
        return (ret.status, ret)


class JobPoolModel(BaseModel):
    pool_size: Optional[PositiveInt] = Field(description='[job pool] set the job pool size')
    process_pool: Optional[bool] = Field(False, description='[job pool] use a process pool')
    thread_pool: Optional[bool] = Field(False, description='[job pool] use a thread pool')

    @root_validator
    def at_most_one_pool_type(cls, values):
        return at_most_one(values, 'process_pool', 'thread_pool')

    def get_pool_type(self) -> JobPool:
        field_names = JobPoolModel.__fields__.keys()
        for field_name in field_names:
            field_value = getattr(self, field_name)
            if issubclass(type(field_value), bool) and field_value:
                return JobPool.from_member(field_name)
        return DebugPanelApp.DEFAULT_POOL_TYPE


class NodesModel(JobPoolModel):
    node: Optional[List[str]] = Field([], aliases=['-n'], description='[nodes] add one or more nodes to the list of nodes to process')
    nodes: Optional[List[FilePath]] = Field([], aliases=['-N'], description='[nodes] add the nodes in one or more files to the list of nodes to process')
    password: Optional[str] = Field(aliases=['-p'], description='[nodes] UI password; default behavior: interactive prompt')
    username: Optional[str] = Field(aliases=['-u'], description='[nodes] UI username; default behavior: interactive prompt')

    @validator('nodes', each_item=True, pre=True)
    def _expand_each_nodes_path(cls, v: Path):
        return path(v)

    def get_nodes(self):
        ret = self.node[:]
        for file_path in self.nodes:
            ret.extend(file_lines(file_path))
        return ret

class AuidsModel(NodesModel):
    auid: Optional[List[str]] = Field([], aliases=['-a'], description='[AUIDs] add one or more AUIDs to the list of AUIDs to process')
    auids: Optional[List[FilePath]] = Field([], aliases=['-A'], description='[AUIDs] add the AUIDs in one or more files to the list of AUIDs to process')

    @validator('auids', each_item=True, pre=True)
    def _expand_each_auids_path(cls, v: Path):
        return path(v)

    def get_auids(self):
        ret = self.auid[:]
        for file_path in self.auids:
            ret.extend(file_lines(file_path))
        return ret


class CrawlPluginsModel(NodesModel):
    pass


class ReloadConfigModel(NodesModel):
    pass


class DebugPanelModel(BaseModel):
    debug_cli: Optional[bool] = Field(False, description='print the result of parsing command line arguments')
    # verbose: bool = Field(description='print the result of parsing command line arguments')
    copyright: Optional[CopyrightCommand.type(__copyright__)] = CopyrightCommand.field()
    cp: Optional[CrawlPluginsModel] = Field(description='synonym for: crawl-plugins')
    crawl_plugins: Optional[CrawlPluginsModel] = Field(description='cause nodes to crawl plugins', alias='crawl-plugins')
    license: Optional[LicenseCommand.type(__license__)] = LicenseCommand.field()
    rc: Optional[ReloadConfigModel] = Field(description='synonym for: reload-config')
    reload_config: Optional[ReloadConfigModel] = Field(description='cause nodes to reload their configuration', alias='reload-config')
    version: Optional[VersionCommand.type(__version__)] = VersionCommand.field()


class DebugPanelCli(DebugPanelApp, BaseCli[DebugPanelModel]):

    def __init__(self):
        DebugPanelApp.__init__(self)
        BaseCli.__init__(self,
                         model=DebugPanelModel,
                         prog='debugpanel',
                         description='Tool to interact with the LOCKSS 1.x DebugPanel servlet')

    def _cp(self, crawl_plugins_model: CrawlPluginsModel) -> None:
        self._crawl_plugins(crawl_plugins_model)

    def _crawl_plugins(self, crawl_plugins_model: CrawlPluginsModel) -> None:
        self._do_nodes_command(crawl_plugins_model, self.crawl_plugins)

    def _copyright(self, copyright_model: StringCommand) -> None:
        self._do_string_command(copyright_model)

    def _license(self, license_model: StringCommand) -> None:
        self._do_string_command(license_model)

    def _version(self, version_model: StringCommand) -> None:
        self._do_string_command(version_model)

    # def run(self):
    #     parser : ArgumentParser = ArgumentParser(model=DebugPanelModel,
    #                                              prog='debugpanel',
    #                                              description='Tool to interact with the LOCKSS 1.x DebugPanel servlet')
    #     self.args = parser.parse_typed_args()
    #     print(DebugPanelModel.__fields__.keys())
    #     if self.args.debug_cli:
    #         print(self.args)
    #     if self.args.copyright:
    #         self.args.copyright.print()
    #     if self.args.license:
    #         self.args.license.print()
    #     if self.args.version:
    #         self.args.version.print()
    #     self._initialize_auth()
    #     if (crawl_plugins := self.args.cp or self.args.crawl_plugins):
    #         self.add_nodes(crawl_plugins.get_nodes())
    #         self.crawl_plugins()
    #     elif (reload_config := self.args.rc or self.args.reload_config):
    #         self.add_nodes(reload_config.get_nodes())
    #         self.reload_config()

    def _do_auids_command(self, auids_model: AuidsModel, func: Callable) -> None:
        self.add_auids(*auids_model.get_auids())
        self._do_nodes_command(auids_model, func)

    def _do_nodes_command(self, nodes_model: NodesModel, func: Callable) -> None:
        self.add_nodes(*nodes_model.get_nodes())
        self._initialize_auth(nodes_model)
        self.set_pool_type(nodes_model.get_pool_type()) #FIXME
        func()

    def _do_string_command(self, string_command: StringCommand) -> None:
        string_command.action()

    def _initialize_auth(self, nodes_model):
        _u = nodes_model.username or input('UI username: ')
        _p = nodes_model.password or getpass('UI password: ')
        self._auth = (_u, _p)


def main():
    DebugPanelCli().run()


################### FIXME ####################

'''

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
            for path in self._args._auids:
                self._auids.extend(_file_lines(path))
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
        _u = self._args.username or input('UI username: ')
        _p = self._args.password or getpass.getpass('UI password: ')
        self._auth = (_u, _p)

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

    def _make_option_output_format(self, container):
        container.add_argument('--output-format',
                               metavar='FMT',
                               choices=tabulate.tabulate_formats,
                               default='simple',
                               help='set tabular output format to %(metavar)s (default: %(default)s; choices: %(choices)s)')

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

    def _make_parser(self):
        for cls in [rich_argparse.RichHelpFormatter]:
            cls.styles.update({
                'argparse.args': f'bold {cls.styles["argparse.args"]}',
                'argparse.groups': f'bold {cls.styles["argparse.groups"]}',
                'argparse.metavar': f'bold {cls.styles["argparse.metavar"]}',
                'argparse.prog': f'bold {cls.styles["argparse.prog"]}',
            })
        self._parser = argparse.ArgumentParser(prog=DebugPanelCli.PROG,
                                               formatter_class=rich_argparse.RichHelpFormatter)
        self._subparsers = self._parser.add_subparsers(title='commands',
                                                       description="Add --help to see the command's own help message.",
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
                                   'Cause nodes to check the substance of AUs.',
                                   'cause nodes to check the substance of AUs',
                                   lockss.debugpanel.check_substance)

    def _make_parser_copyright(self, container):
        parser = container.add_parser('copyright',
                                      description='Show copyright and exit.',
                                      help='show copyright and exit',
                                      formatter_class=self._parser.formatter_class)
        parser.set_defaults(fun=self._copyright)

    def _make_parser_crawl(self, container):
        self._make_parser_per_auid(container,
                                   'crawl', ['cr'],
                                   'Cause nodes to crawl AUs.',
                                   'cause nodes to crawl AUs',
                                   lockss.debugpanel.crawl)

    def _make_parser_crawl_plugins(self, container):
        self._make_parser_per_node(container,
                                   'crawl-plugins', ['cp'],
                                   'Cause nodes to crawl plugins.',
                                   'cause nodes to crawl plugins',
                                   lockss.debugpanel.crawl_plugins)

    def _make_parser_deep_crawl(self, container):
        parser = self._make_parser_per_auid(container,
                                            'deep-crawl', ['dc'],
                                            'Cause nodes to crawl AUs, with depth.',
                                            'cause nodes to crawl AUs, with depth',
                                            lockss.debugpanel.deep_crawl)
        self._make_option_depth(parser)

    def _make_parser_disable_indexing(self, container):
        parser = self._make_parser_per_auid(container,
                                            'disable-indexing', ['di'],
                                            'Cause nodes to disable metadata indexing of AUs.',
                                            'cause nodes to disable metadata indexing of AUs',
                                            lockss.debugpanel.disable_indexing)

    def _make_parser_license(self, container):
        parser = container.add_parser('license',
                                      description='Show license and exit.',
                                      help='show license and exit',
                                      formatter_class=self._parser.formatter_class)
        parser.set_defaults(fun=self._license)

    def _make_parser_per_auid(self, container, option, aliases, description, help, target):
        parser = container.add_parser(option, aliases=aliases,
                                      description=description,
                                      help=help,
                                      formatter_class=self._parser.formatter_class)
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
                                      help=help,
                                      formatter_class=self._parser.formatter_class)
        parser.set_defaults(fun=self._per_node)
        parser.set_defaults(target=target)
        self._make_option_output_format(parser)
        self._make_options_nodes(parser)
        self._make_options_job_pool(parser)

    def _make_parser_poll(self, container):
        self._make_parser_per_auid(container,
                                   'poll', ['po'],
                                   'Cause nodes to poll AUs.',
                                   'cause nodes to poll AUs',
                                   lockss.debugpanel.poll)

    def _make_parser_reindex_metadata(self, container):
        parser = self._make_parser_per_auid(container,
                                            'reindex-metadata', ['ri'],
                                            'Cause nodes to reindex the metadata of AUs.',
                                            'cause nodes to reindex the metadata of AUs',
                                            lockss.debugpanel.reindex_metadata)

    def _make_parser_reload_config(self, container):
        self._make_parser_per_node(container,
                                   'reload-config', ['rc'],
                                   'Cause nodes to reload their configuration.',
                                   'cause nodes to reload their configuration',
                                   lockss.debugpanel.reload_config)

    def _make_parser_usage(self, container):
        parser = container.add_parser('usage',
                                      description='Show detailed usage and exit.',
                                      help='show detailed usage and exit',
                                      formatter_class=self._parser.formatter_class)
        parser.set_defaults(fun=self._usage)

    def _make_parser_validate_files(self, container):
        self._make_parser_per_auid(container,
                                   'validate-files', ['vf'],
                                   'Cause nodes to run file validation on AUs.',
                                   'cause nodes to run file validation on AUs',
                                   lockss.debugpanel.validate_files)

    def _make_parser_version(self, container):
        parser = container.add_parser('version',
                                      description='Show version and exit.',
                                      help='show version and exit',
                                      formatter_class=self._parser.formatter_class)
        parser.set_defaults(fun=self._version)

    def _per_auid(self):
        self._initialize_auth()
        self._initialize_executor()
        node_objects = [lockss.debugpanel.node(node, *self._auth) for node in self._get_nodes()]
        futures = {self._executor.submit(_do_per_auid, node_object, auid, self._args.target, pickled=True): (node, auid) for auid in self._get_auids() for node, node_object in zip(self._get_nodes(), node_objects)}
        results = {}
        for future in concurrent.futures.as_completed(futures):
            k = futures[future]
            try:
                status, reason = future.result()
                results[k] = 'Requested' if status == 200 else reason
            except Exception as exc:
                if self._args.verbose:
                    traceback.print_exc()
                results[k] = exc
        # Output
        print(tabulate.tabulate([[auid] + [results[(node, auid)] for node in self._get_nodes()] for auid in self._get_auids()],
                                headers=['AUID'] + self._get_nodes(),
                                tablefmt=self._args.output_format))

    def _per_node(self):
        self._initialize_auth()
        self._initialize_executor()
        node_objects = [lockss.debugpanel.node(node, *self._auth) for node in self._get_nodes()]
        futures = {self._executor.submit(_do_per_node, node_object, self._args.target, pickled=True): node for node, node_object in zip(self._get_nodes(), node_objects)}
        results = {}
        for future in concurrent.futures.as_completed(futures):
            k = futures[future]
            try:
                status, reason = future.result()
                results[k] = 'Requested' if status == 200 else reason
            except Exception as exc:
                if self._args.verbose:
                    traceback.print_exc()
                results[k] = exc
        # Output
        print(tabulate.tabulate([[node, results[node]] for node in self._get_nodes()],
                                headers=['Node', 'Result'],
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

'''