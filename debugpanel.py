#!/usr/bin/env python2

'''A script to interact with the LOCKSS daemon's DebugPanel servlet.'''

__copyright__ = '''\
Copyright (c) 2000, Board of Trustees of Leland Stanford Jr. University.
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

__version__ = '0.3.1'

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

import base64
import getpass
from multiprocessing import Pool as ProcessPool
from multiprocessing.dummy import Pool as ThreadPool
from optparse import OptionGroup, OptionParser
import os.path
import sys
from threading import Lock, Thread
import time
import traceback
import urllib2

_STDERR_LOCK = Lock()

class _DebugPanelOptions(object):

    @staticmethod
    def make_parser():
        # Create parser
        usage = '%prog {OPERATION} {--host=HOST|--hosts=HFILE}... [--auid=AUID|--auids=AFILE]... [OPTIONS]...'
        parser = OptionParser(version=__version__, description=__doc__, usage=usage)
        parser.add_option('--copyright', '-C', action='store_true', help='show copyright and exit')
        parser.add_option('--license', '-L', action='store_true', help='show license and exit')
        parser.add_option('--tutorial', '-T', action='store_true', help='show tutorial and exit')
        # Operations
        group = OptionGroup(parser, 'Operations')
        group.add_option('--check-substance', action='store_true', help='request substance check of AUs')
        group.add_option('--crawl', action='store_true', help='request crawl of AUs')
        group.add_option('--crawl-plugins', action='store_true', help='cause plugin registries to be crawled')
        group.add_option('--deep-crawl', action='store_true', help='request deep crawl of AUs')
        group.add_option('--disable-indexing', action='store_true', help='disable indexing of AUs')
        group.add_option('--poll', action='store_true', help='call poll on AUs')
        group.add_option('--reindex-metadata', action='store_true', help='request metadata reindexing of AUs')
        group.add_option('--reload-config', action='store_true', help='cause config to be reloaded')
        parser.add_option_group(group)
        # Hosts
        group = OptionGroup(parser, 'Hosts')
        group.add_option('--host', action='append', default=list(), help='add HOST to target hosts')
        group.add_option('--hosts', action='append', default=list(), metavar='HFILE', help='add hosts in HFILE to target hosts')
        group.add_option('--password', metavar='PASS', help='UI password (default: interactive prompt)')
        group.add_option('--username', metavar='USER', help='UI username (default: interactive prompt)')
        parser.add_option_group(group)
        # AUIDs
        group = OptionGroup(parser, 'AUIDs', 'Required by --check-substance, --crawl, --deep-crawl, --disable-indexing, --poll, --reindex-metadata')
        group.add_option('--auid', action='append', default=list(), help='add AUID to target AUIDs')
        group.add_option('--auids', action='append', default=list(), metavar='AFILE', help='add AUIDs in AFILE to target AUIDs')
        parser.add_option_group(group)
        # Other options
        group = OptionGroup(parser, 'Other options')
        group.add_option('--debug', action='store_true', help='print verbose error messages')
        group.add_option('--depth', type='int', default=123, help='depth of deep crawls (default %default)')
        group.add_option('--keep-going', action='store_true', help='if an error occurs, go on to next target host')
        group.add_option('--wait', type='int', default=0, metavar='SEC', help='wait SEC seconds between requests (default: %default)')
        parser.add_option_group(group)
        # Job pool
        group = OptionGroup(parser, 'Job pool')
        group.add_option('--pool-size', metavar='SIZE', type='int', default=0, help='size of job pool, 0 for unlimited (default: %default)')
        group.add_option('--process-pool', action='store_true', help='use a process pool')
        group.add_option('--thread-pool', action='store_true', help='use a thread pool (default)')
        parser.add_option_group(group)
        # Done
        return parser

    def __init__(self, parser, opts, args):
        super(_DebugPanelOptions, self).__init__()
        # --copyright, --license, --tutorial (--help, --version already taken care of)
        if any([opts.copyright, opts.license, opts.tutorial]):
            if opts.copyright: print __copyright__
            elif opts.license: print __license__
            elif opts.tutorial: print __tutorial__
            else: raise RuntimeError, 'internal error'
            sys.exit()
        # check_substance, crawl, crawl_plugins, deep_crawl, disable_indexing, poll, reindex_metadata, reload_config
        flds = ['check_substance', 'crawl', 'crawl_plugins', 'deep_crawl', 'disable_indexing', 'poll', 'reindex_metadata', 'reload_config']
        if len(filter(None, [getattr(opts, fld) for fld in flds])) != 1:
            parser.error('exactly one of %s is required' % (', '.join(['--%s' % (fld.replace('_', '-')) for fld in flds])))
        for fld in flds:
            setattr(self, fld, getattr(opts, fld))
        # hosts
        self.hosts = opts.host[:]
        for fstr in opts.hosts:
            self.hosts.extend(_file_lines(fstr))
        if len(self.hosts) == 0:
            parser.error('at least one target host is required')
        # auids
        flds = ['check_substance', 'crawl', 'deep_crawl', 'disable_indexing', 'poll', 'reindex_metadata']
        if any([getattr(opts, fld) for fld in flds]):
            self.auids = opts.auid[:]
            for fstr in opts.auids:
                self.auids.extend(_file_lines(fstr))
            if len(self.auids) == 0:
                parser.error('at least one target AUID is required')
        elif len(opts.auid) + len(opts.auids) > 0:
            parser.error('--auid, --auids only valid with %s' % (', '.join(['--%s' % (fld.replace('_', '-')) for fld in flds])))
        # depth, keep_going, pool_size, wait
        if opts.pool_size < 0:
            parser.error('invalid pool size: %d' % (opts.pool_size,))
        if opts.wait < 0:
            parser.error('invalid wait duration: %d' % (opts.wait,))
        for fld in ['debug', 'depth', 'keep_going', 'pool_size', 'wait']:
            setattr(self, fld, getattr(opts, fld))
        # pool_class, pool_size
        if opts.process_pool and opts.thread_pool:
            parser.error('--process-pool and --thread-pool are mutually exclusive')
        self.pool_class = ProcessPool if opts.process_pool else ThreadPool
        self.pool_size = opts.pool_size or len(self.hosts)
        # auth
        u = opts.username or getpass.getpass('UI username: ')
        p = opts.password or getpass.getpass('UI password: ')
        self.auth = base64.encodestring('%s:%s' % (u, p)).replace('\n', '')

def _make_request(options, host, query, **kwargs):
    for k, v in kwargs.iteritems(): query = '%s&%s=%s' % (query, k, v)
    req = urllib2.Request('http://%s/DebugPanel?%s' % (host, query))
    req.add_header('Authorization', 'Basic %s' % options.auth)
    return req

def _execute_request(req):
    try:
        return urllib2.urlopen(req)
    except urllib2.HTTPError as e:
        if e.code == 401:
            raise Exception, 'bad username or password (HTTP 401)'
        elif e.code == 403:
            raise Exception, 'not allowed from this IP address (HTTP 403)'
        else:
            raise Exception, 'HTTP %d error: %s' % (e.code, e.reason)
    except urllib2.URLError as e:
        raise Exception, 'URL error: %s' % (e.reason,)

def _do_per_auid(options, host, action, auid, **kwargs):
    action_enc = action.replace(' ', '%20')
    auid_enc = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
    req = _make_request(options, host, 'action=%s&auid=%s' % (action_enc, auid_enc), **kwargs)
    _execute_request(req)

def _do_per_host(options, host, action):
    action_enc = action.replace(' ', '%20')
    req = _make_request(options, host, 'action=%s' % (action_enc,))
    _execute_request(req)

def _do_per_auid_job(options_host):
    options, host = options_host
    kwargs = dict()
    if options.check_substance: action = 'Check Substance'
    elif options.crawl: action = 'Force Start Crawl'
    elif options.deep_crawl: action, kwargs = 'Force Deep Crawl', {'depth':options.depth}
    elif options.disable_indexing: action = 'Disable Indexing'
    elif options.poll: action = 'Start V3 Poll'
    elif options.reindex_metadata: action = 'Force Reindex Metadata'
    else: raise RuntimeError, 'internal error'
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
    else: raise RuntimeError, 'internal error'
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
  else: raise RuntimeError, 'internal error'
  jobs = [(options, host) for host in options.hosts]
  for host, error in pool.imap_unordered(func, jobs):
      if error is not None:
          _STDERR_LOCK.acquire()
          sys.stderr.write('%s: %s\n' % (host, str(error),))
          _STDERR_LOCK.release()
          if not options.keep_going:
              sys.exit(1)

# Last modified 2015-08-31
def _file_lines(fstr):
    with open(os.path.expanduser(fstr)) as f: ret = filter(lambda y: len(y) > 0, [x.partition('#')[0].strip() for x in f])
    if len(ret) == 0: sys.exit('Error: %s contains no meaningful lines' % (fstr,))
    return ret

def _main():
    '''Main method.'''
    parser = _DebugPanelOptions.make_parser()
    (opts, args) = parser.parse_args()
    options = _DebugPanelOptions(parser, opts, args)
    t = Thread(target=_do_debug_panel, args=(options,))
    t.daemon = True
    t.start()
    while True:
        t.join(1.0)
        if not t.is_alive(): break

# Main entry point
if __name__ == '__main__': _main()

