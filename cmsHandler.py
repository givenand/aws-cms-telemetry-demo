import boto3
import requests

from utils.config_loader import Config

class ConnectedMobility():
    #external constants
    cdfStackName = 'CDF'
    cmsStackName = 'CMS'
    authStackName = 'Authorizer'
    assetLibraryUrl = 'AssetLibraryApiGatewayUrl'
    facadeApiGatewayUrl = 'FacadeApiGatewayUrl'
    cfUuserPoolClientId = 'UserPoolClientId'
    cfUserPoolId = 'UserPoolId'
    cfCertficateId = 'CertificateId'
    CONFIG_PATH = 'config.ini'
    config = Config(CONFIG_PATH)
    config_parameters = config.get_section('SETTINGS')
    cAcceptHeader = config_parameters['ACCEPT_HEADER']
    cContentType = config_parameters['CONTENT_TYPE']
        
    #CF Constants
    cflogResourceId = 'LogicalResourceId'
    cfphyResourceId = 'PhysicalResourceId'
    cfStackResources = 'StackResources'
    cfStacks = 'Stacks'
    cfOutputs = 'Outputs'
    cfOutputKey = 'OutputKey'
    cfOutputValue = 'OutputValue'
    
    __assetLibraryBaseUrl = ''
    __cmscfResourcesArn = ''
    __cognitoId = ''
    __userPoolClientId = ''
    __userPoolId = ''
    __facadeEndpointUrl = ''
    __certificateId = ''
    __cdf_stackARN = ''
    __cdf_cf = {}
    __cdf_outputs = {}
    __cdfSubstackOutputs = {}
    __cf = None
    session = None
        
    def __init__(self, profile, stackname):
        self.profile = profile
        self.stackname = stackname
        self.session = boto3.Session(profile_name = profile)
        
        super().__init__()
    
    @property    
    def cf(self):
        if self.__cf == None: 
            self.__cf = self.session.client('cloudformation')
        return self.__cf
    @property
    def cdf_cf(self):
        if not self.__cdf_cf: 
            self.__cdf_cf = self.cf.describe_stacks(StackName=self.stackname)[self.cfStacks]
        return self.__cdf_cf
    @property
    def cdfOutputs(self):
        if not self.__cdf_outputs:
            self.__cdf_outputs = self.cdf_cf[0][self.cfOutputs]
        return self.__cdf_outputs
    @property
    def cdfStackARN(self):
        if not self.__cdf_stackARN:
            self.__cdf_stackARN = self.getValuefromResourceDict(self.cf.describe_stack_resources(StackName=self.stackname)[self.cfStackResources], self.cdfStackName)
        return self.__cdf_stackARN
    @property
    def cdfSubstackOutputs(self):
        if not self.__cdfSubstackOutputs: 
            self.__cdfSubstackOutputs = self.cf.describe_stacks(StackName=self.cdfStackARN)[self.cfStacks][0][self.cfOutputs]
        return self.__cdfSubstackOutputs
    @property
    def assetLibraryBaseUrl(self):
        if self.__assetLibraryBaseUrl == '':
            self.__assetLibraryBaseUrl = self.getValuefromDict(self.cdfSubstackOutputs, self.assetLibraryUrl)      
        return self.__assetLibraryBaseUrl
    @property
    def facadeEndpointUrl(self):
        if self.__facadeEndpointUrl == '':
            self.__facadeEndpointUrl = self.getValuefromDict(self.cdfOutputs, self.facadeApiGatewayUrl)
        return self.__facadeEndpointUrl
    @property
    def certificateId(self):
        if self.__certificateId == '':
            self.__certificateId = self.getValuefromDict(self.cdfOutputs, self.cfCertficateId)
        return self.__certificateId
    def cognitoId(self):
        return self.__cognitoId
    @property
    def userPoolClientId(self):
        if not self.__userPoolClientId:
            self.__userPoolClientId = self.getValuefromDict(self.cdfOutputs, self.cfUuserPoolClientId)
        return self.__userPoolClientId
    @property
    def userPoolId(self):
        if self.__userPoolId == '':
            self.__userPoolId = self.getValuefromDict(self.cdfOutputs, self.cfUserPoolId)
        return self.__userPoolId
    
    def getValuefromDict(self, vals, keyValName):
        v = next(filter(lambda output: output[self.cfOutputKey] == keyValName, vals))
        return (v[self.cfOutputValue])
    
    def getValuefromResourceDict(self, vals, keyValName):
        v = next(filter(lambda output: output[self.cflogResourceId] == keyValName, vals))
        return (v[self.cfphyResourceId])   
             
    def getSupplier(self, deviceMaker, authorization) -> None:
        #TODO://create function to general the path
        url = self.assetLibraryBaseUrl + "/groups/%2Fauto%2Fsuppliers%2F{0}"
        url = url.format(deviceMaker)
        payload = {} # payload.format(deviceMaker, deviceMaker, GUID)
    
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }
        
        response = requests.request("GET", url, headers=headers, data=payload)

        return response

    def createSupplier(self, deviceMaker, GUID, authorization) -> None:
        
        url = self.assetLibraryBaseUrl + "/groups"
        payload='{{\n    \"groupPath\" : \"/auto/suppliers/{0}\",\n    \"parentPath\" : \"/auto/suppliers\",\n    \"templateId\" : \"auto_supplier\",\n    \"name\" : \"{1}\",\n    \"attributes\" : {{\n        \"externalId\": \"{2}\"\n    }}\n}}'
        payload = payload.format(deviceMaker, deviceMaker, GUID)
        
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)

        return response

    def getCMSUser(self, firstName, lastName, username, authorization) -> None:
        url = self.facadeEndpointUrl + "/users"

        payload="{{\n    \"username\" : \"{0}\",\n    \"firstName\" : \"{1}\",\n    \"lastName\" : \"{2}\"\n}}"
        payload = payload.format(firstName, lastName, username)
        
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)

        return response

    def createCMSUser(self, firstName, lastName, username, authorization) -> None:
        url = self.facadeEndpointUrl + "/users"

        payload="{{\n    \"username\" : \"{0}\",\n    \"firstName\" : \"{1}\",\n    \"lastName\" : \"{2}\"\n}}"
        payload = payload.format(username, firstName, lastName)
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        return response

    def registerDevice(self, externalId, thingName, authorization) -> None:
        url = "{0}/suppliers/{1}/devices/{2}/register"
        url = url.format(self.facadeEndpointUrl, externalId, thingName)
        payload="{{\n    \"templateId\":\"auto_ecu\",\n    \"certificateId\": \"{0}\",\n    \"attributes\": {{\n        \"type\":\"tcu\",\n        \"model\":\"TCU-1\"\n    }}\n}}"
        payload = payload.format(self.certificateId)
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        return response
    
    def activateDevice(self, externalId, thingName, vin, authorization) -> None:
        url = "{0}/suppliers/{1}/devices/{2}/activate"
        url = url.format(self.facadeEndpointUrl, externalId, thingName)
        payload = payload='{{\n    \"vehicle\": {{\n        \"make\": \"DENSO\",\n        \"model\": \"DN\",\n        \"modelYear\": 2019,\n        \"marketCode\": \"NA\",\n        \"vin\": \"{0}\",\n        \"bodyType\": \"Saloon\",\n        \"fuelType\": \"Gas\",\n        \"transmissionType\": \"Auto\",\n        \"transmissionAutoType\": \"7-speed\",\n        \"colorCode\": \"B1B!\",\n        \"iviType\": \"Premium\",\n        \"ecus\": [{{\n            \"type\": \"tcu\",\n            \"id\": \"{1}\",\n            \"softwareVersion\": \"1.9.1\"\n        }}]\n    }}\n}}'
        payload = payload.format(vin, thingName)
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)

        return response

    def associateDevice(self, username, vin, authorization) -> None: 
        url = "{0}/groups/{1}{2}/owns/groups/{3}{4}"
        url = url.format(self.assetLibraryBaseUrl,"%2Fauto%2Fusers%2F", username, '%2Fauto%2Fvehicles%2F', vin)
        payload={}
        headers = {
            'Authorization': authorization,
            'Accept': self.cAcceptHeader,
            'Content-Type': self.cContentType
        }  
        response = requests.request("PUT", url, headers=headers, data=payload)

        return response
