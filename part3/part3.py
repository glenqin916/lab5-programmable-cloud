#!/usr/bin/env python3
import os
import googleapiclient.discovery
import google.oauth2.service_account as service_account

# Configuration
CRED_FILE = 'service-credentials.json'
credentials = service_account.Credentials.from_service_account_file(CRED_FILE)
project = os.getenv('GOOGLE_CLOUD_PROJECT') or 'YOUR_PROJECT_ID'
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

with open('vm1_logic.py', 'r') as f:
    vm1_logic_code = f.read()

with open(CRED_FILE, 'r') as f:
    service_json = f.read()

# Startup script for VM2 to run flask application
vm2_startup_script = """#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip git
mkdir -p /opt/flask-app
cd /opt/flask-app
git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial
cd flask-tutorial
python3 -m pip install -e .
export FLASK_APP=flaskr
python3 -m flask init-db
nohup python3 -m flask run -h 0.0.0.0 -p 5000 > /var/log/flask_startup.log 2>&1 &
"""

# Startup script to create VVM1 instance
vm1_startup = f"""#!/bin/bash
mkdir -p /srv && cd /srv
curl http://metadata/computeMetadata/v1/instance/attributes/service-credentials -H "Metadata-Flavor: Google" > service-credentials.json
curl http://metadata/computeMetadata/v1/instance/attributes/vm1-logic -H "Metadata-Flavor: Google" > vm1_logic.py
curl http://metadata/computeMetadata/v1/instance/attributes/vm2-startup -H "Metadata-Flavor: Google" > vm2-startup.sh
export GOOGLE_CLOUD_PROJECT={project}

apt-get update && apt-get install -y python3-pip
pip3 install --upgrade google-api-python-client google-auth
python3 vm1_logic.py
"""

# Launches first instance and passes uses VM2 script to create second instance
def launch_vm1():
    config = {
        'name': 'lab5-vm1-controller',
        'machineType': f"zones/us-west1-b/machineTypes/e2-micro",
        'disks': [{'boot': True, 'autoDelete': True, 'initializeParams': {
            'sourceImage': 'projects/debian-cloud/global/images/family/debian-11'
        }}],
        'networkInterfaces': [{'network': 'global/networks/default', 'accessConfigs': [{'type': 'ONE_TO_ONE_NAT'}]}],
        'metadata': {
            'items': [
                {'key': 'startup-script', 'value': vm1_startup},
                {'key': 'vm1-logic', 'value': vm1_logic_code},
                {'key': 'service-credentials', 'value': service_json},
                {'key': 'vm2-startup', 'value': vm2_startup_script}
            ]
        }
    }
    print("Launching VM-1 (Controller)...")
    service.instances().insert(project=project, zone='us-west1-b', body=config).execute()

if __name__ == '__main__':
    launch_vm1()
