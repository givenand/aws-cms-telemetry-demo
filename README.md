# AWS CMS Enablement 

This repo contains several scripts necessary to automate the creation of devices in Connected Mobility Solution

```bash
./setupSingleVehicle.py --profile=givenand-cms --stackName=cms-dev1 --VIN=LSH14J4C4LA046511 --FirstName=Test --LastName=User --Username=testCMSUser1 --Password=Testing1234
```

# Requirements

1. The CMS CF was deployed succsesfully, please follow the instructions here: https://quip-amazon.com/hLrnALX7bgCd/Connected-Mobility-Solution-Getting-Started

```bash
pip install virtualenv
brew install pyenv-virtualenv

vim ~/.zshrc

# Setup virtualenv home
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# Tell pyenv-virtualenvwrapper to use pyenv when creating new Python environments
export PYENV_VIRTUALENVWRAPPER_PREFER_PYVENV="true"

# Set the pyenv shims to initialize
if command -v pyenv 1>/dev/null 2>&1; then
 eval "$(pyenv init -)"
fi

mkdir ~/.virtualenvs

pyenv global 3.6.12

pyenv virtualenv 3.6.12 CMS

pip install nvm

nvm install 12.18.2

nvm use 12.18.2 

npm install -g pnpm@3.5.3

brew install --cask docker
````
```
./infrastructure/deploy-core.bash -e cmsdev2 -b givenand-cms2-s3 -p givenand-kp-cms2 -R us-west-2 -P givenand-cms -B  -y s3://givenand-cms2-s3/template-snippets/ -i 0.0.0.0/0 

./infrastructure/deploy.bash -b givenand-cms2-s3 -h givenand@amazon.com -B -R us-west-2 -K givenand-cms -e cmsdev2 -P givenand-cms -p givenand-kp-cms2
```
2. An AWS CLI profile is setup that has administrator access to the account where CMS is deployed.  This account will be referenced in the script parameters as "profile"

3. A valid VIN will be used as the thing name and subsequent simulations

# Credentials

Before you can deploy an application, be sure you have credentials configured. If you have previously configured your machine to run boto3 (the AWS SDK for Python) or the AWS CLI then you can skip this section.

If this is your first time configuring credentials for AWS you can follow these steps to quickly get started:

$ mkdir ~/.aws
$ cat >> ~/.aws/config
[default]
aws_access_key_id=YOUR_ACCESS_KEY_HERE
aws_secret_access_key=YOUR_SECRET_ACCESS_KEY
region=YOUR_REGION (such as us-west-2, us-west-1, etc)

If you want more information on all the supported methods for configuring credentials, see the boto3 docs.

# Overview

The setupSingleVehicle.py will perform all the necessary steps to create a single vehicle in CMS.  The script uses the CF template exports to build the necessary API endpoints, get the necessary certificateIds and user credentials needed to make changes

1. The script will first make modifications to the Cognito User Pool created by default by the CMS CF template.  This will allow for automated creation of users and authentication, rather than a manual method via the Cognito front-end

2. The script will then take this cognito client Id and pass it into CMS APIs to authenticate to those front-end APIs

3. From here, we now need to follow the setup process for a vehicle, which is the following:
    a. Create a device supplier (Denso, NXP, etc)
    b. Register a device (TCU, ECU, etc)
    c. Activate a device
    d. Assosciate a device to a user

4. At this point, we have created a CMS user and created a single vehicle.  The next step is provisioning certificates to the device such that it can connect to IoT Core

5. To create device certificates for a fleet, the decision was made to use just-in-time-registration which provides a bootstrap certificate to place on the device during manufacturing.  This certificate will allow the device to connect and subscribe to reserved IoT Core topics which will then provision the production certificate for the device.

6. When the device connects to this reserved topic a new certificate and public/private key is generated and downloaded to the device.  The device then uses that combination to attach to CMS topics.

7. From there, we can use the generateTelemetry.py to create payloads for devices generating routes and simulating vehicle traffic within the UI.

# Creating your Device

The next thing we will do is run the script to setup the device


# Create some telemetry
