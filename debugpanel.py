#!/usr/bin/env python

# $Id$

__copyright__ = '''\
Copyright (c) 2000-2015 Board of Trustees of Leland Stanford Jr. University,
all rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
STANFORD UNIVERSITY BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Except as contained in this notice, the name of Stanford University shall not
be used in advertising or otherwise to promote the sale, use or other dealings
in this Software without prior written authorization from Stanford University.
'''

__version__ = '0.2.5'

__man__ = '''\
A script to interact with DebugPanel.

A list of hosts is built up by accumulating host:port pairs passed with --host
and host:port pairs read from files passed with --hosts.

If a username is passed with --username, use it to connect to hosts, otherwise
prompt for one interactively. Likewise, if a password is passed with
--password, use it to connect to hosts, otherwise prompt for one interactively.

Operations that can be applied to each host include:

  --crawl-plugins
      Causes the daemon to recrawl plugin registries.

  --reload-config
      Causes the daemon to reload its config.

Other operations are applied to specific AUs. A list of AUIDs is built up by
accumulating those read from files passed with --auids and those passed via
--auid and the command line as arguments.

Operations that can be applied to each AU of each host include:

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

Currently, all individual operations are performed sequentially. You can add a
pause with --wait (expressed in whole seconds). The --keep-going option goes on
to the next host if something fails for a given host.
'''

import base64
import getpass
import optparse
import os.path
import sys
import time
import urllib2

class Options(object):
  DEPTH = 123
  WAIT = 0
  def __init__(self):
    super(Options, self).__init__()
    self.__auth = None
    self.__auids = list()
    self.__check_substance = False
    self.__crawl = False
    self.__crawl_plugins = False
    self.__deep_crawl = False
    self.__depth = Options.DEPTH
    self.__disable_indexing = False
    self.__hosts = list()
    self.__keep_going = False
    self.__poll = False
    self.__reindex_metadata = False
    self.__reload_config = False
    self.__wait = Options.WAIT
  def add_auids(self, auids): self.__auids.extend(auids)
  def get_auids(self): return self.__auids
  def set_auth(self, auth): self.__auth = auth
  def get_auth(self): return self.__auth
  def is_check_substance(self): return self.__check_substance
  def set_check_substance(self, check_substance): self.__check_substance = check_substance
  def is_crawl(self): return self.__crawl
  def set_crawl(self, crawl): self.__crawl = crawl
  def is_crawl_plugins(self): return self.__crawl_plugins
  def set_crawl_plugins(self, crawl_plugins): self.__crawl_plugins = crawl_plugins
  def is_deep_crawl(self): return self.__deep_crawl
  def set_deep_crawl(self, deep_crawl): self.__deep_crawl = deep_crawl
  def get_depth(self): return self.__depth
  def set_depth(self, depth): self.__depth = depth
  def is_disable_indexing(self): return self.__disable_indexing
  def set_disable_indexing(self, disable_indexing): self.__disable_indexing = disable_indexing
  def get_hosts(self): return self.__hosts
  def add_hosts(self, hosts): self.__hosts.extend(hosts)
  def is_keep_going(self): return self.__keep_going
  def set_keep_going(self, keep_going): self.__keep_going = keep_going
  def is_poll(self): return self.__poll
  def set_poll(self, poll): self.__poll = poll
  def is_reindex_metadata(self): return self.__reindex_metadata
  def set_reindex_metadata(self, reindex_metadata): self.__reindex_metadata = reindex_metadata
  def is_reload_config(self): return self.__reload_config
  def set_reload_config(self, reload_config): self.__reload_config = reload_config
  def get_wait(self): return self.__wait
  def set_wait(self, wait): self.__wait = wait

# Global
must_sleep = False

def make_parser():
  parser = optparse.OptionParser(version=__version__, usage='%prog [--host=HOST|--hosts=HFILE]... [OPTIONS] [--auids=AFILE|--auid=AUID|AUID]...')
  parser.add_option('--auid', action='append', default=list(), metavar='AUID', help='adds AUID to the list of AUIDs')
  parser.add_option('--auids', action='append', default=list(), metavar='AFILE', help='adds AUIDs from AFILE to the list of AUIDs')
  parser.add_option('--check-substance', action='store_true', default=False, help='requests substance check of selected AUs')
  parser.add_option('--crawl', action='store_true', default=False, help='requests crawl of selected AUs')
  parser.add_option('--crawl-plugins', action='store_true', default=False, help='causes plugin registries to be crawled')
  parser.add_option('--deep-crawl', action='store_true', default=False, help='requests deep crawl of selected AUs')
  parser.add_option('--depth', type='int', default=Options.DEPTH, help='depth of deep crawls (default %default)')
  parser.add_option('--disable-indexing', action='store_true', default=False, help='disables indexing of selected AUs')
  parser.add_option('--host', action='append', default=list(), help='adds host:port pair to the list of hosts')
  parser.add_option('--hosts', action='append', default=list(), metavar='HFILE', help='adds host:port pairs from HFILE to the list of hosts')
  parser.add_option('--keep-going', action='store_true', default=False, help='if an error occurs, go on to the next host')
  parser.add_option('--password', metavar='PASS', help='UI password')
  parser.add_option('--poll', action='store_true', default=False, help='calls poll on selected AUs')
  parser.add_option('--reindex-metadata', action='store_true', default=False, help='requests metadata reindexing of selected AUs')
  parser.add_option('--reload-config', action='store_true', default=False, help='causes the config to be reloaded')
  parser.add_option('--username', metavar='USER', help='UI username')
  parser.add_option('--wait', type='int', default=Options.WAIT, metavar='SEC', help='wait SEC seconds between requests (default %default)')
  return parser

def process_options(parser, opts, args):
  options = Options()
  if not any([opts.check_substance, opts.crawl, opts.crawl_plugins, opts.deep_crawl, opts.disable_indexing, opts.poll, opts.reindex_metadata, opts.reload_config]):
    parser.error('At least one of --check-substance, --crawl, --crawl-plugins, --deep-crawl, --disable-indexing, --poll, --reindex-metadata, --reload-config is required')
  if len(opts.host) + len(opts.hosts) == 0: parser.error('At least one host is required')
  options.add_hosts(opts.host)
  for f in opts.hosts: options.add_hosts(_file_lines(f))
  options.set_crawl_plugins(opts.crawl_plugins)
  options.set_reload_config(opts.reload_config)
  if any([opts.check_substance, opts.crawl, opts.deep_crawl, opts.disable_indexing, opts.poll, opts.reindex_metadata]) and len(args) + len(opts.auid) + len(opts.auids) == 0:
    parser.error('For --check-substance, --crawl, --deep-crawl, --disable-indexing, --poll, --reindex-metadata, at least one AUID is required')
  options.add_auids(args)
  options.add_auids(opts.auid[:])
  for f in opts.auids: options.add_auids(_file_lines(f))
  options.set_check_substance(opts.check_substance)
  options.set_crawl(opts.crawl)
  options.set_deep_crawl(opts.deep_crawl)
  options.set_disable_indexing(opts.disable_indexing)
  options.set_poll(opts.poll)
  options.set_reindex_metadata(opts.reindex_metadata)
  options.set_depth(opts.depth)
  options.set_keep_going(opts.keep_going)
  options.set_wait(opts.wait)
  if opts.username is None: u = raw_input('UI username: ')
  else: u = opts.username
  if opts.password is None: p = getpass.getpass('UI password: ')
  else: p = opts.password
  options.set_auth(base64.encodestring('%s:%s' % (u, p)).replace('\n', ''))
  return options

def do_crawl_plugins(options, host):
  do_per_host(options, host, 'Crawl Plugins')

def do_reload_config(options, host):
  do_per_host(options, host, 'Reload Config')

def do_per_host(options, host, action):
  maybe_sleep(options)
  action_enc = action.replace(' ', '%20')
  req = make_request(options, host, 'action=%s' % (action_enc,))
  execute_request(req, host)

def do_check_substance(options, host, auid):
  do_per_auid(options, host, 'Check Substance', auid)

def do_crawl(options, host, auid):
  do_per_auid(options, host, 'Force Start Crawl', auid)

def do_deep_crawl(options, host, auid):
  do_per_auid(options, host, 'Force Deep Crawl', auid, depth=options.get_depth())

def do_disable_indexing(options, host, auid):
  do_per_auid(options, host, 'Disable Indexing', auid)

def do_poll(options, host, auid):
  do_per_auid(options, host, 'Start V3 Poll', auid)

def do_reindex_metadata(options, host, auid):
  do_per_auid(options, host, 'Reindex Metadata', auid)

def do_per_auid(options, host, action, auid, **kwargs):
  maybe_sleep(options)
  action_enc = action.replace(' ', '%20')
  auid_enc = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
  req = make_request(options, host, 'action=%s&auid=%s' % (action_enc, auid_enc), **kwargs)
  execute_request(req, host)

def maybe_sleep(options):
  global must_sleep
  if must_sleep: time.sleep(options.get_wait())
  must_sleep = True

def make_request(options, host, query, **kwargs):
  for k, v in kwargs.iteritems(): query = '%s&%s=%s' % (query, k, v)
  req = urllib2.Request('http://%s/DebugPanel?%s' % (host, query))
  req.add_header('Authorization', 'Basic %s' % options.get_auth())
  return req

def execute_request(req, host):
  try: return urllib2.urlopen(req)
  except urllib2.URLError as e:
    raise Exception, 'Error: %s: %s' % (host, e.reason)
  except urllib2.HTTPError as e:
    if e.code == 401: raise Exception, 'Error: %s: bad username or password (HTTP 401)' % (host,)
    else: raise Exception, 'Error: %s: HTTP %d' % (host, e.code)

# Last modified 2015-08-31
def _file_lines(fstr):
  with open(os.path.expanduser(fstr)) as f: ret = filter(lambda y: len(y) > 0, [x.partition('#')[0].strip() for x in f])
  if len(ret) == 0: sys.exit('Error: %s contains no meaningful lines' % (fstr,))
  return ret

if __name__ == '__main__':
  parser = make_parser()
  (opts, args) = parser.parse_args()
  options = process_options(parser, opts, args)
  for host in options.get_hosts():
    try:
      if options.is_crawl_plugins(): do_crawl_plugins(options, host)
      if options.is_reload_config(): do_reload_config(options, host)
      for auid in options.get_auids():
        if options.is_check_substance(): do_check_substance(options, host, auid)
        if options.is_crawl(): do_crawl(options, host, auid)
        if options.is_deep_crawl(): do_deep_crawl(options, host, auid)
        if options.is_disable_indexing(): do_disable_indexing(options, host, auid)
        if options.is_poll(): do_poll(options, host, auid)
        if options.is_reindex_metadata(): do_reindex_metadata(options, host, auid)
    except Exception as e:
      if not options.is_keep_going(): raise
      print str(e)

