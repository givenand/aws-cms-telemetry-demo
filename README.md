# AWS CMS Enablement 

This repo contains several scripts necessary to automate the creation of devices in Connected Mobility Solution

```bash
./setupSingleVehicle.py --profile=givenand-cms --stackName=cms-dev1 --VIN=LSH14J4C4LA046511 --FirstName=Test --LastName=User --Username=testCMSUser1 --Password=Testing1234
```

# Requirements

1. The CMS CF was deployed succsesfully, please follow the instructions here: https://quip-amazon.com/hLrnALX7bgCd/Connected-Mobility-Solution-Getting-Started

2. An AWS CLI profile is setup that has administrator access to the account where CMS is deployed.  This account will be referenced in the script parameters as "profile"

3. A valid VIN will be used as the thing name and subsequent simulations

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