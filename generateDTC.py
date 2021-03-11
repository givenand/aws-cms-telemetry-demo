#!/usr/bin/env python3

import argparse
import logging
import json
import sys
import requests
import uuid
import time
import boto3
import botocore 
from utils.config_loader import Config
from pprint import pprint as pretty
import json
import random

from datetime import datetime

from payloadHandler import payloadHandler 

from cmsHandler import ConnectedMobility
from cognitoHandler import Cognito

from awsiot import mqtt_connection_builder
from awscrt import io, mqtt, auth, http

log = logging.getLogger('deploy.cf.create_or_update')  # pylint: disable=C0103

def on_connection_interrupted(self, connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))

# Callback when an interrupted connection is re-established.
def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(self.on_resubscribe_complete)

def main(vin, dtc):

   #Set Config path
   CONFIG_PATH = 'config.ini'
   payloadhandler = payloadHandler(CONFIG_PATH)
   #c = Cognito(profile)
   #m = ConnectedMobility(profile, stackname)
   config = Config(CONFIG_PATH)
   config_parameters = config.get_section('SETTINGS')
   ENDPOINT = config_parameters['IOT_ENDPOINT']
   
   CLIENT_ID = vin
   PATH_TO_CERT = "{}/{}".format(config_parameters['SECURE_CERT_PATH'].format(unique_id=CLIENT_ID), config_parameters['PROD_CERT'])
   PATH_TO_KEY = "{}/{}".format(config_parameters['SECURE_CERT_PATH'].format(unique_id=CLIENT_ID), config_parameters['PROD_KEY'])
   PATH_TO_ROOT = "{}/{}".format(config_parameters['ROOT_CERT_PATH'], config_parameters['ROOT_CERT'])

   event_loop_group = io.EventLoopGroup(1)
   host_resolver = io.DefaultHostResolver(event_loop_group)
   client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

   test_MQTTClient = mqtt_connection_builder.mtls_from_path(
        endpoint=ENDPOINT,
        cert_filepath=PATH_TO_CERT,
        pri_key_filepath=PATH_TO_KEY,
        client_bootstrap=client_bootstrap,
        ca_filepath=PATH_TO_ROOT,
        client_id=CLIENT_ID,
        clean_session=False,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        keep_alive_secs=6)
   
   print("Connecting with Prod certs to {} with client ID '{}'...".format(ENDPOINT, CLIENT_ID))
   connect_future = test_MQTTClient.connect()
 
   connect_future.result()
   print("Connected with production certificates to the endpoint")
   
   payload = payloadhandler.getDTCPayload( dtc, CLIENT_ID)
   payloadhandler.publishDTCPayload(test_MQTTClient, payload, CLIENT_ID)
   print("Successfully published DTC: {}".format(dtc))
  
   exit()
           
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()

    parser.add_argument("-v", "--VIN", action="store", dest="vin", default=None, help="VIN for vehicle")
    parser.add_argument("-d", "--DTC", action="store", dest="dtc", default=None, help="DTC for vehicle")

    args = parser.parse_args()

    if args.vin and args.dtc:
        main(args.vin, args.dtc)
    else:
        print('[Error] Missing arguments..')
        parser.print_help()