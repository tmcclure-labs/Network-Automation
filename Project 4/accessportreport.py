import json
import mytools
import netmiko
import os
import sys
import re
from datetime import datetime

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

def generate_compliance_report(connection, device, access_ports, report_file):
    """
    Generates a compliance report for access port interfaces.
    """
    compliant_count = 0
    non_compliant_count = 0

    report_file.write(f"Compliance Report for Device: {device['ip']}\n")
    report_file.write("=" * 50 + "\n")

    for interface in access_ports:
        report_file.write(f"Interface: {interface}\n")
        output = connection.send_command(f"show run interface {interface}")
        reference_lines = get_reference_lines()
        interface_lines = output.splitlines()

        # Check compliance
        compliant = True
        for line in reference_lines:
            # Strip leading whitespace from both interface line and reference line
            reference_line_stripped = line.strip()
            if all(reference_line_stripped not in interface_line.strip() for interface_line in interface_lines):
                compliant = False
                non_compliant_count += 1
                report_file.write(f"- Missing: {line}\n")
        
        if compliant:
            compliant_count += 1
            report_file.write("- Compliance: Yes\n")
        else:
            report_file.write("- Compliance: No\n")

        report_file.write("\n")

    report_file.write(f"Total compliant: {compliant_count}\n")
    report_file.write(f"Total non-compliant: {non_compliant_count}\n")


def get_reference_lines():
    """
    Reads the reference file and returns lines as a list.
    """
    with open('access-port-reference.txt', 'r') as reference_file:
        reference_lines = [line.strip() for line in reference_file.readlines()]
    return reference_lines

def connect_and_generate_report(device, username, password, report_file):
    """
    Connects to a device, retrieves access ports, and generates a compliance report.
    """
    try:
        print(f"\nConnecting to device: {device['ip']}")
        connection = netmiko.ConnectHandler(**device)
        print("Retrieving access port information...")
        output = connection.send_command('show run | i interface Fa|interface Gi|interface Tw|interface Fo|switchport mode access')
        access_ports = get_access_ports_from_config(output)
        generate_compliance_report(connection, device, access_ports, report_file)
        connection.disconnect()
        print(f"Successfully generated report for device: {device['ip']}")
        return device['ip'], 'Successful'
    except netmiko_exceptions as error:
        print(f"Failed to connect to device: {device['ip']}. Error: {error}")
        return device['ip'], 'Failed'

if len(sys.argv) < 2:
    print('Usage:', os.path.split(sys.argv[0])[-1], 'devices.json')
    exit()

netmiko_exceptions = (netmiko.NetMikoTimeoutException,
                      netmiko.NetMikoAuthenticationException)

now = datetime.now()
timestamp = now.strftime("%Y%m%d_%H%M%S")
report_filename = f"Access_Port_Report_{timestamp}.txt"
report_path = os.path.join("Reports", report_filename)

with open(sys.argv[1]) as dev_file, open(report_path, 'w') as report_file:
    devices = json.load(dev_file)

    results = {'Successful': [], 'Failed': []}

    print("\nReport generation started...\n")

    for device in devices:
        device['username'] = username
        device['password'] = password
        ip, status = connect_and_generate_report(device, username, password, report_file)
        results[status].append(ip)

    print("\nReport generation completed.\n")
    print(json.dumps(results, indent=2))
