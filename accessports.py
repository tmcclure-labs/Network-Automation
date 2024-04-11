#Accessports.py

import json
import mytools
import netmiko
import os
import sys
import re

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

for device in devices:
    device['username'] = username
    device['password'] = password
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
        for interface in access_ports:
            config_to_apply = additional_config.copy()
            config_to_apply.insert(0, f'interface {interface}\n')
            connection.send_config_set(config_to_apply)
        connection.send_command('write memory')
        connection.send_command(log_message.format('Completed change:', change_sum))
        connection.disconnect()
        results['Successful'].append(device['ip'])
    except netmiko_exceptions as error:
        print('Failed to ', device['ip'], error)
        results['Failed'].append(': '.join((device['ip'], str(error))))

print(json.dumps(results, indent=2))
with open('results-' + change_number + '.json', 'w') as results_file:
    json.dump(results, results_file, indent=2)
