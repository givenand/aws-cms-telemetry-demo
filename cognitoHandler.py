import boto3

class Cognito():
    client = None
    
    def __init__(self, profile):
        self.session = boto3.Session(profile_name = profile)
        self.client = self.session.client('cognito-idp')
        super().__init__()
        
    def checkCognitoUser(self, username: str, 
                    user_pool_id: str) -> None:
        
        # initial sign up
        try:
            resp = self.client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=username
            )
        except self.client.exceptions.UserNotFoundException as e:
            print(e)
            #if e == 'UserNotFoundException':
            return False
        if resp:
            return True
            
    def authenticateCognitoUser(self, username: str, password: str, 
                                user_pool_id: str, app_client_id: str) -> None:
        respUpdate = self.client.update_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=app_client_id,
            ExplicitAuthFlows=['ADMIN_NO_SRP_AUTH','USER_PASSWORD_AUTH']
        )
        
        if respUpdate:
            respInitiate = self.client.admin_initiate_auth(
                UserPoolId=user_pool_id,
                ClientId=app_client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password
                }
            )

        if respInitiate:
            print("Log in success")
        else:
            exit()
            
        return respInitiate['AuthenticationResult']['IdToken']

    def createCognitoUser(self, username: str, password: str, 
                    user_pool_id: str, app_client_id: str) -> None:
        #modify user pool to allow user signup
        respUpdate = self.client.update_user_pool(
            UserPoolId=user_pool_id,
            AdminCreateUserConfig=
                {
                'AllowAdminCreateUserOnly': False,
                }
        )
        if respUpdate:
         # initial sign up
            respSignup = self.client.sign_up(
                ClientId=app_client_id,
                Username=username,
                Password=password,
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': 'test@test.com'
                    },
                ]
            )
        if respSignup:
            # then confirm signup
            respConfirm = self.client.admin_confirm_sign_up(
                UserPoolId=user_pool_id,
                Username=username
            )    
            if respConfirm: return True
        else:
            return False