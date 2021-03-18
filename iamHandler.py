import boto3
from botocore.exceptions import ClientError

import json

class IAM():
    session = None
    client = None 
         
    def __init__(self, profile):

        self.session = boto3.Session(profile_name = profile)
        self.client = self.session.client('iam')
        super().__init__()
        
    def describeRole(self, roleName):
        try:
            describe_role_res = self.client.get_role(
                RoleName=roleName
            )
            
            return describe_role_res
        except ClientError as error:
            if error.response['Error']['Code'] == 'NoSuchEntity':
                return 'NoSuchEntity'
            else:
                return 'Unexpected error occurred... Role could not be created', error
            
    def createRole(self, policyArn,roleName, description):
        try:
            #open the 
            #with open('assets/' + payloadJsonFileName) as f:
            #    role = json.load(f)

            create_role_res = self.client.create_role(
                RoleName=roleName,
                AssumeRolePolicyDocument=json.dumps(role),
                Description=description
            )
            
            return create_role_res
        except ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                return 'Role already exists... hence exiting from here'
            else:
                return 'Unexpected error occurred... Role could not be created', error
            
    def attachPolicy(self, roleName, policyArn):
        try:
            attachpolicy_res = self.client.attach_role_policy(
                RoleName=roleName,
                PolicyArn=policyArn
            )
            
            return attachpolicy_res
        except ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                return 'Role already exists... hence exiting from here'
            else:
                return 'Unexpected error occurred... Role could not be created', error
            
    
            