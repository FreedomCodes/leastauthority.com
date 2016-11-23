#!/usr/bin/python

import os, sys

from twisted.internet import reactor
from twisted.python.failure import Failure

from lae_automation.config import Config
from lae_automation.signup import DeploymentConfiguration, deploy_server


if len(sys.argv) < 13:
    print "Usage: python deploy_server.py ACCESS_KEY_ID SECRET_KEY USER_TOKEN PRODUCT_TOKEN BUCKET_NAME AMI_IMAGE_ID INSTANCE_SIZE CUSTOMER_NAME CUSTOMER_EMAIL CUSTOMER_KEYINFO SECRETS_PATH CONFIG_PATH"
    print "Happy server-deploying!"
    sys.exit(1)

useraccesskeyid = sys.argv[1]
usersecretkey = sys.argv[2]
usertoken = sys.argv[3]
producttoken = sys.argv[4]
bucketname = sys.argv[5]
amiimageid = sys.argv[6]
instancesize = sys.argv[7]
customer_name = sys.argv[8]
customer_email = sys.argv[9]
customer_keyinfo = sys.argv[10]
secretspath = sys.argv[11]
configpath = sys.argv[12]

EC2_ENDPOINT = 'https://ec2.us-east-1.amazonaws.com/'
#EC2_ENDPOINT = 'https://ec2.amazonaws.com/'

secretsfile = open(secretspath, 'a')

def cb(x):
    secretsfile.close()
    print str(x)
    if isinstance(x, Failure) and hasattr(x.value, 'response'):
        print x.value.response

config = Config(configpath)
deploy_config = DeploymentConfiguration(
    s3_access_key_id=useraccesskeyid,
    s3_secret_key=usersecretkey,
    bucketname=bucketname,
    amiimageid=amiimageid,
    instancesize=instancesize,
    usertoken=usertoken,
    producttoken=producttoken,
    oldsecrets=None,
    customer_email=customer_email,
    customer_pgpinfo=None,
    secretsfile=secretspath,

    ssec2_access_key_id=config["ssec2_access_key_id"],
    ssec2_secret_path=config["ssec2_secret_path"],

    ssec2admin_keypair_name=config["ssec2admin_keypair_name"],
    ssec2admin_keypair_path=config["ssec2admin_keypair_path"],

    monitor_pubkey_path=config["monitor_pubkey_path"],
    monitor_privkey_path=config["monitor_privkey_path"],
)

d = deploy_server(deploy_config, sys.stdout, sys.stderr)
d.addBoth(cb)
d.addCallbacks(lambda ign: os._exit(0), lambda ign: os._exit(1))
reactor.run()
