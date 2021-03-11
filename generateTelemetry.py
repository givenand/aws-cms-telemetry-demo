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
from iotHandler import IOT
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

def main(profile, vin):

   #Set Config path
   CONFIG_PATH = 'config.ini'
   payloadhandler = payloadHandler(CONFIG_PATH)
   #c = Cognito(profile)
   #m = ConnectedMobility(profile, stackname)
   config = Config(CONFIG_PATH)
   config_parameters = config.get_section('SETTINGS')
   #ENDPOINT = config_parameters['IOT_ENDPOINT']
   i = IOT(profile,"", "", CONFIG_PATH)   
   ENDPOINT = i.iotEndpoint
   
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
        
   tripId = uuid.uuid4().hex
   print("Generating Trip ID of {}".format(tripId))
   latLongDict = payloadhandler.generateLatLongFromCSV()
   print("Begin publishing trip data.  Will publish {} payloads".format(len(latLongDict)))
   startCoords = next(iter(latLongDict))
   endCoords = list(latLongDict)[-1]
   startTime = payloadhandler.getTimestampMS()
   for i in latLongDict:
       payload = payloadhandler.getPayload( i, tripId, CLIENT_ID)
       payloadhandler.publishPayload(test_MQTTClient, payload, CLIENT_ID)
       print("Successfully published coordinates {} of {}".format(i, len(latLongDict)))
       time.sleep(1)
   
   trippayload = payloadhandler.getTripPayload(startTime, startCoords, endCoords, tripId, CLIENT_ID)
   payloadhandler.publishTripPayload(test_MQTTClient, trippayload, CLIENT_ID) 
   
   print("Trip data published sucessfully")   
   exit()
           
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser('generateTelemetry.py')

    parser.add_argument("-p", "--profile", action="store", dest="profile", default=None, help="AWS CLI profile")
    #parser.add_argument("-s", "--stackname", action="store", dest="stackname", default=None, help="AWS Stack Name for CMS")
    #parser.add_argument("-u", "--username", action="store", dest="username", help="Username to log into CMS")
    #parser.add_argument("-pwd", "--password", action="store", dest="password", default=None, help="Password for CMS User")
    #parser.add_argument("-c", "--city", action="store", dest="city", help="City to start the journey")
    #parser.add_argument("-st", "--state", action="store", dest="state", default=None, help="State to start the journey")
    parser.add_argument("-v", "--VIN", action="store", dest="vin", default=None, help="VIN for vehicle")
    
    args = parser.parse_args()

    if args.profile and args.vin:
        main(args.profile, args.vin)
    else:
        print('[Error] Missing Arguments..')
        parser.print_help()

