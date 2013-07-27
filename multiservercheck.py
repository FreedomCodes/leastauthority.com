#!/usr/bin/python

import sys, os
from cStringIO import StringIO

from twisted.python.filepath import FilePath
from twisted.python.failure import Failure
from twisted.internet import reactor

from lae_util.streams import LoggingTeeStream
from lae_automation.config import Config
from lae_automation.monitor import check_servers, read_serverinfo, compare_servers_to_local, \
    send_monitoring_report
from lae_automation.aws.queryapi import wait_for_EC2_properties, ServerInfoParser


skip_end_to_end = "--skip-end-to-end" in sys.argv
recreate_test_file = "--recreate" in sys.argv

endpoint_uri = 'https://ec2.us-east-1.amazonaws.com/'
config = Config()

ec2secretpath='../secret_config/ec2secret'
ec2accesskeyid = str(config.other['ec2_access_key_id'])
ec2secretkey = FilePath(ec2secretpath).getContent().strip()
serverinfocsvpath = '../serverinfo.csv'
lasterrorspath = '../lasterrors.txt'
secretsdirpath = '../secrets'

monitor_privkey_path = str(config.other['monitor_privkey_path'])

stdout = sys.stdout
errorstream = StringIO()
stderr = LoggingTeeStream(errorstream, stdout, '|')

serverinfotuple = read_serverinfo(serverinfocsvpath)
localstate = {}
for propertytuple in serverinfotuple:
    (launch_time, instance_id, publichost, status) = propertytuple
    localstate[instance_id] = (launch_time, publichost, status)

lasterrors = None
lasterrorsfp = FilePath(lasterrorspath)
if lasterrorsfp.exists():
    lasterrors = lasterrorsfp.getContent()

secretsdirfp = FilePath(secretsdirpath)
try:
    from lae_automation import endtoend
    (secrets_by_bucket, secrets_by_host) = endtoend.read_secrets_dir(secretsdirfp, stdout, stderr)
except ImportError:
    import traceback
    traceback.print_exc(stderr)
    (secrets_by_bucket, secrets_by_host) = ({}, {})
    skip_end_to_end = True

POLL_TIME = 10
ADDRESS_WAIT_TIME = 60

d = wait_for_EC2_properties(ec2accesskeyid, ec2secretkey, endpoint_uri,
                            ServerInfoParser(('launchTime', 'instanceId'), ('dnsName', 'instanceState.name')),
                            POLL_TIME, ADDRESS_WAIT_TIME, stdout, stderr)

d.addCallback(lambda remoteproperties: compare_servers_to_local(remoteproperties, localstate, stdout, stderr))

d.addCallback(lambda host_list: check_servers(host_list, monitor_privkey_path, secrets_by_bucket, secrets_by_host,
                                              stdout, stderr, skip_end_to_end, recreate_test_file))

def cb(x):
    if isinstance(x, Failure):
        print >>stderr, str(x)
        if hasattr(x.value, 'response'):
            print >>stderr, x.value.response

    errors = errorstream.getvalue()
    print >>sys.stderr, errors
    if errors != lasterrors:
        d2 = send_monitoring_report(errors)
        def _sent(ign):
            lasterrorsfp.setContent(errors)
            raise Exception("Sent failure report.")
        def _err(f):
            print >>sys.stderr, str(f)
            return f
        d2.addCallbacks(_sent, _err)
        return d2

d.addBoth(cb)
d.addCallbacks(lambda ign: os._exit(0), lambda ign: os._exit(1))
reactor.run()
