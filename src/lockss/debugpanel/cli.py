#!/usr/bin/env python3

# Copyright (c) 2000-2026, Board of Trustees of Leland Stanford Jr. University
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

from collections.abc import Callable, Iterator
from concurrent.futures import Executor, Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum
from inspect import ismethod
from itertools import chain
from pathlib import Path
from typing import Any, Optional

from click_extra import ChoiceSource, EnumChoice, ExtraContext, Section, TableFormat, color_option, echo, group, option, option_group, pass_context, pass_obj, print_table, progressbar, prompt, show_params_option
from cloup.constraints import mutually_exclusive

from lockss.pybasic.cliutil import NonNegativeInt, click_path, compose_decorators, make_extra_context_settings, make_table_format_option
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines
from . import Node, RequestUrlOpenT, check_substance, crawl, crawl_plugins, deep_crawl, disable_indexing, poll, reload_config, reindex_metadata, validate_files, DEFAULT_DEPTH, __copyright__, __license__, __version__


class _JobPoolType(Enum):
    """An enum of job pool types."""
    THREAD_POOL = 'thread-pool'
    PROCESS_POOL = 'process-pool'


#: The default ``_JobPoolType``.
_DEFAULT_JOB_POOL_TYPE: _JobPoolType = _JobPoolType.THREAD_POOL


@dataclass(kw_only=True)
class _Opts:
    """Data class to hold parsed command line options."""
    # Node operation
    node: tuple[str, ...] = ()
    nodes: tuple[Path, ...] = ()
    u: Optional[str] = None # DEPRECATED
    username: Optional[str] = None
    p: Optional[str] = field(default=None, repr=False) # DEPRECATED
    password: Optional[str] = field(default=None, repr=False)
    # AUID operation
    auid: tuple[str, ...] = ()
    auids: tuple[Path, ...] = ()
    # Depth
    depth: Optional[int] = None
    # Job pool
    pool_size: Optional[int] = None
    pool_type: Optional[_JobPoolType] = None
    process_pool: bool = False # DEPRECATED
    thread_pool: bool = False # DEPRECATED
    # Output
    headings: Optional[bool] = None
    progress: Optional[bool] = None
    table_format: Optional[TableFormat] = None

    def __post_init__(self):
        """Post-initialization method, to handle deprecated options."""
        if self.u:
            self.username, self.u = self.u, None
        if self.p:
            self.password, self.p = self.p, None
        if self.process_pool:
            self.pool_type, self.process_pool = _JobPoolType.PROCESS_POOL, False
        if self.thread_pool:
            self.pool_type, self.thread_pool = _JobPoolType.THREAD_POOL, False
        if not self.username:
            self.username = prompt('UI username')
        if not self.password:
            self.password = prompt('UI password', hide_input=True, confirmation_prompt=False)
        if not self.pool_type:
            self.pool_type = _DEFAULT_JOB_POOL_TYPE


class _DebugPanelCli(object):
    """DebugPanel command line application."""

    def __init__(self, ctx: ExtraContext):
        """
        Constructor.

        :param ctx: The Click Extra context.
        :type ctx: ExtraContext
        """
        super().__init__()
        self._ctx: ExtraContext = ctx
        self._opts: Optional[_Opts] = None
        self._auids: Optional[list[str]] = None
        self._executor: Optional[Executor] = None
        self._nodes: Optional[list[str]] = None

    def check_substance(self) -> None:
        """Implementation of the ``check-substance`` command."""
        self._do_auid_command(check_substance)

    def crawl(self) -> None:
        """Implementation of the ``crawl`` command."""
        self._do_auid_command(crawl)

    def crawl_plugins(self) -> None:
        """Implementation of the ``crawl-plugins`` command."""
        self._do_node_command(crawl_plugins)

    def deep_crawl(self) -> None:
        """Implementation of the ``deep-crawl`` command."""
        self._do_auid_command(deep_crawl, depth=self._opts.depth)

    def disable_indexing(self) -> None:
        """Implementation of the ``disable-indexing`` command."""
        self._do_auid_command(disable_indexing)

    def dispatch(self, method: Callable[[], None], **cli_kwargs) -> None:
        """
        Initializes from the given command line options and invokes the given
        (bound) method.

        :param method: A (bound) method.
        :type method: Callable[[], None]
        :param cli_kwargs: The command line arguments passed by Click Extra.
        :type cli_kwargs: dict[str, Any]
        """
        if not ismethod(method):
            raise InternalError() from ValueError(method)
        self._opts = _Opts(**cli_kwargs)
        method()

    def poll(self) -> None:
        """Implementation of the ``poll`` command."""
        self._do_auid_command(poll)

    def reindex_metadata(self) -> None:
        """Implementation of the ``reindex-metadata`` command."""
        self._do_auid_command(reindex_metadata)

    def reload_config(self) -> None:
        """Implementation of the ``reload-config`` command."""
        self._do_node_command(reload_config)

    def validate_files(self) -> None:
        """Implementation of the ``validate-files`` command."""
        self._do_auid_command(validate_files)

    def _do_auid_command(self,
                         node_auid_func: Callable[[Node, str], RequestUrlOpenT],
                         **kwargs) -> None:
        """
        Performs one AUID-centric command.

        :param node_auid_func: A function that applies to a ``Node`` and an AUID
                               and returns what ``urllib.request.urlopen``
                               returns.
        :type node_auid_func: Callable[[Node, str], RequestUrlOpenT]
        """
        self._initialize_auid_operation()
        opts = self._opts
        node_objects = [Node(node, opts.username, opts.password) for node in self._nodes]
        futures: dict[Future, tuple[str, str]] = {self._executor.submit(node_auid_func, node_object, auid, **kwargs): (node, auid) for auid in self._auids for node, node_object in zip(self._nodes, node_objects)}
        completed: Iterator[Future] = as_completed(futures)
        results: dict[tuple[str, str], Any] = {}
        with progressbar(completed, length=len(futures), label='Progress') if opts.progress else nullcontext(completed) as bar:
            for future in bar:
                node_auid = futures[future]
                try:
                    with future.result() as resp:
                        status: int = resp.status
                        reason: str = resp.reason
                        results[node_auid] = 'Requested' if status == 200 else reason
                except Exception as exc:
                    results[node_auid] = exc
        print_table([[auid, *[results[(node, auid)] for node in self._nodes]] for auid in self._auids],
                    headers=['AUID', *self._nodes] if opts.headings else None,
                    table_format=opts.table_format)

    def _do_node_command(self,
                         node_func: Callable[[Node], RequestUrlOpenT],
                         **kwargs) -> None:
        """
        Performs one node-centric command.

        :param node_func: A function that applies to a ``Node`` and returns
                          what ``urllib.request.urlopen`` returns.
        :type node_func: Callable[[Node], RequestUrlOpenT]
        """
        self._initialize_node_operation()
        opts = self._opts
        node_objects = [Node(node, opts.username, opts.password) for node in self._nodes]
        futures: dict[Future, str] = {self._executor.submit(node_func, node_object, **kwargs): node for node, node_object in zip(self._nodes, node_objects)}
        completed: Iterator[Future] = as_completed(futures)
        results: dict[str, Any] = {}
        with progressbar(completed, length=len(futures), label='Progress') if opts.progress else nullcontext(completed) as bar:
            for future in bar:
                node = futures[future]
                try:
                    with future.result() as resp:
                        status: int = resp.status
                        reason: str = resp.reason
                        results[node] = 'Requested' if status == 200 else reason
                except Exception as exc:
                    results[node] = exc
        print_table([[node, results[node]] for node in self._nodes],
                    headers=['Node', 'Result'] if opts.headings else None,
                    table_format=self._opts.table_format)

    def _initialize_auid_operation(self) -> None:
        """
        Initializes for an AUID-centric operation. Fails if the list of AUIDs
        ends up being empty.
        """
        self._initialize_node_operation()
        self._auids = [*(opts := self._opts).auid, *chain.from_iterable(file_lines(file_path) for file_path in opts.auids)]
        if len(self._auids) == 0:
            self._ctx.fail('The list of AUIDs to process is empty')

    def _initialize_node_operation(self) -> None:
        """
        Initializes for a node-centric operation. Fails if the list of nodes
        ends up being empty.
        """
        self._nodes = [*(opts := self._opts).node, *chain.from_iterable(file_lines(file_path) for file_path in opts.nodes)]
        if len(self._nodes) == 0:
            self._ctx.fail('The list of nodes to process is empty')
        match opts.pool_type:
            case _JobPoolType.PROCESS_POOL:
                self._executor = ProcessPoolExecutor(max_workers=opts.pool_size)
            case _JobPoolType.THREAD_POOL:
                self._executor = ThreadPoolExecutor(max_workers=opts.pool_size)
            case _:
                raise InternalError() from ValueError(opts.pool_type)
        if opts.username is None:
            opts.username = prompt('UI username')
        if opts.password is None:
            opts.password = prompt('UI password', hide_input=True)


#: The AUID option group: --auid/-a, --auids/-A
_auid_option_group = option_group(
    'AUID options',
    option('--auid', '-a', metavar='AUID', multiple=True, help='Add AUID to the list of AUIDs to process.'),
    option('--auids', '-A', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the AUIDs in FILE to the list of AUIDs to process.')
)


#: The depth option group: --depth/-d
_depth_option_group = option_group(
    'Depth options',
    option('--depth', '-d', metavar='DEPTH', type=NonNegativeInt, default=DEFAULT_DEPTH, help='Set the crawl depth to DEPTH.')
)


#: The node option group: --node/-n, --nodes/-N, --username/-U, --password/-P
_node_option_group = option_group(
    'Node options',
    option('--node', '-n', metavar='NODE', multiple=True, help='Add NODE to the list of nodes to process.'),
    option('--nodes', '-N', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the nodes in FILE to the list of nodes to process.'),
    mutually_exclusive(
        # option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.', prompt='UI username'),
        option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.'),
        option('-u', metavar='USER', deprecated='Use -U instead.')
    ),
    mutually_exclusive(
        # password_option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.', prompt='UI password', confirmation_prompt=False),
        option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.'),
        option('-p', metavar='PASS', deprecated='Use -P instead.')
    )
)


#: The output option group: --headings/--no-headings, --progress/--no-progress, --table-format/-T
_output_option_group = option_group(
    'Output options',
    option('--headings/--no-headings', is_flag=True, default=True, help='Set whether to include column headings in tabular output.'),
    option('--progress/--no-progress', is_flag=True, default=True, help='Set whether to display a progress bar during processing.'),
    make_table_format_option()
)


#: The job pool option group: --pool-size, --pool-type
_pool_option_group = option_group(
    'Job pool options',
    option('--pool-size', metavar='SIZE', type=Optional[NonNegativeInt], default=None, help='Set the job pool size to SIZE.', show_default='CPU-dependent'),
    mutually_exclusive(
        # option('--pool-type', type=EnumChoice(choices=_JobPoolType, choice_source=ChoiceSource.VALUE), default=_DEFAULT_JOB_POOL_TYPE, help=f'Set the job pool type to the given type.'),
        option('--pool-type', type=EnumChoice(choices=_JobPoolType, choice_source=ChoiceSource.VALUE), show_default=_DEFAULT_JOB_POOL_TYPE, help=f'Set the job pool type to the given type.'),
        option('--process-pool', is_flag=True, deprecated='Use --pool-type=process-pool instead.'),
        option('--thread-pool', is_flag=True, deprecated='Use --pool-type=thread-pool instead.')
    )
)


#: The composite AUID operation decorator.
_auid_operation = compose_decorators(_node_option_group, _auid_option_group, _pool_option_group, _output_option_group, pass_obj)


#: The composite node operation decorator.
_node_operation = compose_decorators(_node_option_group, _pool_option_group, _output_option_group, pass_obj)


@group('debugpanel', params=None, context_settings=make_extra_context_settings())
@color_option
@show_params_option
@pass_context
def _debugpanel(ctx: ExtraContext, **kwargs):
    """Command line tool to interact with the LOCKSS 1.x DebugPanel servlet."""
    ctx.obj = _DebugPanelCli(ctx)


#: A subcommand section for AUID commands.
_AUID_COMMANDS = Section('AUID commands')


#: A subcommand section for node commands.
_NODE_COMMANDS = Section('Node commands')


@_debugpanel.command('check-substance', aliases=['cs'], section=_AUID_COMMANDS, help='Cause nodes to check the substance of AUs.')
@_auid_operation
def _check_substance(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to check the substance of AUs."""
    cli.dispatch(cli.check_substance, **kwargs)


@_debugpanel.command('copyright', help='Show the copyright and exit.')
def _copyright() -> None:
    """Show the copyright and exit."""
    echo(__copyright__)


@_debugpanel.command('crawl', aliases=['cr'], section=_AUID_COMMANDS, help='Cause nodes to crawl AUs.')
@_auid_operation
def _crawl(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to crawl AUs."""
    cli.dispatch(cli.crawl, **kwargs)


@_debugpanel.command('crawl-plugins', aliases=['cp'], section=_NODE_COMMANDS, help='Cause nodes to crawl plugins.')
@_node_operation
def _crawl_plugins(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to crawl plugins."""
    cli.dispatch(cli.crawl_plugins, **kwargs)


@_debugpanel.command('deep-crawl', aliases=['dc'], section=_AUID_COMMANDS, help='Cause nodes to deep-crawl AUs.')
@compose_decorators(_node_option_group, _auid_option_group, _depth_option_group, _pool_option_group, _output_option_group, pass_obj)
def _deep_crawl(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to deep-crawl AUs."""
    cli.dispatch(cli.deep_crawl, **kwargs)


@_debugpanel.command('disable-indexing', aliases=['di'], section=_AUID_COMMANDS, help='Cause nodes to disable metadata indexing for AUs.')
@_auid_operation
def _disable_indexing(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to disable metadata indexing for AUs."""
    cli.dispatch(cli.disable_indexing, **kwargs)


@_debugpanel.command('license', help='Show the software license and exit.')
def license() -> None:
    """Show the software license and exit."""
    echo(__license__)


@_debugpanel.command('poll', aliases=['po'], section=_AUID_COMMANDS, help='Cause nodes to poll AUs.')
@_auid_operation
def _poll(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to poll AUs."""
    cli.dispatch(cli.poll, **kwargs)


@_debugpanel.command('reload-config', aliases=['rc'], section=_NODE_COMMANDS, help='Cause nodes to reload their configuration.')
@_node_operation
def _reload_config(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to reload their configuration."""
    cli.dispatch(cli.reload_config, **kwargs)


@_debugpanel.command('reindex-metadata', aliases=['ri'], section=_AUID_COMMANDS, help='Cause nodes to reindex the metadata of AUs.')
@_auid_operation
def _reindex_metadata(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to reindex the metadata of AUs."""
    cli.dispatch(cli.reindex_metadata, **kwargs)


@_debugpanel.command('validate-files', aliases=['vf'], section=_AUID_COMMANDS, help='Cause nodes to validate the files of AUs.')
@_auid_operation
def _validate_files(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to validate the files of AUs."""
    cli.dispatch(cli.validate_files, **kwargs)


@_debugpanel.command('version', help='Show the version number and exit.')
def version() -> None:
    """Show the version number and exit."""
    echo(__version__)


def main() -> None:
    """Main entry point of the module."""
    _debugpanel()


# Main entry point of the module.
if __name__ == '__main__':
    main()
