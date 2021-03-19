#!/usr/bin/env python3
import argparse
import logging
import json
import sys
import requests
import uuid
import os
from urllib.request import urlopen
from provisioningHandler import ProvisioningHandler
from utils.config_loader import Config

import boto3
import botocore 

from pprint import pprint as pretty
import json
import random

from datetime import datetime
from cognitoHandler import Cognito
from iotHandler import IOT

from cmsHandler import ConnectedMobility

#external constants
cdfStackName = 'CDF'
cmsStackName = 'CMS'
authStackName = 'Authorizer'
assetLibraryUrl = 'AssetLibraryApiGatewayUrl'
facadeApiGatewayUrl = 'FacadeApiGatewayUrl'
cfUuserPoolClientId = 'UserPoolClientId'
cfUserPoolId = "UserPoolId"
cfCertficateId = 'CertificateId'

#CF Constants
cflogResourceId = 'LogicalResourceId'
cfphyResourceId = 'PhysicalResourceId'
cfStackResources = 'StackResources'
cfStacks = 'Stacks'
cfOutputs = 'Outputs'
cfOutputKey = 'OutputKey'
cfOutputValue = 'OutputValue'

#Variables to be populated from CMS/CDF CF 
assetLibraryBaseUrl = None
facadeEndpointUrl = None
simulationEndpiontUrl = None
certificateId = None
cognitoId = None
userPoolClientId = None
userPoolId = None

#session = boto3.Session(profile_name = profile)

log = logging.getLogger('deploy.cf.create_or_update')  # pylint: disable=C0103

# Provided callback for provisioning method feedback.
def callback(payload):
    print(payload)
    
def main(profile, stackname, cdfstackname, vin, firstname, lastname, username, password, skip, csr):
    
   #Set Config path
   CONFIG_PATH = 'config.ini'

   config = Config(CONFIG_PATH)
   config_parameters = config.get_section('SETTINGS')
   secure_cert_path = config_parameters['SECURE_CERT_PATH']
   bootstrap_cert = config_parameters['CLAIM_CERT']
   root_cert_url = config_parameters['AWS_ROOT_CERT_URL']
   root_cert = config_parameters['ROOT_CERT']
   root_cert_path = config_parameters['ROOT_CERT_PATH']
   default_role_name = config_parameters['DEFAULT_ROLE_NAME']
   default_role_arn = config_parameters['POLICY_ARN_IOT']
   deviceMaker = config_parameters['DEVICE_MAKER']
   provisioning_template_name = config_parameters['PROVISIONING_TEMPLATE_NAME']
   provisioning_template_description = config_parameters['PROVISIONING_TEMPLATE_DESCRIPTION']
   provisioning_policy_file_name = config_parameters['POLICY_JSON']
   provisioning_template_file_name = config_parameters['TEMPLATE_JSON']
   provisioning_policy_name = config_parameters['PROVISIONING_POLICY_NAME']
   
   externalId = uuid.uuid4().hex
   thingName = vin

   c = Cognito(profile)
   m = ConnectedMobility(profile, stackname, cdfstackname)
   i = IOT(profile, default_role_name, default_role_arn, CONFIG_PATH)   
   provisioner = ProvisioningHandler(CONFIG_PATH, provisioning_template_name, thingName, i.iotEndpoint)
   
   #begin setting up device certificates for this thing
   #We will use fleet provisioning to take a bootstrap certificate, this bootstrap certificate is allowed to connect to specific topics that will allow for the creation
   #of the permananet certificate.  The permanent certificate is then downloaded to the /certs folder and used to connect to the telemetry topics 
   print("Setting up provisioning templates.")
   if skip is not True:
    i.setupProvisioningTemplate(
        provisioning_template_name,
        provisioning_template_description, 
        provisioning_template_file_name, 
        provisioning_policy_name, 
        provisioning_policy_file_name)
   
   if not c.checkCognitoUser(username,m.userPoolId):
     print("Creating user ...")
     c.createCognitoUser(username, password, m.userPoolId, m.userPoolClientId)
     
   print("Logging in user ...")
   authorization = c.authenticateCognitoUser(username, password, m.userPoolId, m.userPoolClientId)
 
   #check to see if supplier exists, otherwise create a new one.
   response = m.getSupplier(deviceMaker, authorization)
   
   if response.status_code != 200:   
       print("Creating supplier ...")
       response = m.createSupplier(deviceMaker = deviceMaker, GUID = externalId, authorization = authorization)
       if response.status_code == 204:
           print("Vehicle Supplier created successfully...")
       else:
           print("Error creating vehicle supplier.  Exiting. Error: %s", response)
           exit()
   else: 
       #get externalId from existing supplier
       data = json.loads(response.text)  
       externalId = data["attributes"]["externalId"]
   
   print("Creating CMS User ...") 
   response = m.createCMSUser(firstName = firstname, lastName = lastname, username = username, authorization = authorization)
   
   if response.status_code == 201 or response.status_code == 204:
       print("CMS User created successfully...")
   else:
       print("Error creating CMS User.  May currently exist, who knows, there's no method to check.")

   #create provisioning certificate
   print("Creating provisioning certificates and writing to local directory.")
   certificateArn = i.createProvisioningCertificate(True, provisioning_template_name, vin)
   print("Certificates created successfully")
   #attach the new certificate to the policy already created
   print("Attaching the boostrap policy to the certificate")
   i.attachPolicyToCertificate(provisioning_policy_name, certificateArn)
   print("Policy attached successfully")
   if csr is True:
      i.createCertificateSigningRequest(True, vin, common_name=vin, country=None, state=None, city=None,
              organization=None, organizational_unit=None, email_address=None)
       
   try: #to get root cert if it does not exist    
        print("Getting root certificate")
        root_path = "{}/{}".format( root_cert_path, root_cert)
        if not os.path.exists( root_path):
            response = urlopen(root_cert_url)
            content = response.read().decode('utf-8')
            with open(root_path, "w" ) as f:
                f.write( content )
                f.close()
   except Exception as e:
            print(e)
            exit()
   print("Root certificate downloaded to certificates directory.")
   #try:
   if csr is not True:
    print("{}/{}".format(secure_cert_path.format(unique_id=vin), bootstrap_cert))
    with open("{}/{}".format(secure_cert_path.format(unique_id=vin), bootstrap_cert), 'r') as f:
        # Call super-method to perform aquisition/activation
        # of certs, association of thing, etc. Returns general
        # purpose callback at this point.
        # Instantiate provisioning handler, pass in path to config
       provisioner.get_official_certs(callback, None, None)
   else: 
       provisioner.get_official_certs(callback, vin, 'csr-bootstrap.csr')
   #except IOError:
   #     print("### Bootstrap cert non-existent. Official cert may already be in place.")          

   print("Registering Device ...")          
   response = m.registerDevice(externalId, thingName, authorization, provisioner.CertificateId)
   
   if response.status_code == 200 or response.status_code == 204 or response.status_code == 201:
       print("Device registered successfully...")
   elif response.status_code == 409:
       print("Device already registered.  Will attempt to activate the device...")
   else:
       print(response)
       print("Error registering the device.  Exiting.")
       exit()
      
   response = m.activateDevice(deviceMaker = deviceMaker, externalId = externalId, thingName = thingName, vin = vin, authorization = authorization)
   
   if response.status_code == 204:
       print("Device activated successfully...")
   else:
       print("Error activating device.  Exiting.")
       exit()
   
   response = m.associateDevice(username = username, vin = vin, authorization = authorization) 
   
   if response.status_code == 204 or response.status_code == 200:
       print("Device associated successfully...")
       print("External ID: {}".format(externalId))
       print("Thing Name: {}".format(thingName))
   else:
       print("Error associating device to user.  Exiting.")
       exit()    
       
   print("Vehicle setup sucessfully, please visit http://{} to login with your user and see your vehicle".format(m.cloudFrontDomainUrl))            

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--profile", action="store", dest="profile", default=None, help="AWS CLI profile that has admin access to your CMS stack")
    parser.add_argument("-s", "--stackName", action="store", dest="stackname", default=None, help="Name given to your CMS stack")
    parser.add_argument("-c", "--CDFstackName", action="store", dest="cdfstackname", default=None, help="Name given to your CDF stack (cdf-core-{cms stack name}")
    parser.add_argument("-v", "--VIN", action="store", dest="vin", default=None, help="VIN for your vehicle")
    parser.add_argument("-f", "--FirstName", action="store", dest="firstname", help="First Name for CMS User")
    parser.add_argument("-l", "--LastName", action="store", dest="lastname", default=None, help="Last Name for CMS User")
    parser.add_argument("-u", "--Username", action="store", dest="username", help="Username to log into CMS")
    parser.add_argument("-pwd", "--Password", action="store", dest="password", help="Password to log into CMS")
    parser.add_argument("-skip", "--SkipSetupProvisioningTemplates", action="store_true", dest="skip", default=False, help="Skip setup of fleet provisioning template")
    parser.add_argument("-csr", "--GenerateCSR", action="store_true", dest="csr", default=False, help="Register with CSR?")
    
    args = parser.parse_args()

    if args.profile and args.stackname and args.cdfstackname and args.vin and args.firstname and args.lastname and args.username and args.password:
        main(args.profile, args.stackname, args.cdfstackname, args.vin, args.firstname, args.lastname, args.username, args.password, args.skip, args.csr)
    else:
        print('[Error] Missing arguments..')
        parser.print_help()
        
