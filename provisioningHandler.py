#!/usr/bin/env python3

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
from utils.config_loader import Config
from payloadHandler import payloadHandler
import time
import uuid
import logging
import json 
import os
import asyncio
import glob
import sys

class ProvisioningHandler:

    def __init__(self, file_path, template_name, thing_name):
        """Initializes the provisioning handler
        
        Arguments:
            file_path {string} -- path to your configuration file
        """
        #Logging
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger(__name__)
        
        #Load configuration settings from config.ini
        config = Config(file_path)
        self.config_parameters = config.get_section('SETTINGS')
        self.secure_cert_path = self.config_parameters['SECURE_CERT_PATH']
        self.iot_endpoint = self.config_parameters['IOT_ENDPOINT']	
        self.template_name = template_name #self.config_parameters['PRODUCTION_TEMPLATE']
        self.rotation_template = self.config_parameters['CERT_ROTATION_TEMPLATE']
        self.claim_cert = self.config_parameters['CLAIM_CERT']
        self.secure_key = self.config_parameters['SECURE_KEY']
        self.root_cert = self.config_parameters['ROOT_CERT']
        self.root_cert_path = self.config_parameters['ROOT_CERT_PATH']
        self.topic_name = self.config_parameters['TOPIC_NAME']
        self.unique_id = thing_name

        self.primary_MQTTClient = None
        self.test_MQTTClient = None
        self.callback_returned = False
        self.message_payload = {}
        self.isRotation = False

        self.payloadhandler = payloadHandler(file_path)
    def core_connect(self):
        """ Method used to connect to AWS IoTCore Service. Endpoint collected from config.
        
        """
        if self.isRotation:
            self.logger.info('Connecting with Bootstrap certificate ')
            print('Connecting with Bootstrap certificate ')
            self.get_current_certs()
        else:
            self.logger.info('Connecting with Bootstrap certificate ')
            print('Connecting with Bootstrap certificate ')

        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
        path = self.secure_cert_path.format(unique_id=self.unique_id)
        print(path)
        self.primary_MQTTClient = mqtt_connection_builder.mtls_from_path(
            endpoint=self.iot_endpoint,
            cert_filepath="{}/{}".format(path, self.claim_cert),
            pri_key_filepath="{}/{}".format(path, self.secure_key),
            client_bootstrap=client_bootstrap,
            ca_filepath="{}/{}".format(self.root_cert_path, self.root_cert),
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
            client_id=self.unique_id,
            clean_session=False,
            keep_alive_secs=6)
        
        print("Connecting to {} with client ID '{}'...".format(self.iot_endpoint, self.unique_id))
        connect_future = self.primary_MQTTClient.connect()
        # Future.result() waits until a result is available
        connect_future.result()
        print("Connected!")
        
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
            
    def on_resubscribe_complete(self, resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))

    def get_current_certs(self):
        print('{}/[!boot]*.crt'.format(self.secure_cert_path.format(unique_id=self.unique_id)))
        path = self.secure_cert_path.format(unique_id=self.unique_id)
        non_bootstrap_certs = glob.glob('{}/[!boot]*.crt'.format(path))
        non_bootstrap_key = glob.glob('{}/[!boot]*.key'.format(path))

        #Get the current cert
        if len(non_bootstrap_certs) > 0:
            self.claim_cert = os.path.basename(non_bootstrap_certs[0])

        #Get the current key
        if len(non_bootstrap_key) > 0:
            self.secure_key = os.path.basename(non_bootstrap_key[0])
        
    def enable_error_monitor(self):
        """ Subscribe to pertinent IoTCore topics that would emit errors
        """

        template_reject_topic = "$aws/provisioning-templates/{}/provision/json/rejected".format(self.template_name)
        certificate_reject_topic = "$aws/certificates/create/json/rejected"
        
        template_accepted_topic = "$aws/provisioning-templates/{}/provision/json/accepted".format(self.template_name)
        certificate_accepted_topic = "$aws/certificates/create/json/accepted"

        subscribe_topics = [template_reject_topic, certificate_reject_topic, template_accepted_topic, certificate_accepted_topic]

        for mqtt_topic in subscribe_topics:
            print("Subscribing to topic '{}'...".format(mqtt_topic))
            mqtt_topic_subscribe_future, _ = self.primary_MQTTClient.subscribe(
                topic=mqtt_topic,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.basic_callback)

            # Wait for subscription to succeed
            mqtt_topic_subscribe_result = mqtt_topic_subscribe_future.result()
            print("Subscribed with {}".format(str(mqtt_topic_subscribe_result['qos'])))

    def get_official_certs(self, callback, isRotation=False):
        """ Initiates an async loop/call to kick off the provisioning flow.
            Triggers:
               on_message_callback() providing the certificate payload
        """
        if isRotation:
            self.template_name = self.rotation_template
            self.isRotation = True

        return asyncio.run(self.orchestrate_provisioning_flow(callback))

    async def orchestrate_provisioning_flow(self,callback):
        # Connect to core with provision claim creds
        self.core_connect()

        # Monitor topics for errors
        self.enable_error_monitor()

        # Make a publish call to topic to get official certs
        #self.primary_MQTTClient.publish("$aws/certificates/create/json", "{}", 0)

        self.primary_MQTTClient.publish(
            topic="$aws/certificates/create/json",
            payload="{}",
            qos=mqtt.QoS.AT_LEAST_ONCE)
        time.sleep(1)

        # Wait the function return until all callbacks have returned
        # Returned denoted when callback flag is set in this class.
        while not self.callback_returned:
            await asyncio.sleep(0)

        return callback(self.message_payload)

    def on_message_callback(self, payload):
        """ Callback Message handler responsible for workflow routing of msg responses from provisioning services.
        
        Arguments:
            payload {bytes} -- The response message payload.
        """
        json_data = json.loads(payload)
        
        # A response has been recieved from the service that contains certificate data. 
        if 'certificateId' in json_data:
            self.logger.info('Success. Saving keys to the device! ')
            print('Success. Saving keys to the device! ')
            self.assemble_certificates(json_data)
        
        # A response contains acknowledgement that the provisioning template has been acted upon.
        elif 'deviceConfiguration' in json_data:
            if self.isRotation:
                self.logger.info('Activation Complete ')
                print('Activation Complete')
            else:
                self.logger.info('Certificate Activated and device {} associated '.format(json_data['thingName']))
                print('ertificate Activated and device {} associated '.format(json_data['thingName']))

            self.validate_certs()
        elif 'service_response' in json_data:
            self.logger.info(json_data)
            print('Successfully connected with production certificates ')
        else:
            self.logger.info(json_data)

    def assemble_certificates(self, payload):
        """ Method takes the payload and constructs/saves the certificate and private key. Method uses
        existing AWS IoT Core naming convention.
        
        Arguments:
            payload {string} -- Certifiable certificate/key data.
        Returns:
            ownership_token {string} -- proof of ownership from certificate issuance activity.
        """
        ### Cert ID 
        cert_id = payload['certificateId']
        self.new_key_root = cert_id[0:10]

        os.makedirs(self.secure_cert_path.format(unique_id=self.unique_id), exist_ok=True) 
        
        self.new_cert_name = 'production-certificate.pem.crt' ##.format(self.new_key_root)
        ### Create certificate
        f = open('{}/{}'.format(self.secure_cert_path.format(unique_id=self.unique_id), self.new_cert_name), 'w+')
        f.write(payload['certificatePem'])
        f.close()
        

        ### Create private key
        self.new_key_name = 'production-private.pem.key' ##.format(self.new_key_root)
        f = open('{}/{}'.format(self.secure_cert_path.format(unique_id=self.unique_id), self.new_key_name), 'w+')
        f.write(payload['privateKey'])
        f.close()

        ### Extract/return Ownership token
        self.ownership_token = payload['certificateOwnershipToken']
        
        # Register newly aquired cert
        self.register_thing(self.unique_id, self.ownership_token)
    # Callback when the subscribed topic receives a message
    def on_message_received(self, topic, payload, **kwargs):
        print("Received message from topic '{}': {}".format(topic, payload))
        self.callback_returned = True
        
    def register_thing(self, serial, token):
        """Calls the fleet provisioning service responsible for acting upon instructions within device templates.
        
        Arguments:
            serial {string} -- unique identifer for the thing. Specified as a property in provisioning template.
            token {string} -- The token response from certificate creation to prove ownership/immediate possession of the certs.
            
        Triggers:
            on_message_callback() - providing acknowledgement that the provisioning template was processed.
        """
        if self.isRotation:
            self.logger.info('Validating expiration and activating certificate ')
            print('Validating expiration and activating certificate ')
        else:
            self.logger.info(' Activating Certificate and associating with device ')
            print('Activating Certificate and associating with device ')
                
        register_template = {"certificateOwnershipToken": token, "parameters": {"SerialNumber": serial}}
        
        #Register thing / activate certificate
        self.primary_MQTTClient.publish(
            topic="$aws/provisioning-templates/{}/provision/json".format(self.template_name),
            payload=json.dumps(register_template),
            qos=mqtt.QoS.AT_LEAST_ONCE)
        time.sleep(2)

    def validate_certs(self):
        """Responsible for (re)connecting to IoTCore with the newly provisioned/activated certificate - (first class citizen cert)
        """
        self.logger.info('Connecting with production certificate ')
        print('Connecting with production certificate ')
        self.cert_validation_test()
        self.new_cert_pub_sub()
        print("Activated and tested credentials ({}, {}). ".format(self.new_key_name, self.new_cert_name))
        print("Files saved to {} ".format(self.secure_cert_path.format(unique_id=self.unique_id)))
        print("Successfully provisioned")
        self.callback_returned = True

    def cert_validation_test(self):
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
        cpath = self.secure_cert_path.format(unique_id=self.unique_id)
        self.test_MQTTClient = mqtt_connection_builder.mtls_from_path(
            endpoint=self.iot_endpoint,
            cert_filepath="{}/{}".format(cpath, self.new_cert_name),
            pri_key_filepath="{}/{}".format(cpath, self.new_key_name),
            client_bootstrap=client_bootstrap,
            ca_filepath="{}/{}".format(self.root_cert_path, self.root_cert),
            client_id=self.unique_id,
            clean_session=False,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
            keep_alive_secs=6)
        
        print("Connecting with Prod certs to {} with client ID '{}'...".format(self.iot_endpoint, self.unique_id))
        connect_future = self.test_MQTTClient.connect()
        # Future.result() waits until a result is available
        connect_future.result()
        print("Connected with Prod certs!")

    def basic_callback(self, topic, payload, **kwargs):
        print("Received message from topic '{}': {}".format(topic, payload))
        self.message_payload = payload
        self.on_message_callback(payload)

        if topic == "dt/cvra/{deviceid}/cardata".format(deviceid=self.unique_id):
            # Finish the run successfully
            print("Successfully provisioned")
            self.callback_returned = True
        elif (topic == "$aws/provisioning-templates/{}/provision/json/rejected".format(self.template_name) or
            topic == "$aws/certificates/create/json/rejected"):
            print("Failed provisioning")
            self.callback_returned = True

    def new_cert_pub_sub(self):
        """Method testing a call to the basic telemetry topic (which was specified in the policy for the new certificate)
        """

        new_cert_topic = self.topic_name.format(deviceid=self.unique_id)
       # print("Subscribing to topic '{}'...".format(new_cert_topic))
       # mqtt_topic_subscribe_future, _ = self.test_MQTTClient.subscribe(
       #     topic=new_cert_topic,
       #     qos=mqtt.QoS.AT_LEAST_ONCE,
       #     callback=self.on_message_received)

        # Wait for subscription to succeed
        #mqtt_topic_subscribe_result = mqtt_topic_subscribe_future.result()
        print("Publishing initial payload to {}".format(new_cert_topic))
        tripId = uuid.uuid4().hex
        coords = self.payloadhandler.generateInitialCoordinatesFromCSV()
        payload = self.payloadhandler.getPayload( coords[0], tripId, self.unique_id)
        self.payloadhandler.publishPayload(self.test_MQTTClient, payload, self.unique_id)
        print("Published successfully!")
#        self.test_MQTTClient.publish(
#            topic=new_cert_topic,
#            payload=self.getPayload('payload.json'),
#            qos=mqtt.QoS.AT_LEAST_ONCE)

    def getPayload(self, payloadJsonFileName):
        with open('assets/' + payloadJsonFileName) as f:
                template = json.load(f)
        return json.dumps(template)