#!/usr/bin/env python3
import argparse
import logging
import json
import boto3
import botocore 
import time
import sys
import threading
from awsiot import mqtt_connection_builder
from awscrt import io, mqtt, auth, http
from iotHandler import IOT



#io.init_logging(getattr(io.LogLevel, 'INFO'), 'stderr')

received_count = 0
received_all_event = threading.Event()

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_count
    received_count += 1
    if received_count == 10:
        received_all_event.set()

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
    CLIENT_ID = "LSH14J4C4KA097019"
    PATH_TO_CERT = "certs/c18f164ef1-certificate.pem.crt"
    PATH_TO_KEY = "certs/c18f164ef1-private.pem.key"
    PATH_TO_ROOT = "certs/root.ca.pem"
    MESSAGE = "Hello World"
    TOPIC = "test"
    RANGE = 20

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
    
            
    print("Connecting with Prod certs to {} with client ID '{}'...".format(ENDPOINT,CLIENT_ID))
    connect_future = test_MQTTClient.connect()
    # Future.result() waits until a result is available
    connect_future.result()

    print("Connected with Prod certs!")
    #time.sleep(10)
    new_cert_topic = "dt/cvra/{deviceid}/cardata".format(deviceid=CLIENT_ID)
    #new_cert_topic = TOPIC
    print("Subscribing to topic '{}'...".format(new_cert_topic))
    mqtt_topic_subscribe_future, _ = test_MQTTClient.subscribe(
        topic=new_cert_topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)

    # Wait for subscription to succeed
    mqtt_topic_subscribe_result = mqtt_topic_subscribe_future.result()
    print("Subscribed with {}".format(str(mqtt_topic_subscribe_result['qos'])))

    publish_count = 1
    while (publish_count <= 10):
        message = "{} [{}]".format("test", publish_count)
        print("Publishing message to topic '{}': {}".format(new_cert_topic, message))
        test_MQTTClient.publish(
            topic=new_cert_topic,
            payload=message,
            qos=mqtt.QoS.AT_LEAST_ONCE)
        time.sleep(1)
        publish_count += 1

    # Wait for all messages to be received.
    # This waits forever if count was set to 0.
    if not received_all_event.is_set():
        print("Waiting for all messages to be received...")

    received_all_event.wait()
    print("{} message(s) received.".format(received_count))

    # Disconnect
    print("Disconnecting...")
    disconnect_future = test_MQTTClient.disconnect()
    disconnect_future.result()
    print("Disconnected!")

        
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