#!/bin/bash

LOG_FILE=deploy.log

cd cdf-infrastructure-auto
./deploy.bash -e development -u $ASSET_BUCKET -p $KEY_PAIR -i 0.0.0.0/0 -g scofranc@amazon.com -b $RSRC_BUCKET -R $REGION -P default -B -C | tee $LOG_FILE
