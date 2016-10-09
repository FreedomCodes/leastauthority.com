#!/usr/bin/python

import sys, os
from twisted.python.filepath import FilePath
from twisted.python.failure import Failure
from twisted.internet import reactor

from lae_automation.config import Config
from lae_automation.aws.queryapi import wait_for_EC2_properties, ServerInfoParser, pubIPextractor


endpoint_uri = 'https://ec2.us-east-1.amazonaws.com/'
config = Config()

ec2secretpath='../secret_config/ssec2_secret_key'
ec2accesskeyid = str(config.other['ssec2_access_key_id'])
ec2secretkey = FilePath(ec2secretpath).getContent().strip()

monitor_privkey_path = str(config.other['monitor_privkey_path'])
admin_privkey_path = str(config.other['ssec2admin_privkey_path'])


POLL_TIME = 10
ADDRESS_WAIT_TIME = 60

d = wait_for_EC2_properties(ec2accesskeyid, ec2secretkey, endpoint_uri,
                            ServerInfoParser(('launchTime', 'instanceId'), ('dnsName',)),
                            POLL_TIME, ADDRESS_WAIT_TIME, sys.stdout, sys.stderr)

def list_public_hosts(remotepropstuplelist):
    for rpt in remotepropstuplelist:
        publichost = pubIPextractor(rpt[2])
        if publichost:
            print publichost

d.addCallback(list_public_hosts)


def cb(x):
    if isinstance(x, Failure) and hasattr(x.value, 'response'):
        print x.value.response

d.addBoth(cb)
d.addCallbacks(lambda ign: os._exit(0), lambda ign: os._exit(1))
reactor.run()
