import json
import mytools
import netmiko
import os
import sys
import re
from datetime import datetime

def get_access_ports_from_config(output):
    lines = output.splitlines()

    access_ports = []

    access_pattern = re.compile(r'^\s*switchport mode access$')

    for i in range(len(lines)):
        if access_pattern.match(lines[i]):
            match = re.match(r'^\s*interface\s+(\S+)', lines[i - 1])
            if match:
                access_ports.append(match.group(1))

    return access_ports

def generate_changes(access_ports, additional_config):
    """
    Generates changes to be applied to access ports.
    """
    changes = []
    for interface in access_ports:
        config_to_apply = additional_config.copy()
        config_to_apply.insert(0, f'interface {interface}\n')
        changes.extend(config_to_apply)
        changes.append('\n')
    return changes

def log_changes(device, changes):
    """
    Logs changes made to the device.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{device['ip']}_{timestamp}.txt"
    file_path = os.path.join("Device Log", filename)
    with open(file_path, 'w') as out_file:
        for change in changes:
            out_file.write(change)

def connect_and_apply_changes(device, username, password, change_sum, additional_config):
    """
    Connects to a device, retrieves access ports, applies changes, and logs results.
    """
    try:
        print('~' * 79)
        print('Connecting to device:', device['ip'])
        print()
        connection = netmiko.ConnectHandler(**device)
        log_message = 'send log 6 "{} {}"'
        connection.send_command(log_message.format('Starting Change:', change_sum))
        output = connection.send_command('show run | i interface Eth|interface Gi|interface Tw|interface Fo|switchport mode access')
        access_ports = get_access_ports_from_config(output)
        print('Access Ports:', access_ports)
        changes = generate_changes(access_ports, additional_config)
        log_changes(device, changes)
        connection.send_command('write memory')
        connection.send_command(log_message.format('Completed change:', change_sum))
        connection.disconnect()
        return device['ip'], 'Successful'
    except netmiko_exceptions as error:
        print('Failed to ', device['ip'], error)
        return device['ip'], 'Failed'

if len(sys.argv) < 2:
    print('Usage:', os.path.split(sys.argv[0])[-1], 'devices.json')
    exit()

change_sum = mytools.get_input('Please enter change summary: ')

netmiko_exceptions = (netmiko.NetMikoTimeoutException,
                      netmiko.NetMikoAuthenticationException)

username, password = mytools.get_credentials()

with open(sys.argv[1]) as dev_file:
     devices = json.load(dev_file)

results = {'Successful': [], 'Failed': []}

with open('add-interface-config.txt', 'r') as config_file:
    additional_config = config_file.readlines()

# Main loop
for device in devices:
    device['username'] = username
    device['password'] = password
    ip, status = connect_and_apply_changes(device, username, password, change_sum, additional_config)
    results[status].append(ip)

print(json.dumps(results, indent=2))
