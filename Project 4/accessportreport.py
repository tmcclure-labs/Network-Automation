import json
import mytools
import netmiko
import os
import sys
import re
from datetime import datetime
from pprint import pprint

username, password = mytools.get_credentials()

def get_access_ports_from_config(output):
    lines = output.splitlines()

    access_ports = []

    access_pattern = re.compile(r'^\s*switchport mode access$')

    for i in range(len(lines)):
        if access_pattern.match(lines[i]):
            match = re.match(r'^\s*interface\s+(\S+)', lines[i - 1])
            if match:
                access_ports.append(match.group(1))
    print("Access Ports:", access_ports)
    return access_ports

def generate_compliance_report(connection, device, access_ports):
    """
    Generates a compliance report for access port interfaces.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"Access Port Report_{timestamp}.txt"
    report_path = os.path.join("Reports", filename)
    with open(report_path, 'w') as report_file:
        report_file.write(f"Compliance Report for Device: {device['ip']}\n")
        report_file.write("=" * 50 + "\n")
        
        # Print the access ports to verify their contents
        print("Access Ports:", access_ports)

        for interface in access_ports:
            report_file.write(f"Interface: {interface}\n")
            output = connection.send_command(f"show run interface {interface}")
            reference_lines = get_reference_lines()
            interface_lines = output.splitlines()

            # Check compliance
            compliant = True
            for line in reference_lines:
                # Strip leading whitespace from reference line
                reference_line_stripped = line.strip()
                if all(reference_line_stripped not in interface_line.strip() for interface_line in interface_lines):
                    compliant = False
                    report_file.write(f"- Missing: {line}\n")
                    break  # Exit the loop once a mismatch is found
            
            if compliant:
                report_file.write("- Compliance: Yes\n")
            else:
                report_file.write("- Compliance: No\n")
            
            # Add a newline character after writing compliance status for each interface
            report_file.write("\n")



def get_reference_lines():
    """
    Reads the reference file and returns lines as a list.
    """
    with open('access-port-reference.txt', 'r') as reference_file:
        reference_lines = [line.strip() for line in reference_file.readlines()]
    return reference_lines


def connect_and_generate_report(device, username, password):
    """
    Connects to a device, retrieves access ports, and generates a compliance report.
    """
    try:
        print('~' * 79)
        print('Connecting to device:', device['ip'])
        print()
        connection = netmiko.ConnectHandler(**device)
        output = connection.send_command('show run | i interface Eth|interface Gi|interface Tw|interface Fo|switchport mode access')
        print("Output for 'show run | i interface Eth|interface Gi|interface Tw|interface Fo|switchport mode access':")
        print(output)
        access_ports = get_access_ports_from_config(output)
        generate_compliance_report(connection, device, access_ports)
        connection.disconnect()
        return device['ip'], 'Successful'
    except netmiko_exceptions as error:
        print('Failed to ', device['ip'], error)
        return device['ip'], 'Failed'

if len(sys.argv) < 2:
    print('Usage:', os.path.split(sys.argv[0])[-1], 'devices.json')
    exit()

netmiko_exceptions = (netmiko.NetMikoTimeoutException,
                      netmiko.NetMikoAuthenticationException)

with open(sys.argv[1]) as dev_file:
     devices = json.load(dev_file)

results = {'Successful': [], 'Failed': []}

# Main loop
for device in devices:
    device['username'] = username
    device['password'] = password
    ip, status = connect_and_generate_report(device, username, password)
    results[status].append(ip)

print(json.dumps(results, indent=2))
