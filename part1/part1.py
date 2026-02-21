#!/usr/bin/env python3
import argparse
import os
import time
from pprint import pprint

import googleapiclient.discovery
import google.auth
import googleapiclient.errors

credentials, project = google.auth.default()
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

# Configuration
ZONE = 'us-west1-b'
INSTANCE_NAME = 'lab5-part1-instance'
PORT = 5000

# This script runs automatically when the VM boots
STARTUP_SCRIPT = """#!/bin/bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git
git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial
cd flask-tutorial
sudo python3 setup.py install
sudo pip3 install -e .
export FLASK_APP=flaskr
flask init-db
nohup flask run -h 0.0.0.0 &
"""

#
# Stub code - just lists all instances
#
def list_instances(compute, project, zone):
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items'] if 'items' in result else None

def wait_for_operation(compute, project, operation, zone=None):
    """Wait for a global or zone operation to finish."""
    print('Waiting for operation...', end='', flush=True)
    while True:
        if zone:
            result = compute.zoneOperations().get(project=project, zone=zone, operation=operation['name']).execute()
        else:
            result = compute.globalOperations().get(project=project, operation=operation['name']).execute()
        
        if result['status'] == 'DONE':
            print(' done.')
            return result
        print('.', end='', flush=True)
        time.sleep(2)

def create_firewall_rule(compute, project):
    """Creates a firewall rule to allow traffic on port 5000."""
    firewall_body = {
        'name': 'allow-flask-5000',
        'targetTags': ['flask-server'],
        'allowed': [{'IPProtocol': 'tcp', 'ports': [str(PORT)]}],
        'sourceRanges': ['0.0.0.0/0'],
        'description': 'Allow port 5000 for Lab 5'
    }
    try:
        print("Creating firewall rule...")
        op = compute.firewalls().insert(project=project, body=firewall_body).execute()
        wait_for_operation(compute, project, op)
    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 409: # Already exists
            print("Firewall rule already exists.")
        else: raise e

def create_instance(compute, project, zone, name):
    image_response = compute.images().getFromFamily(project='debian-cloud', family='debian-11').execute()
    source_disk_image = image_response['selfLink']
    
    config = {
        'name': name,
        'machineType': f"zones/{zone}/machineTypes/e2-micro",
        'tags': {'items': ['flask-server']},
        'disks': [{'boot': True, 'autoDelete': True, 'initializeParams': {'sourceImage': source_disk_image}}],
        'networkInterfaces': [{'network': 'global/networks/default', 'accessConfigs': [{'type': 'ONE_TO_ONE_NAT'}]}],
        'metadata': {'items': [{'key': 'startup-script', 'value': STARTUP_SCRIPT}]}
    }
    print(f"Creating instance {name}...")
    return compute.instances().insert(project=project, zone=zone, body=config).execute()

print("Your running instances are:")
instances = list_instances(service, project, ZONE)

if instances:
    for instance in instances:
        print(instance['name'])
else:
    print("None")
    
create_firewall_rule(service, project)
op = create_instance(service, project, ZONE, INSTANCE_NAME)
wait_for_operation(service, project, op, zone=ZONE)

# Get IP to show the user
instance_info = service.instances().get(project=project, zone=ZONE, instance=INSTANCE_NAME).execute()
external_ip = instance_info['networkInterfaces'][0]['accessConfigs'][0]['natIP']

print(f"\nSUCCESS! Visit your app at: http://{external_ip}:{PORT}")
