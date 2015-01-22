#!/usr/bin/env python

# $Id$

#
# Copyright (c) 2000-2015 Board of Trustees of Leland Stanford Jr. University,
# all rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# STANFORD UNIVERSITY BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Except as contained in this notice, the name of Stanford University shall not
# be used in advertising or otherwise to promote the sale, use or other dealings
# in this Software without prior written authorization from Stanford University.
#

#
# A script to interact with DebugPanel.
#
# Usage examples:
#
# debugpanel.py --host=lockss.university.edu:8081 --reload-config
#   Causes lockss.university.edu:8081 to reload its config. (Prompts for a UI
#   username and password.)
#
# debugpanel.py --host=lockss.university.edu:8081 --reload-config --username=UUU
#   Same, but uses UUU as the UI username (and prompts for a UI password).
#
# debugpanel.py --hosts=myhosts.txt --reload-config
#   Causes each host listed in myhosts.txt to reload its config. (Prompts for a
#   UI username and password once, used for all hosts.) Lines that are empty,
#   are all white space, or begin with the character '#' are ignored, other
#   lines are expected to be a host.
#
# debugpanel.py --hosts=myhosts.txt --crawl-plugins
#   Causes each host listed in myhosts.txt to crawl its plugin registries.
#
# debugpanel.py --hosts=myhosts.txt --crawl 'auid1' 'auid2' 'auid3'
#   Causes each host listed in myhosts.txt to request a crawl of the AUs
#   identified by the AUIDs auid1, auid2 and auid3. Quoting recommended (AUIDs
#   have ampersands, which conflict with shell commands.)
#
# debugpanel.py --hosts=myhosts.txt --crawl --auids=myauids.txt
#   Causes each host listed in myhosts.txt to request a crawl of the AUs
#   identified by the AUIDS listed in myauids.txt. Lines in the latter that are
#   empty, are all white space, or begin with the character '#' are ignored,
#   other lines are expected to be an AUID.
#
# debugpanel.py --hosts=myhosts.txt --deep-crawl --auids=myauids.txt
#   Causes each host listed in myhosts.txt to request a deep crawl of the AUs
#   identified by the AUIDS listed in myauids.txt (using some large depth).
#
# debugpanel.py --hosts=myhosts.txt --deep-crawl --auids=myauids.txt --depth=DDD
#   Causes each host listed in myhosts.txt to request a deep crawl of the AUs
#   identified by the AUIDS listed in myauids.txt (using the integer depth DDD).
#
# debugpanel.py --hosts=myhosts.txt --poll --auids=myauids.txt
#   Causes each host listed in myhosts.txt to request a poll of the AUs
#   identified by the AUIDS listed in myauids.txt.
#
# debugpanel.py --hosts=myhosts.txt --poll --auids=myauids.txt --wait=WWW
#   Same, but waits WWW seconds between each request (recommended for all
#   actions requiring a per-AU request like --crawl, --deep-crawl or --poll).
#

__version__ = '0.1.1'

import base64
import getpass
import optparse
import sys
import time
import urllib2

# B=boolean, I=integer, L=list, S=string
LAUIDS = 'auids'
SAUTH = 'auth'
BCRAWL = 'crawl'
BCRAWLPLUGINS = 'crawl-plugins'
BDEEPCRAWL = 'deep-crawl'
IDEPTH = 'depth'
LHOSTS = 'hosts'
BPOLL = 'poll'
BRELOADCONFIG = 'reload-config'
IWAIT = 'wait'

# Global
must_sleep = False

def make_parser():
  parser = optparse.OptionParser(version=__version__, usage='%prog {--host=HOST | --hosts=HFILE} [OPTIONS] [--auids=AFILE | AUID...]')
  parser.add_option('--auids', metavar='AFILE', help='reads AUIDs from AFILE instead of command line arguments')
  parser.add_option('--crawl', help='requests crawl of selected AUs', action='store_true', default=False)
  parser.add_option('--crawl-plugins', help='causes plugin registries to be crawled', action='store_true', default=False)
  parser.add_option('--deep-crawl', help='requests deep crawl of selected AUs', action='store_true', default=False)
  parser.add_option('--depth', help='custom depth of deep crawls', default='123')
  parser.add_option('--host', help='host name')
  parser.add_option('--hosts', metavar='HFILE', help='reads host names from HFILE instead of --host')
  parser.add_option('--password', metavar='PASS', help='UI password')
  parser.add_option('--poll', help='calls poll on selected AUs', action='store_true', default=False)
  parser.add_option('--reload-config', help='causes the config to be reloaded', action='store_true', default=False)
  parser.add_option('--username', metavar='USER', help='UI username')
  parser.add_option('--wait', metavar='SEC', help='wait SEC seconds between requests', default='0')
  return parser

def process_options(opts, args):
  options = dict()
  if opts.host is None and opts.hosts is None: sys.exit('one of --host, --hosts is required')
  if opts.host and opts.hosts: sys.exit('Error: --host, --hosts are mutually exclusive')
  if opts.host: options[LHOSTS] = [opts.host]
  else: options[LHOSTS] = file_lines(opts.hosts)
  if True not in [opts.crawl, opts.crawl_plugins, opts.deep_crawl, opts.poll, opts.reload_config]:
    sys.exit('Error: one of --crawl, --crawl-plugins, --deep_crawl, --poll, --reload-config is required')
  options[BCRAWL] = opts.crawl
  options[BCRAWLPLUGINS] = opts.crawl_plugins
  options[BDEEPCRAWL] = opts.deep_crawl
  options[BPOLL] = opts.poll
  options[BRELOADCONFIG] = opts.reload_config
  if opts.auids: options[LAUIDS] = file_lines(opts.auids)
  else: options[LAUIDS] = args
  if opts.username is None: u = getpass.getpass('UI username: ')
  else: u = opts.username
  if opts.password is None: p = getpass.getpass('UI password: ')
  else: p = opts.password
  options[SAUTH] = base64.encodestring('%s:%s' % (u, p)).replace('\n', '')
  options[IDEPTH] = int(opts.depth)
  options[IWAIT] = int(opts.wait)
  return options

def do_crawl_plugins(options, host):
  do_per_host(options, host, 'Crawl%20Plugins')

def do_reload_config(options, host):
  do_per_host(options, host, 'Reload%20Config')

def do_per_host(options, host, action):
  maybe_sleep(options)
  req = make_request(options, host, 'action=%s' % (action,))
  execute_request(req)

def do_crawl(options, host, auid):
  do_per_auid(options, host, 'Force%20Start%20Crawl', auid)

def do_deep_crawl(options, host, auid):
  do_per_auid(options, host, 'Force%20Deep%20Crawl', auid, depth=options[IDEPTH])

def do_poll(options, host, auid):
  do_per_auid(options, host, 'Start%20V3%20Poll', auid)

def do_per_auid(options, host, action, auid, **kwargs):
  maybe_sleep(options)
  auid_enc = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
  req = make_request(options, host, 'action=%s&auid=%s' % (action, auid_enc), **kwargs)
  execute_request(req)

def maybe_sleep(options):
  global must_sleep
  if must_sleep: time.sleep(options[IWAIT])
  must_sleep = True

def make_request(options, host, query, **kwargs):
  for k, v in kwargs.iteritems(): query = '%s&%s=%s' % (query, k, v)
  req = urllib2.Request('http://%s/DebugPanel?%s' % (host, query))
  req.add_header('Authorization', 'Basic %s' % options[SAUTH])
  return req

def execute_request(req):
  try: return urllib2.urlopen(req)
  except urllib2.HTTPError as e:
    if e.code == 401: sys.exit('Error: bad username or password (HTTP 401)')
    else: sys.exit('Error: HTTP %d' % (e.code,))

def file_lines(filestr):
  ret = [line.strip() for line in open(filestr).readlines() if not (line.isspace() or line.startswith('#'))]
  if len(ret) == 0: sys.exit('Error: %s contains no meaningful lines' % (filestr,))
  return ret

if __name__ == '__main__':
  parser = make_parser()
  (opts, args) = parser.parse_args()
  options = process_options(opts, args)
  for host in options[LHOSTS]:
    if options[BCRAWLPLUGINS]: do_crawl_plugins(options, host)
    if options[BRELOADCONFIG]: do_reload_config(options, host)
    for auid in options[LAUIDS]:
      if options[BCRAWL]: do_crawl(options, host, auid)
      if options[BDEEPCRAWL]: do_deep_crawl(options, host, auid)
      if options[BPOLL]: do_poll(options, host, auid)

