#!/usr/bin/env python3
import os
import time
import googleapiclient.discovery
import google.auth

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
    # 1. Get the disk name from the instance
    instance = compute.instances().get(project=project, zone=zone, instance=instance_name).execute()
    disk_name = instance['disks'][0]['deviceName'] # Usually same as instance name

    # 2. Create the snapshot
    print(f"Creating snapshot {snapshot_name} from disk {disk_name}...")
    snapshot_body = {'name': snapshot_name}
    op = compute.disks().createSnapshot(project=project, zone=zone, disk=disk_name, body=snapshot_body).execute()
    wait_for_operation(compute, project, op, zone=zone)
    print("Snapshot created.")

def create_clone(compute, project, zone, name, snapshot_name):
    snapshot_link = f"projects/{project}/global/snapshots/{snapshot_name}"
    
    config = {
        'name': name,
        'machineType': f"zones/{zone}/machineTypes/e2-micro",
        'tags': {'items': ['flask-server']}, # Re-use Part 1 firewall tag
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {'sourceSnapshot': snapshot_link}
        }],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [{'type': 'ONE_TO_ONE_NAT'}]
        }]
    }
    
    start_time = time.time()
    op = compute.instances().insert(project=project, zone=zone, body=config).execute()
    wait_for_operation(compute, project, op, zone=zone)
    end_time = time.time()
    
    return end_time - start_time

# --- Main ---
# Step 1: Create Snapshot
create_snapshot(service, project, ZONE, SOURCE_INSTANCE, SNAPSHOT_NAME)

# Step 2: Create 3 Clones and track timing
timings = []
for i in range(1, NUM_CLONES + 1):
    clone_name = f"clone-{i}-{SOURCE_INSTANCE}"
    print(f"Creating {clone_name}...")
    duration = create_clone(service, project, ZONE, clone_name, SNAPSHOT_NAME)
    timings.append((clone_name, duration))
    print(f"Finished in {duration:.2f} seconds.")

# Step 3: Write to TIMING.md
with open("TIMING.md", "w") as f:
    f.write("# Creation Timing Results\n\n")
    f.write("| Instance Name | Time (seconds) |\n")
    f.write("| --- | --- |\n")
    for name, duration in timings:
        f.write(f"| {name} | {duration:.2f} |\n")

print("\nTIMING.md has been generated.")