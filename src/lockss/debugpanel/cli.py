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

"""
Command line tool to interact with the LOCKSS 1.x DebugPanel servlet.
"""

from collections.abc import Callable
from concurrent.futures import Executor, Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import Any, Optional

from click_extra import ChoiceSource, EnumChoice, ExtraContext, IntRange, color_option, echo, group, option, option_group, pass_context, pass_obj, password_option, progressbar, show_params_option, table_format_option
from cloup.constraints import mutually_exclusive

from lockss.pybasic.cliutil import click_path, compose_decorators, make_extra_context_settings
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines, path
from . import Node, RequestUrlOpenT, check_substance, crawl, crawl_plugins, deep_crawl, disable_indexing, poll, reload_config, reindex_metadata, validate_files, DEFAULT_DEPTH, __copyright__, __license__, __version__


class _JobPoolType(Enum):
    """
    An enum of job pool types.

    See also ``_DEFAULT_JOB_POOL_TYPE``.
    """
    THREAD_POOL = 'thread-pool'
    PROCESS_POOL = 'process-pool'


_DEFAULT_JOB_POOL_TYPE: _JobPoolType = _JobPoolType.THREAD_POOL


class _DebugPanelCli(object):

    def __init__(self, ctx: ExtraContext):
        super().__init__()
        self._auids: Optional[list[str]] = None
        self._auth: Optional[tuple[str, str]] = None
        self._ctx: ExtraContext = ctx
        self._executor: Optional[Executor] = None
        self._nodes: Optional[list[str]] = None

    def do_auid_command(self,
                        node_auid_func: Callable[[Node, str], RequestUrlOpenT],
                        **kwargs: dict[str, Any]) -> None:
        """
        Performs one AUID-centric command.

        :param node_auid_func: A function that applies to a ``Node`` and an AUID
                               and returns what ``urllib.request.urlopen``
                               returns.
        :type node_auid_func: ``RequestUrlOpenT``
        :param kwargs: Keyword arguments (needed for the ``depth`` command).
        :type kwargs: Dict[str, Any]
        """
        node_objects = [Node(node, *self._auth) for node in self._nodes]
        futures: dict[Future, tuple[str, str]] = {self._executor.submit(node_auid_func, node_object, auid, **kwargs): (node, auid) for auid in self._auids for node, node_object in zip(self._nodes, node_objects)}
        results: dict[tuple[str, str], Any] = {}
        with progressbar(as_completed(futures), length=len(futures), label='Progress') as bar:
            for future in bar:
                with future.result() as resp:
                    node_auid = futures[future]
                    try:
                        status: int = resp.status
                        reason: str = resp.reason
                        results[node_auid] = 'Requested' if status == 200 else reason
                    except Exception as exc:
                        results[node_auid] = exc
        self._ctx.print_table([[auid, *[results[(node, auid)] for node in self._nodes]] for auid in self._auids],
                              ['AUID', *self._nodes])

    def do_node_command(self,
                        node_func: Callable[[Node], RequestUrlOpenT],
                        **kwargs: dict[str, Any]) -> None:
        """
        Performs one node-centric command.

        :param node_func: A function that applies to a ``Node`` and returns
                          what ``urllib.request.urlopen`` returns.
        :type node_auid_func: ``RequestUrlOpenT``
        :param kwargs: Keyword arguments (not currently needed by any command).
        :type kwargs: Dict[str, Any]
        """
        node_objects = [Node(node, *self._auth) for node in self._nodes]
        futures: dict[Future, str] = {self._executor.submit(node_func, node_object, **kwargs): node for node, node_object in zip(self._nodes, node_objects)}
        results: dict[str, Any] = {}
        with progressbar(as_completed(futures), length=len(futures), label='Progress') as bar:
            for future in bar:
                with future.result() as resp:
                    node = futures[future]
                    try:
                        status: int = resp.status
                        reason: str = resp.reason
                        results[node] = 'Requested' if status == 200 else reason
                    except Exception as exc:
                        results[node] = exc
        self._ctx.print_table([[node, results[node]] for node in self._nodes],
                              ['Node', 'Result'])

    def initialize_auid_operation(self,
                                  cli_node: tuple[str, ...],
                                  cli_nodes: tuple[Path, ...],
                                  cli_username: str,
                                  cli_password: str,
                                  cli_auid: tuple[str, ...],
                                  cli_auids: tuple[Path, ...],
                                  cli_pool_size: Optional[int],
                                  cli_pool_type: _JobPoolType,
                                  cli_process_pool: bool,
                                  cli_thread_pool: bool) -> None:
        self.initialize_node_operation(cli_node,
                                       cli_nodes,
                                       cli_username,
                                       cli_password,
                                       cli_pool_size,
                                       cli_pool_type,
                                       cli_process_pool,
                                       cli_thread_pool)
        self._auids = [*cli_auid, *chain.from_iterable(file_lines(file_path) for file_path in cli_auids)]
        if len(self._auids) == 0:
            self._ctx.fail('The list of AUIDs to process is empty')

    def initialize_node_operation(self, cli_node: tuple[str, ...],
                                  cli_nodes: tuple[Path, ...],
                                  cli_username: str,
                                  cli_password: str,
                                  cli_pool_size: Optional[int],
                                  cli_pool_type: _JobPoolType,
                                  cli_process_pool: bool,
                                  cli_thread_pool: bool) -> None:
        self._nodes = [*cli_node, *chain.from_iterable(file_lines(file_path) for file_path in cli_nodes)]
        if len(self._nodes) == 0:
            self._ctx.fail('The list of nodes to process is empty')
        self._auth = (cli_username, cli_password)
        if cli_process_pool:
            cli_pool_type = _JobPoolType.PROCESS_POOL
        elif cli_thread_pool:
            cli_pool_type = _JobPoolType.THREAD_POOL
        match cli_pool_type:
            case _JobPoolType.PROCESS_POOL:
                self._executor = ProcessPoolExecutor(max_workers=cli_pool_size)
            case _JobPoolType.THREAD_POOL:
                self._executor = ThreadPoolExecutor(max_workers=cli_pool_size)
            case _:
                raise InternalError() from ValueError(cli_pool_type)


_node_options = option_group(
    'Node options',
    option('--node', '-n', metavar='NODE', multiple=True, help='Add NODE to the list of nodes to process.'),
    option('--nodes', '-N', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the nodes in FILE to the list of nodes to process.'),
    option('--username', '-u', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.', prompt='UI username'),
    password_option('--password', '-p', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.', prompt='UI password', confirmation_prompt=False)
)


_auid_options = option_group(
    'AUID options',
    option('--auid', '-a', metavar='AUID', multiple=True, help='Add AUID to the list of AUIDs to process.'),
    option('--auids', '-A', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the AUIDs in FILE to the list of AUIDs to process.')
)


_pool_options = option_group(
    'Job pool options',
    option('--pool-size', metavar='SIZE', type=Optional[IntRange(1, None)], default=None, help='Set the job pool size to SIZE.', show_default='CPU-dependent'),
    mutually_exclusive(
        option('--pool-type', type=EnumChoice(choices=_JobPoolType, choice_source=ChoiceSource.VALUE), default=_DEFAULT_JOB_POOL_TYPE, help=f'Set the job pool type to the given type.'),
        option('--process-pool', is_flag=True, deprecated='Use --pool-type=process-pool instead.'),
        option('--thread-pool', is_flag=True, deprecated='Use --pool-type=thread-pool instead.')
    )
)


_table_format_option = table_format_option(help='Set the rendering of tables to the given style.')


_node_operation = compose_decorators(_node_options, pass_obj)


_node_args = ['node', 'nodes', 'username', 'password', 'pool_size', 'pool_type', 'process_pool', 'thread_pool']


_auid_operation = compose_decorators(_node_options, _auid_options, pass_obj)


_auid_args = ['node', 'nodes', 'username', 'password', 'auid', 'auids', 'pool_size', 'pool_type', 'process_pool', 'thread_pool']


@group('debugpanel', params=None, context_settings=make_extra_context_settings())
@_pool_options
@option_group('Output options', color_option, table_format_option)
@show_params_option
@pass_context
def _debugpanel(ctx: ExtraContext, **kwargs):
    ctx.obj = _DebugPanelCli(ctx)


@_debugpanel.command('check-substance', aliases=['cs'], help='Cause nodes to check the substance of AUs.')
@_auid_operation
def _check_substance(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(check_substance)


@_debugpanel.command('copyright', help='Show the copyright then exit.')
def _copyright() -> None:
    echo(__copyright__)


@_debugpanel.command('crawl', aliases=['cr'], help='Cause nodes to crawl AUs.')
@_auid_operation
def _crawl(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(crawl)


@_debugpanel.command('crawl-plugins', aliases=['cp'], help='Cause nodes to crawl plugins.')
@_node_operation
def _crawl_plugins(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_node_operation(*[kwargs.get(k) for k in _node_args])
    cli.do_node_command(crawl_plugins)


@_debugpanel.command('deep-crawl', aliases=['dc'], help='Cause nodes to deep-crawl AUs.')
@compose_decorators(
    _node_options, _auid_options,
    option_group('Depth options',
                 option('--depth', '-d', metavar='DEPTH', type=IntRange(1, None), default=DEFAULT_DEPTH, help='Set the crawl depth to DEPTH.')),
    _pool_options, table_format_option, pass_obj
)
def _deep_crawl(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(deep_crawl, depth=kwargs.get('depth'))


@_debugpanel.command('disable-indexing', aliases=['di'], help='Cause nodes to disable metadata indexing for AUs.')
@_auid_operation
def _disable_indexing(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(disable_indexing)


@_debugpanel.command('license', help='Show the software license then exit.')
def license() -> None:
    echo(__license__)


@_debugpanel.command('poll', aliases=['po'], help='Cause nodes to poll AUs.')
@_auid_operation
def _poll(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(poll)


@_debugpanel.command('reindex-metadata', aliases=['ri'], help='Cause nodes to reindex the metadata of AUs.')
@_auid_operation
def _reindex_metadata(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(reindex_metadata)


@_debugpanel.command('reload-config', aliases=['rc'], help='Cause nodes to reload their configuration.')
@_node_operation
def _reload_config(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_node_operation(*[kwargs.get(k) for k in _node_args])
    cli.do_node_command(reload_config)


@_debugpanel.command('validate-files', aliases=['vf'], help='Cause nodes to validate the files of AUs.')
@_auid_operation
def _validate_files(cli: _DebugPanelCli, **kwargs) -> None:
    cli.initialize_auid_operation(*[kwargs.get(k) for k in _auid_args])
    cli.do_auid_command(validate_files)


@_debugpanel.command('version', help='Show the version number then exit.')
def version() -> None:
    echo(__version__)


def main() -> None:
    _debugpanel()


if __name__ == '__main__':
    main()
