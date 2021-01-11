#!/usr/bin/env python3
import argparse
import logging
import json
import boto3
import botocore 
from awsiot import mqtt_connection_builder
from awscrt import io, mqtt, auth, http
from iotHandler import IOT

def basic_callback(self, topic, payload, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    message_payload = payload

    if topic == "dt/cvra/{deviceid}/cardata".format(deviceid=self.unique_id):
        # Finish the run successfully
        print("Successfully provisioned")
        self.callback_returned = True
    elif (topic == "$aws/provisioning-templates/{}/provision/json/rejected".format(self.template_name) or
        topic == "$aws/certificates/create/json/rejected"):
        print("Failed provisioning")
        self.callback_returned = True
            
def main():
    session = boto3.Session(profile_name = 'givenand-cms')
    client = session.client('iot')

    test_MQTTClient = None    
    
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    ENDPOINT = "a37l6rbyiqptbc-ats.iot.us-west-2.amazonaws.com"
    CLIENT_ID = "LSH14J4C4LA046495"
    PATH_TO_CERT = "certs/25faec7d39-certificate.pem.crt"
    PATH_TO_KEY = "certs/25faec7d39-private.pem.key"
    PATH_TO_ROOT = "certs/root.ca.pem"
    MESSAGE = "Hello World"
    TOPIC = "test/testing"
    RANGE = 20

    test_MQTTClient = mqtt_connection_builder.mtls_from_path(
        endpoint=ENDPOINT,
        cert_filepath=PATH_TO_CERT,
        pri_key_filepath=PATH_TO_KEY,
        client_bootstrap=client_bootstrap,
        ca_filepath=PATH_TO_ROOT,
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=6)
        
    print("Connecting with Prod certs to {} with client ID '{}'...".format(ENDPOINT,CLIENT_ID))
    connect_future = test_MQTTClient.connect()
    # Future.result() waits until a result is available
    connect_future.result()
    
    print("Connected with Prod certs!")

    new_cert_topic = "dt/cvra/{deviceid}/cardata".format(deviceid=CLIENT_ID)
    print("Subscribing to topic '{}'...".format(new_cert_topic))
    mqtt_topic_subscribe_future, _ = test_MQTTClient.subscribe(
        topic=new_cert_topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=basic_callback)

    # Wait for subscription to succeed
    mqtt_topic_subscribe_result = mqtt_topic_subscribe_future.result()
    print("Subscribed with {}".format(str(mqtt_topic_subscribe_result['qos'])))

    test_MQTTClient.publish(
        topic=new_cert_topic,
        payload=json.dumps({"service_response": "##### RESPONSE FROM PREVIOUSLY FORBIDDEN TOPIC #####"}),
        qos=mqtt.QoS.AT_LEAST_ONCE)
    

        
''' i = IOT('givenand-cms', "IotCMSRole", 'arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration')   
###    
#   try:
       response = client.describe_provisioning_template(templateName='CMSFleetProvisioningTemplate6')
       proTemplateArn = response['templateArn']
       print(proTemplateArn)
    except botocore.exceptions.ClientError as error:
       #resource does not exist, create one
       if error.response['Error']['Code'] == 'ResourceNotFoundException':
            i.setupProvisioningTemplate('CMSFleetProvisioningTemplate6', 'CMS Fleet Provisioning Template for Mobility entities', 'provisioningTemplatePolicy.json', 'fleetProvisioning', 'bootstrapCertificatePolicy.json')
           # log.warn('Creating new provisioning template...')
            print('here')
       pass 
    
    exit()
'''       
if __name__ == "__main__":
    main()