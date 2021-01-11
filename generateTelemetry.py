#!/usr/bin/env python3

import argparse
import logging
import json
import sys
import requests
import uuid

import boto3
import botocore 

from pprint import pprint as pretty
import json
import random

from datetime import datetime

from GeoUtils import GeoUtils 
from Config import state
from cms import ConnectedMobility
from Cognito import Cognito

log = logging.getLogger('deploy.cf.create_or_update')  # pylint: disable=C0103

def get_value(data,lookup):  # Or whatever definition you like
    res = data
    for item in lookup:
        res = res[item]
    return res

def replace_value(data, lookup, value):
    obj = get_value(data, lookup[:-1])
    obj[lookup[-1]] = value
  

def main(profile, stackname, vin, city, state, username, password):
    #print("Creating the simulation %s " % cognitoId)

   g = GeoUtils()
   c = Cognito(profile)
   m = ConnectedMobility(profile, stackname)
 
   authToken = c.authenticateCognitoUser(username, password, m.userPoolId, m.userPoolClientId) 
   
   #send a single payload of data:
   data_filename = 'payload.json'
   with open(data_filename) as f:
    data = json.load(f)
   
   lookupLat = ['GeoLocation','Latitude']
   lookupLong = ['GeoLocation','Longitude']
   
   #get city lat long
   place = g.createPlaceObject(city, state)
   
   replace_value(data,lookupLat,float(place["latitude"]))
   replace_value(data,lookupLong,float(place["longitude"]))
   
   replace_value(data, ['MessageId'], vin + '-' + str(datetime.now()))
   print(data)
   exit()
           
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--profile", action="store", dest="profile", default=None, help="AWS CLI profile")
    parser.add_argument("-s", "--stackname", action="store", dest="stackname", default=None, help="AWS Stack Name for CMS")
    parser.add_argument("-u", "--username", action="store", dest="username", help="Username to log into CMS")
    parser.add_argument("-pwd", "--password", action="store", dest="password", default=None, help="Password for CMS User")
    parser.add_argument("-c", "--city", action="store", dest="city", help="City to start the journey")
    parser.add_argument("-st", "--state", action="store", dest="state", default=None, help="State to start the journey")
    parser.add_argument("-v", "--VIN", action="store", dest="vin", default=None, help="VIN for vehicle")
    
    args = parser.parse_args()

    main(args.profile, args.stackname, args.vin, args.city, args.state, args.username, args.password)