#!/usr/bin/python

import sys, os, traceback
from twisted.python.filepath import FilePath
from twisted.python.failure import Failure
from twisted.internet import reactor

from lae_automation.config import Config
from lae_automation.server import register_gatherer
from lae_automation.aws.queryapi import wait_for_EC2_properties, ServerInfoParser, pubIPextractor


endpoint_uri = 'https://ec2.us-east-1.amazonaws.com/'
configpath='../lae_automation_config.json'
config = Config(configpath)

ec2secretpath='../ec2secret'
ec2accesskeyid = str(config.other['ec2_access_key_id'])
ec2secretkey = FilePath(ec2secretpath).getContent().strip()

monitor_privkey_path = str(config.other['monitor_privkey_path'])
admin_privkey_path = str(config.other['admin_privkey_path'])


POLL_TIME = 10
ADDRESS_WAIT_TIME = 60

d = wait_for_EC2_properties(ec2accesskeyid, ec2secretkey, endpoint_uri,
                            ServerInfoParser(('launchTime', 'instanceId'), ('dnsName',)),
                            POLL_TIME, ADDRESS_WAIT_TIME, sys.stdout, sys.stderr)

def notify_servers(remotepropstuplelist):
    for rpt in remotepropstuplelist:
        publichost = pubIPextractor(rpt[2])
        if not publichost:
            print >>sys.stderr, ("Warning: Host launched at %s with instance ID %s has no public IP (maybe it has been terminated)."
                                 % (rpt[0], rpt[1]))
        else:
            print "Notifying %r about gatherer at: %s ..." % (publichost, gatherer_furl)
            try:
                register_gatherer(publichost, admin_privkey_path, stdout, stderr, gatherer_type, gatherer_furl)
            except UnrecognizedGathererType, exceptinstance:
                print >>sys.stderr, "The registration attempted to register a %s gatherer." % (exceptinstance.gtype,)
                raise
            except:
                traceback.print_exc()

d.addCallback(notify_servers)


def cb(x):
    print str(x)
    if isinstance(x, Failure) and hasattr(x.value, 'response'):
        print x.value.response

d.addBoth(cb)
d.addCallbacks(lambda ign: os._exit(0), lambda ign: os._exit(1))
reactor.run()
