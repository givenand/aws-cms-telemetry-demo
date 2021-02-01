# AWS CMS Enablement 

This repo contains several scripts necessary to automate the creation of devices in Connected Mobility Solution

```bash
./setupSingleVehicle.py --profile=givenand-cms --stackName=cms-dev1 --VIN=LSH14J4C4LA046511 --FirstName=Test --LastName=User --Username=testCMSUser1 --Password=Testing1234 --CDFstackName cdf-core-development
```

# Requirements

1. The CMS CF was deployed succsesfully, please follow the onboarding instructions

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

The setupSingleVehicle.py will perform all the necessary steps to create a single vehicle in CMS.  The script uses the CF template exports to build the necessary API endpoints, get the necessary certificateIds and user credentials needed to make changes.

1. The script will first make modifications to the Cognito User Pool created by default by the CMS CF template.  This will allow for automated creation of users and authentication, rather than a manual method via the Cognito front-end

2. The script will then take this cognito client Id and pass it into CMS APIs to authenticate to those front-end APIs

3. From here, we now need to follow the setup process for a vehicle, which is the following:
    1. Create a device supplier (Denso, NXP, etc)
    2. Register a device (TCU, ECU, etc)
    3. Activate a device
    4. Assosciate a device to a user

4. At this point, we have created a CMS user and created a single vehicle.  The next step is provisioning certificates to the device such that it can connect to IoT Core

5. To create device certificates for a fleet, the decision was made to use just-in-time provisioning (JITP) which provides a bootstrap certificate to place on the device during manufacturing.  This certificate will allow the device to connect and subscribe to reserved IoT Core topics which will then provision the production certificate for the device.

6. When the device connects to this reserved topic a new certificate and public/private key is generated and downloaded to the device.  The device then uses that combination to subscribe to CMS topics.  For this demo, we will use virtual devices, essentially a directory with a unique vehicle Id (VIN) and the public/private certificate in the project folder

7. When running the setupSingleVehicle.py script, it will attempt to publish a single telemetry object to the /dt/cvra/+/data topic which is where telemetry data for the vehicle is published.  This initial load of data is necessary to show your vehicle in the UI.  After running the script, the output should show the cloudfront UI URL and the user can click to login with the user they created in the script.

Sample output:
```
Vehicle setup sucessfully, please visit http://d3lqxcqk33ijcr.cloudfront.net to login with your user and see your vehicle
```

8. From there, we can use the generateTelemetry.py to create payloads for devices generating routes and simulating vehicle traffic within the UI.

# Creating your Device

1. To generate telemetry, we can use the generate telemetry script, which will take the VIN that was just used to create
```
./generateTelemetry.py --VIN LSH14J4C4KA097044
```
2. This should post telemetry data (latitude/longitude) to the proper topic every second from the latLong2.csv file.  This data is generated using google maps and other routes can be generated if the below steps are followed.

3. Upon execution, you should see outputs like the below and your vehicle icon should be moving on the screen.

```
Generating Trip ID of 09ec10c7310d44d988cfb0ff5cdb3b98                                                                            Begin publishing trip data.  Will Begin publishing trip data.  Will publish 248 payloads
Successfully published coordinates Coords(x=33.77521, y=-84.39609) of 248
Successfully published coordinates Coords(x=33.77521, y=-84.39606) of 248
Successfully published coordinates Coords(x=33.77521, y=-84.39605) of 248
```

# Create some telemetry

2. To create a CSV of lat/long coordinates to create a proper simulation of a vehicle along a route, the quickest implementation is to utilize an online maps resource and export a route.  This will provide the most accurate data to simulate your trips and begin build upon other features available in CMS.  Below is the procedure to develop that data to be stored in assets/latLong.csv as exported.

    1. Go to maps.google.com 
    2. Click on the hamburger menu and select 'Your Places'
    3. At the bottom of the sidebar, select 'CREATE MAP'
    4. When the map creation interface loads in a new tab, click the 'Add directions' under the search bar
    5. Put in two local landmarks in the city of your choice and the route should appear on the map
    6. Click on the 'Untitled Map' dot menu, and select 'Export to KML/KMZ'
    7. Select the dropdown and select just the route directions and select download.
    8. Find the Placemark/coordinates within the markup language and copy that section (without the tags) into your latLong.csv

