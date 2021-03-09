import boto3
from botocore.exceptions import ClientError
import logging
import os
from utils.config_loader import Config
from iamHandler import IAM
import json
import time

class IOT():
    __client = None 
    __iam = None
         
    def __init__(self, profile, roleName, policyArn, file_path):
        
         #Logging
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger(__name__)
        
        config = Config(file_path)
        self.config_parameters = config.get_section('SETTINGS')
        self.secure_cert_path = self.config_parameters['SECURE_CERT_PATH']
        
        self.profile = profile
        self.session = boto3.Session(profile_name = profile)
        self.client = self.session.client('iot')
        #self.boto3.client('sts').get_caller_identity().get('Account')
        self.iam = IAM(profile)
        self.roleName = roleName
        self.policyArn = policyArn
        super().__init__()
        
    @property    
    def client(self):
        if self.__client == None: 
            self.__client = self.session.client('iot')
        return self.__client
    @client.setter 
    def client(self, val):
        self.__client = val
        
    @property    
    def iam(self):
        if self.__iam == None: 
            self.__iam = IAM(self.profile)
        return self.__iam
    @iam.setter 
    def iam(self, val):
        self.__iam = val
    @property
    def iotEndpoint(self):
        return self.client.describe_endpoint(endpointType='iot:Data-ATS')['endpointAddress']        
    @property
    def certificateArn(self):
        return self.__certificateArn
    @certificateArn.setter 
    def certificateArn(self, carn):
        self.__certificateArn = carn
    
    @property
    def PublicKey(self):
        return self.__publicKey
    @PublicKey.setter 
    def PublicKey(self, val):
        self.__publicKey = val
    
    @property
    def PrivateKey(self):
        return self.__privateKey
    @PrivateKey.setter 
    def PrivateKey(self, val):
        self.__privateKey = val
            
    @property
    def CertificatePem(self):
        return self.__certificatePem
    @CertificatePem.setter 
    def CertificatePem(self, val):
        self.__certificatePem = val
    
    @property
    def CertificateId(self):
        return self.__certificateId
    @CertificateId.setter 
    def CertificateId(self, val):
        self.__certificateId = val
        
    @property
    def roleName(self):
        return self.__roleName
    @roleName.setter 
    def roleName(self, val):
        self.__roleName = val
    
    @property
    def roleArn(self):
        return self.__roleArn
    @roleArn.setter 
    def roleArn(self, val):
        self.__roleArn= val

    @property
    def provisioningTemplateArn(self):
        return self.__provisioningTemplateArn
    @provisioningTemplateArn.setter 
    def provisioningTemplateArn(self, val):
        self.__provisioningTemplateArn= val
                
    @property
    def policyArn(self):
        return self.__policyArn
    @policyArn.setter 
    def policyArn(self, val):
        self.__policyArn= val
    def attachPolicyToCertificate(self, policyName, certificateArn):
        try:
            response = self.client.attach_policy(
                policyName = policyName,
                target = certificateArn
            )
            
            return response
        except ClientError as error:
            if error.response['Error']['Code'] == 'NoSuchEntity':
                return 'NoSuchEntity'
            else:
                return 'Unexpected error occurred... Role could not be created', error
            

    def attachIoTPolicytoRole(self):
        resp_attach = self.iam.attachPolicy(self.roleName, self.policyArn)
        return resp_attach
    def getPolicy(self, policyName):
        try:
            describe_policy_res = self.client.get_policy(
                policyName=policyName
            )
            
            return describe_policy_res
        except ClientError as error:
            if error.response['Error']['Code'] == 'ResourceNotFoundException':
                return 'ResourceNotFoundException'
            else:
                return 'Unexpected error occurred... Role could not be created', error
            
    def getProvisioningPolicy(self, templateName):
        try:
            response = self.client.describe_provisioning_template(templateName=templateName)
            return response['templateArn']
        except ClientError as error:
        #resource does not exist
            if error.response['Error']['Code'] == 'ResourceNotFoundException':
                return 'ResourceNotFoundException'
            else:
                return 'Unexpected error occurred... Error finding policy', error
   
    def createProvisioningPolicy(self, policyName, provisioningTemplateName, payloadJsonFileName):
        try:
            version = None
            response = self.getPolicy(policyName)
            if response != 'ResourceNotFoundException':
                version = response['defaultVersionId']
              
            #open the json
            with open('assets/' + payloadJsonFileName) as f:
                policy = json.load(f)

            accountId = self.session.client('sts').get_caller_identity().get('Account')
            region = self.session.region_name
            
            policyF = json.dumps(policy).replace("$REGION", region).replace("$ACCOUNT", accountId).replace("$PROVTEMPLATE",provisioningTemplateName )
                        
            if version is not None:   
                #print(version) 
                self.client.delete_policy_version(
                    policyName=policyName,
                    policyVersionId=version
                )
                
                #update or create a new version but set this version as default as it refers to a new provisioning template
                create_policy_res = self.client.create_policy_version(
                    policyName=policyName,
                    policyDocument=policyF,
                    setAsDefault= True
                )
            else:
                #update or create a new version but set this version as default as it refers to a new provisioning template
                #print(json.dumps(policyF))
                create_policy_res = self.client.create_policy(
                    policyName=policyName,
                    policyDocument=policyF
                )
                
                
            return create_policy_res
        except ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                return 'Policy already exists... hence exiting from here'
            else:
                return 'Unexpected error occurred... Role could not be created', error        
    def createProvisioningPolicyRole(self):
        response = self.iam.describeRole(self.roleName)  
        if response == 'NoSuchEntity':
            policy_res = self.iam.createRole('iotRoleTrust.json',self.roleName, 'Iot Services Trust role')
            print(policy_res)
            if policy_res =='Role already exists... hence exiting from here' or policy_res == 'Unexpected error occurred... Role could not be created':
                return 'Error'
            else:
                self.roleArn = policy_res['Role']['Arn']
        else:
            self.roleArn = response['Role']['Arn']
        return self.roleArn
    
    def createIoTProvisioningTemplate(self, templateName, templateDescription, provisioningRoleArn, payloadJsonFileName):
        #no API in boto if the provisioning template exsists??
        try:
            with open('assets/' + payloadJsonFileName) as f:
                template = json.load(f)

            prov_template_resp = self.client.create_provisioning_template(
                templateName=templateName,
                description=templateDescription,
                templateBody=json.dumps(template),
                enabled=True,
                provisioningRoleArn=provisioningRoleArn
            )
        
            return prov_template_resp['templateArn']
        except ClientError as error:
            if error.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                return 'ResourceAlreadyExistsException'
            else:
                return 'Unexpected error occurred... Template could not be created', error
            
    def setupProvisioningTemplate(self, 
                                  provisioningTemplateName, 
                                  templateDescription, 
                                  templatePayloadJsonFileName, 
                                  policyName, 
                                  policyPayloadJsonFileName,
                                  vin):
        #first check if policy exists
        print("Check for existing provisioning policy...")
        response_prov_policy = self.getProvisioningPolicy(provisioningTemplateName)
        if response_prov_policy != 'ResourceNotFoundException':
            print("Error occured:  The template currently exists and cannot create another with the same name.  Please change the name and try again")
            exit()
        
        print("Creating the provisioning policy role...")
        #then create the role the policy can be attached to
        self.createProvisioningPolicyRole()
        print("Created Role.")
        #attach the role to the iot base service role
        print("Attaching base IoT Policy to role...")
        self.attachIoTPolicytoRole()
        time.sleep(5)
        print("Attached.")
        #create the policy
        print("Creating the policy associated with the provisioning template bootstrap...")
        policy_response = self.createProvisioningPolicy(policyName, provisioningTemplateName, policyPayloadJsonFileName)
        print(policy_response)
        print("Bootstrap Policy successfully created.")
        #create the provisioningtemplate
        print("Creating Fleet Provisioning Template...")
        time.sleep(10)
        response_provisioning = self.createIoTProvisioningTemplate(provisioningTemplateName, templateDescription, self.roleArn, templatePayloadJsonFileName)
        if response_provisioning == 'ResourceAlreadyExistsException':
            return "Error occured:  The template currently exists and cannot create another with the same name.  Please change the name and try again"
        else: 
            print(response_provisioning)
            self.provisioningTemplate = response_provisioning
            print("Provisioning Template successfully created.")      

        #create provisioning certificate
        print("Creating provisioning certificates and writing to local directory...")
        self.createProvisioningCertificate(True, provisioningTemplateName, vin)
        print("Certificates created successfully")
        #attach the new certificate to the policy already created
        print("Attaching the boostrap policy to the certificate")
        self.attachPolicyToCertificate(policyName, self.certificateArn)
        print("Policy attached successfully")
        return True
    def describeProvisioningTemplate(self, provisioningTemplateName):
        return self.client.describe_provisioning_template(templateName=provisioningTemplateName)
    def createProvisioningCertificate(self, writeToFile, provisi, vin):
        try:
            certResponse = self.client.create_keys_and_certificate(
                    setAsActive = True
            )
            
            data = json.loads(json.dumps(certResponse, sort_keys=False, indent=4))
            for element in data: 
                    if element == 'certificateArn':
                            self.certificateArn = data['certificateArn']
                    elif element == 'keyPair':
                            self.PublicKey = data['keyPair']['PublicKey']
                            self.PrivateKey = data['keyPair']['PrivateKey']
                    elif element == 'certificatePem':
                            self.certificatePem = data['certificatePem']
                    elif element == 'certificateId':
                            self.certificateId = data['certificateId']
            
            if writeToFile:
                path = self.secure_cert_path.format(unique_id=vin)                         
                os.makedirs(path.format(unique_id=vin), exist_ok=True) 
    
                with open(path + '/bootstrap-public.pem.key', 'w') as outfile:
                        outfile.write(self.PublicKey)
                with open(path + '/bootstrap-private.pem.key', 'w') as outfile:
                        outfile.write(self.PrivateKey)
                with open(path + '/bootstrap-certificate.pem.crt', 'w') as outfile:
                        outfile.write(self.certificatePem)

            print('certificateId: %s', self.certificateId)
            #TODO://make sure this worked
        except ClientError as error: 
            return error   
