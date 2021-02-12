#!/usr/bin/env python3

'''A script to interact with the LOCKSS daemon's DebugPanel servlet.'''

__copyright__ = '''\
Copyright (c) 2000-2021, Board of Trustees of Leland Stanford Jr. University.
All rights reserved.'''

__license__ = '''\
Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.'''

__version__ = '0.4.1'

__tutorial__ = '''\
TUTORIAL

A list of target hosts is built up by accumulating host:port pairs passed with
--host and host:port pairs read from files passed with --hosts.

If a username is passed with --username, it is used to connect to target hosts,
otherwise an interactive prompt asks for one. Likewise, if a password is passed
with --password, it is used to connect to hosts, otherwise an interactive prompt
asks for one.

Operations that can be applied to each target host include:

  --crawl-plugins
      Causes the daemon to recrawl plugin registries.

  --reload-config
      Causes the daemon to reload its config.

Other operations are applied to specific AUs. A list of target AUIDs is built up
by accumulating those passed via --auid and those read from files passed with
--auids.

Operations that can be applied to each target AU of each target host include:

  --check-substance
      Requests a substance check of the AU.

  --crawl
      Requests a crawl of the AU.

  --deep-crawl
      Requests a deep crawl of the AU. You can specify a custom depth with
      --depth.

  --disable-indexing
      Disables indexing of the metadata of the AU.

  --poll
      Requests a poll of the AU.

  --reindex-metadata
      Requests reindexing of the metadata of the AU.

Up to the number of target hosts passed with --pool-size is processed in
parallel; by default (or if a value of 0 is passed), all the target hosts in
parallel. Each is processed in its own thread by default or if --thread-pool is
specified, or in its own process if --process-pool is specified.

You can specify a number of seconds to wait between requests to each target host
with --wait.

The --debug options causes verbose error messages to be displayed to stderr.

An error causes the program to exit, unless --keep-going is specified, in which
case processing for the offending target host ends prematurely but processing
for the other target hosts continues.
'''

import argparse
import base64
import getpass
from multiprocessing import Pool as ProcessPool
from multiprocessing.dummy import Pool as ThreadPool
import os.path
import sys
from threading import Lock, Thread
import time
import traceback
import urllib.request

_STDERR_LOCK = Lock()

class _DebugPanelOptions(object):

    @staticmethod
    def make_parser():
        # Create parser
        usage = '%(prog)s {OPERATION} {--host=HOST|--hosts=HFILE}... [--auid=AUID|--auids=AFILE]... [OPTIONS]...'
        parser = argparse.ArgumentParser(description=__doc__, usage=usage)
        parser.add_argument('--version', '-V', action='version', version=__version__)
        parser.add_argument('--copyright', '-C', action='store_true', help='show copyright and exit')
        parser.add_argument('--license', '-L', action='store_true', help='show license and exit')
        parser.add_argument('--tutorial', '-T', action='store_true', help='show tutorial and exit')
        # Operations
        group = parser.add_argument_group('Operations')
        group.add_argument('--check-substance', action='store_true', help='request substance check of AUs')
        group.add_argument('--crawl', action='store_true', help='request crawl of AUs')
        group.add_argument('--crawl-plugins', action='store_true', help='cause plugin registries to be crawled')
        group.add_argument('--deep-crawl', action='store_true', help='request deep crawl of AUs')
        group.add_argument('--disable-indexing', action='store_true', help='disable indexing of AUs')
        group.add_argument('--poll', action='store_true', help='call poll on AUs')
        group.add_argument('--reindex-metadata', action='store_true', help='request metadata reindexing of AUs')
        group.add_argument('--reload-config', action='store_true', help='cause config to be reloaded')
        # Hosts
        group = parser.add_argument_group('Hosts')
        group.add_argument('--host', action='append', default=list(), help='add HOST to target hosts')
        group.add_argument('--hosts', action='append', default=list(), metavar='HFILE', help='add hosts in HFILE to target hosts')
        group.add_argument('--password', metavar='PASS', help='UI password (default: interactive prompt)')
        group.add_argument('--username', metavar='USER', help='UI username (default: interactive prompt)')
        # AUIDs
        group = parser.add_argument_group('AUIDs', 'Required by --check-substance, --crawl, --deep-crawl, --disable-indexing, --poll, --reindex-metadata')
        group.add_argument('--auid', action='append', default=list(), help='add AUID to target AUIDs')
        group.add_argument('--auids', action='append', default=list(), metavar='AFILE', help='add AUIDs in AFILE to target AUIDs')
        # Other options
        group = parser.add_argument_group('Other options')
        group.add_argument('--debug', action='store_true', help='print verbose error messages')
        group.add_argument('--depth', type=int, default=123, help='depth of deep crawls (default %(default)s)')
        group.add_argument('--keep-going', action='store_true', help='if an error occurs, go on to next target host')
        group.add_argument('--wait', type=int, default=0, metavar='SEC', help='wait SEC seconds between requests (default: %(default)s)')
        # Job pool
        group = parser.add_argument_group('Job pool')
        group.add_argument('--pool-size', metavar='SIZE', type=int, default=0, help='size of job pool, 0 for unlimited (default: %(default)s)')
        group.add_argument('--process-pool', action='store_true', help='use a process pool')
        group.add_argument('--thread-pool', action='store_true', help='use a thread pool (default)')
        # Done
        return parser

    def __init__(self, parser, args):
        super(_DebugPanelOptions, self).__init__()
        # --copyright, --license, --tutorial (--help, --version already taken care of)
        if any([args.copyright, args.license, args.tutorial]):
            if args.copyright: print(__copyright__)
            elif args.license: print(__license__)
            elif args.tutorial: print('This option is currently disabled.')
#            elif args.tutorial: print(__tutorial__)
            else: raise RuntimeError('internal error')
            sys.exit()
        # check_substance, crawl, crawl_plugins, deep_crawl, disable_indexing, poll, reindex_metadata, reload_config
        flds = ['check_substance', 'crawl', 'crawl_plugins', 'deep_crawl', 'disable_indexing', 'poll', 'reindex_metadata', 'reload_config']
        if len(list(filter(None, [getattr(args, fld) for fld in flds]))) != 1:
            parser.error('exactly one of %s is required' % (', '.join(['--%s' % (fld.replace('_', '-')) for fld in flds])))
        for fld in flds:
            setattr(self, fld, getattr(args, fld))
        # hosts
        self.hosts = args.host[:]
        for fstr in args.hosts:
            self.hosts.extend(_file_lines(fstr))
        if len(self.hosts) == 0:
            parser.error('at least one target host is required')
        # auids
        flds = ['check_substance', 'crawl', 'deep_crawl', 'disable_indexing', 'poll', 'reindex_metadata']
        if any([getattr(args, fld) for fld in flds]):
            self.auids = args.auid[:]
            for fstr in args.auids:
                self.auids.extend(_file_lines(fstr))
            if len(self.auids) == 0:
                parser.error('at least one target AUID is required')
        elif len(args.auid) + len(args.auids) > 0:
            parser.error('--auid, --auids only valid with %s' % (', '.join(['--%s' % (fld.replace('_', '-')) for fld in flds])))
        # depth, keep_going, pool_size, wait
        if args.pool_size < 0:
            parser.error('invalid pool size: %d' % (args.pool_size,))
        if args.wait < 0:
            parser.error('invalid wait duration: %d' % (args.wait,))
        for fld in ['debug', 'depth', 'keep_going', 'pool_size', 'wait']:
            setattr(self, fld, getattr(args, fld))
        # pool_class, pool_size
        if args.process_pool and args.thread_pool:
            parser.error('--process-pool and --thread-pool are mutually exclusive')
        self.pool_class = ProcessPool if args.process_pool else ThreadPool
        self.pool_size = args.pool_size or len(self.hosts)
        # auth
        u = args.username or getpass.getpass('UI username: ')
        p = args.password or getpass.getpass('UI password: ')
        self.auth = base64.b64encode('{}:{}'.format(u, p).encode('utf-8')).decode('utf-8')

def _make_request(options, host, query, **kwargs):
    for k, v in kwargs.items(): query = '{}&{}={}'.format(query, k, v)
    url = 'http://{}/DebugPanel?{}'.format(host, query)
    req = urllib.request.Request(url, headers={'Authorization': 'Basic {}'.format(options.auth)})
    return req

def _execute_request(req):
    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Exception('bad username or password (HTTP 401)') from e
        elif e.code == 403:
            raise Exception('not allowed from this IP address (HTTP 403)') from e
        else:
            raise Exception('HTTP {} error: {}'.format(e.code, e.reason)) from e
    except urllib.error.URLError as e:
        raise Exception('URL error: {}'.format(e.reason)) from e

def _do_per_auid(options, host, action, auid, **kwargs):
    action_enc = action.replace(' ', '%20')
    auid_enc = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
    req = _make_request(options, host, 'action={}&auid={}'.format(action_enc, auid_enc), **kwargs)
    _execute_request(req)

def _do_per_host(options, host, action):
    action_enc = action.replace(' ', '%20')
    req = _make_request(options, host, 'action={}'.format(action_enc))
    _execute_request(req)

def _do_per_auid_job(options_host):
    options, host = options_host
    kwargs = dict()
    if options.check_substance: action = 'Check Substance'
    elif options.crawl: action = 'Force Start Crawl'
    elif options.deep_crawl: action, kwargs = 'Force Deep Crawl', {'depth': options.depth}
    elif options.disable_indexing: action = 'Disable Indexing'
    elif options.poll: action = 'Start V3 Poll'
    elif options.reindex_metadata: action = 'Force Reindex Metadata'
    else: raise RuntimeError('internal error')
    try:
        sleep = False
        for auid in options.auids:
            if sleep: time.sleep(options.wait)
            sleep = options.wait > 0
            _do_per_auid(options, host, action, auid, **kwargs)
        return (host, None)
    except Exception as e:
        if options.debug:
            _STDERR_LOCK.acquire()
            traceback.print_exc()
            _STDERR_LOCK.release()
        return (host, e)

def _do_per_host_job(options_host):
    options, host = options_host
    if options.crawl_plugins: action = 'Crawl Plugins'
    elif options.reload_config: action = 'Reload Config'
    else: raise RuntimeError('internal error')
    try:
        _do_per_host(options, host, action)
        return (host, None)
    except Exception as e:
        if options.debug:
            _STDERR_LOCK.acquire()
            traceback.print_exc()
            _STDERR_LOCK.release()
        return (host, e)

def _do_debug_panel(options):
  pool = options.pool_class(options.pool_size)
  if options.crawl_plugins or options.reload_config:
      func = _do_per_host_job
  elif options.check_substance or options.crawl or options.deep_crawl \
        or options.disable_indexing or options.poll or options.reindex_metadata:
      func = _do_per_auid_job
  else: raise RuntimeError('internal error')
  jobs = [(options, host) for host in options.hosts]
  for host, error in pool.imap_unordered(func, jobs):
      if error is not None:
          _STDERR_LOCK.acquire()
          sys.stderr.write('{}: {}\n'.format(host, str(error)))
          _STDERR_LOCK.release()
          if not options.keep_going:
              sys.exit(1)

# Last modified 2020-10-01
def _file_lines(fstr):
    with open(os.path.expanduser(fstr)) as f: ret = list(filter(lambda y: len(y) > 0, [x.partition('#')[0].strip() for x in f]))
    if len(ret) == 0: sys.exit('Error: {} contains no meaningful lines'.format(fstr))
    return ret

def _main():
    '''Main method.'''
    parser = _DebugPanelOptions.make_parser()
    args = parser.parse_args()
    options = _DebugPanelOptions(parser, args)
    t = Thread(target=_do_debug_panel, args=(options,))
    t.daemon = True
    t.start()
    while True:
        t.join(1.0)
        if not t.is_alive(): break

# Main entry point
if __name__ == '__main__': _main()

