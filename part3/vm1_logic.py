#!/usr/bin/env python3
import os
import googleapiclient.discovery
import google.oauth2.service_account as service_account

# Use the credentials file downloaded via curl in the startup script
key_path = 'service-credentials.json'
credentials = service_account.Credentials.from_service_account_file(key_path)
project = os.getenv('GOOGLE_CLOUD_PROJECT')
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

ZONE = 'us-west1-b'
VM2_NAME = 'lab5-vm2-flask'

def create_vm2():
    # Retrieve the startup script for VM2 that was passed to VM1 metadata
    # (The curl command in VM1's startup script will save this to vm2-startup.sh)
    with open('vm2-startup.sh', 'r') as f:
        vm2_startup = f.read()

    image_response = service.images().getFromFamily(project='debian-cloud', family='debian-11').execute()
    source_disk_image = image_response['selfLink']

    config = {
        'name': VM2_NAME,
        'machineType': f"zones/{ZONE}/machineTypes/e2-micro",
        'tags': {'items': ['flask-server']},
        'disks': [{'boot': True, 'autoDelete': True, 'initializeParams': {'sourceImage': source_disk_image}}],
        'networkInterfaces': [{'network': 'global/networks/default', 'accessConfigs': [{'type': 'ONE_TO_ONE_NAT'}]}],
        'metadata': {'items': [{'key': 'startup-script', 'value': vm2_startup}]}
    }

    print(f"VM-1 is now launching VM-2...")
    return service.instances().insert(project=project, zone=ZONE, body=config).execute()

if __name__ == '__main__':
    create_vm2()