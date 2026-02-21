#!/usr/bin/env python3
import os
import time
import googleapiclient.discovery
import google.auth
from googleapiclient.errors import HttpError

credentials, project = google.auth.default()
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

ZONE = 'us-west1-b'
SOURCE_INSTANCE = 'lab5-part1-instance'
SNAPSHOT_NAME = f'base-snapshot-{SOURCE_INSTANCE}'
NUM_CLONES = 3

def wait_for_operation(compute, project, operation, zone=None):
    while True:
        if zone:
            result = compute.zoneOperations().get(project=project, zone=zone, operation=operation['name']).execute()
        else:
            result = compute.globalOperations().get(project=project, operation=operation['name']).execute()
        if result['status'] == 'DONE':
            return result
        time.sleep(2)

def create_snapshot(compute, project, zone, instance_name, snapshot_name):
    instance = compute.instances().get(project=project, zone=zone, instance=instance_name).execute()
    
    source_disk_name = instance['disks'][0]['source'].split('/')[-1]
    
    print(f"Found actual disk name: {source_disk_name}")

    snapshot_body = {
        'name': snapshot_name,
        'description': 'Snapshot of the configured Flask server'
    }
    
    return compute.disks().createSnapshot(
        project=project, 
        zone=zone, 
        disk=source_disk_name, 
        body=snapshot_body
    ).execute()

def create_clone(compute, project, zone, name, snapshot_name):
    snapshot_link = f"projects/{project}/global/snapshots/{snapshot_name}"
    
    config = {
        'name': name,
        'machineType': f"zones/{zone}/machineTypes/e2-micro",
        'metadata': {
            'items': [{
                'key': 'startup-script',
                'value': '#!/bin/bash\ncd /opt/flask-app/flask-tutorial\nexport FLASK_APP=flaskr\npython3 -m flask init-db\nnohup python3 -m flask run --host=0.0.0.0 --port=5000 > /var/log/flask_clone.log 2>&1 &'
            }]
        },
        'tags': {'items': ['flask-server']},
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {'sourceSnapshot': snapshot_link}
        }],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [{'type': 'ONE_TO_ONE_NAT'}]
        }],
        
    }
    
    start_time = time.time()
    op = compute.instances().insert(project=project, zone=zone, body=config).execute()
    wait_for_operation(compute, project, op, zone=zone)
    end_time = time.time()
    
    return end_time - start_time

def snapshot_exists(compute, project, snapshot_name):
    try:
        compute.snapshots().get(project=project, snapshot=snapshot_name).execute()
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return False
        raise

# --- Main ---
if not snapshot_exists(service, project, SNAPSHOT_NAME):
    op = create_snapshot(service, project, ZONE, SOURCE_INSTANCE, SNAPSHOT_NAME)
    print("Waiting for snapshot creation...")
    wait_for_operation(service, project, op)
else:
    print(f"Snapshot already exists: {SNAPSHOT_NAME}")

print("Ensuring snapshot is READY...")
while True:
    snap = service.snapshots().get(project=project, snapshot=SNAPSHOT_NAME).execute()
    if snap['status'] == 'READY':
        break
    print(f"Snapshot status: {snap['status']}. Waiting...")
    time.sleep(5)

timings = []
for i in range(1, NUM_CLONES + 1):
    clone_name = f"clone-{i}-{SOURCE_INSTANCE}"
    print(f"Creating {clone_name}...")
    duration = create_clone(service, project, ZONE, clone_name, SNAPSHOT_NAME)
    timings.append((clone_name, duration))
    print(f"Finished in {duration:.2f} seconds.")

with open("TIMING.md", "w") as f:
    f.write("# Creation Timing Results\n\n")
    f.write("| Instance Name | Time (seconds) |\n")
    f.write("| --- | --- |\n")
    for name, duration in timings:
        f.write(f"| {name} | {duration:.2f} |\n")

print("\nTIMING.md has been generated.")
