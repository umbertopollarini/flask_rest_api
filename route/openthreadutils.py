# BEGIN: 

from flask import Blueprint, jsonify, request
import subprocess
import re
openthreadutils_bp = Blueprint('openthreadutils', __name__)

@openthreadutils_bp.route('/openthread/configurations', methods=['GET'])
def get_openthread_config():
    """
    Retrieves the OpenThread configuration by executing the 'sudo ot-ctl dataset' command as root.
    Returns a JSON response containing the OpenThread configuration.

    Example response:
    {
        "config": {
            "panid": "0xdead",
            "extpanid": "dead1111dead2222",
            "networkname": "OpenThreadGuide",
            "networkkey": "11112233445566778899DEAD1111DEAD"
        }
    }
    """
    try:
        # Execute the command as root
        command = 'sudo ot-ctl dataset active'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Parse the output and return the configuration as a JSON response
            config = {}
            for line in output.decode('utf-8').split('\n'):
                if ':' in line:
                    values = line.split(':')
                    key = values[0].strip().lower().replace(" ", "")
                    value = ':'.join(values[1:]).strip()
                    config[key] = value
                    value = ':'.join(values[1:]).strip()
                    config[key] = value
            return jsonify({'config': config})
        else:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to retrieve OpenThread configuration'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})

@openthreadutils_bp.route('/openthread/configurations', methods=['POST'])
def set_openthread_config():
    """
    Sets the OpenThread configuration by executing the 'sudo ot-ctl dataset <config>' command as root.
    The configuration is passed as a JSON object in the request body.

    Example request body:
    {
        "config": {
            "panid": "0xdead",
            "extpanid": "dead1111dead2222",
            "networkname": "OpenThreadGuide",
            "networkkey": "11112233445566778899DEAD1111DEAD"
        }
    }
    """
    try:
        # Get the configuration from the request body
        from flask import request
        data = request.get_json() # type: ignore
        config = data['config']

        # Execute the commands as root
        for key, value in config.items():
            command = f'sudo ot-ctl dataset {key} {value}'
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()

            if process.returncode != 0:
                # Return an error message if the command failed
                return jsonify({'error': f'Failed to set OpenThread {key} configuration'})

        return jsonify({'message': 'OpenThread configuration set successfully'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'error': str(e)})
    



@openthreadutils_bp.route('/openthread/bbr', methods=['GET'])
def get_openthread_bbr():
    try:
        # Execute the command as root
        command = 'sudo ot-ctl bbr'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to execute command'})
        
        # Parse the output to extract the relevant information
        output_lines = output.decode().split('\n')

        bbr_primary = ""
        seqno = output_lines[1].split(': ')[1]
        delay = output_lines[2].split(': ')[1]
        timeout = output_lines[3].split(': ')[1]
        print(bbr_primary, seqno, delay, timeout)

        # Return the information as a JSON object
        return jsonify({
            'bbr_primary': bbr_primary,
            'seqno': seqno,
            'delay': delay,
            'timeout': timeout
        })

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'error': str(e)})


@openthreadutils_bp.route('/openthread/topology', methods=['GET'])
def get_openthread_topology():

    try:
        # Execute the command as root
        command = 'sudo ot-ctl meshdiag topology'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to execute command'})

        output_lines = output.decode().split('\n')
        nodes = []
        for i, line in enumerate(output_lines):
            match = re.search(r'id:(\d+) rloc16:(\w+) ext-addr:(\w+) ver:(\d+)(.*)', line)
            if match:
                node = {
                    'id': match.group(1),
                    'rloc16': match.group(2),
                    'ext-addr': match.group(3),
                    'ver': match.group(4),
                    'info': match.group(5).strip()
                }
                # Check if the next line contains links information
                if i+1 < len(output_lines):
                    links_match = re.search(r'(\d+)-links:{(.*)}', output_lines[i+1])
                    if links_match:
                        node['links'] = links_match.group(2).strip().split()
                nodes.append(node)

        # Return the information as a JSON object
        return jsonify({'nodes': nodes})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'error': str(e)})

import subprocess
import re
import time

@openthreadutils_bp.route('/openthread/topology/ip6-addrs', methods=['GET'])
def get_openthread_topology_ip6_addrs():

    try:
        # Execute the command as root
        command = 'sudo ot-ctl meshdiag topology ip6-addrs'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to execute command'})

        output_lines = output.decode().split('\n')
        nodes = []
        for i, line in enumerate(output_lines):
            match = re.search(r'id:(\d+) rloc16:(\w+) ext-addr:(\w+)( ver:(\d+))?(.*)', line)
            if match:
                node = {
                    'id': match.group(1),
                    'rloc16': match.group(2),
                    'ext-addr': match.group(3),
                    'ver': match.group(5) if match.group(5) else '',
                    'info': match.group(6).strip() if match.group(6) else ''
                }

                node['links'] = []
                # Check if the next line contains links information
                if i+1 < len(output_lines):
                    links_match = re.search(r'(\d+)-links:{(.*)}', output_lines[i+1])
                    if links_match:
                        node['links'].extend(links_match.group(2).strip().split())

                # Check if the next line contains links information
                if i+2 < len(output_lines):
                    links_match = re.search(r'(\d+)-links:{(.*)}', output_lines[i+2])
                    if links_match:
                        node['links'].extend(links_match.group(2).strip().split())

                # Check if the next line contains ipv6 addresses information
                if i+2 < len(output_lines):
                    ipv6_addrs_match = re.search(r'ip6-addrs:(.*)', output_lines[i+2])
                    if ipv6_addrs_match:
                        ipv6_addrs = output_lines[i+3].replace(' ', '').replace('\r', '')
                        node['ip6_addr'] = ipv6_addrs
                    else:
                        print('No ipv6 addresses found for node', node['id'])

                 # Check if the next line contains ipv6 addresses information
                if i+3 < len(output_lines):
                    ipv6_addrs_match = re.search(r'ip6-addrs:(.*)', output_lines[i+3])
                    if ipv6_addrs_match:
                        ipv6_addrs = output_lines[i+4].replace(' ', '').replace('\r', '')
                        node['ip6_addr'] = ipv6_addrs
                    else:
                        print('No ipv6 addresses found for node', node['id'])

                # Ping the node's ip6_addr and add the response time in milliseconds
                if 'ip6_addr' in node:
                    ping_command = f'ping -c 1 -W 1 {node["ip6_addr"]}'
                    ping_process = subprocess.Popen(ping_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    ping_output, ping_error = ping_process.communicate()
                    if ping_process.returncode == 0:
                        # Extract the response time from the ping output
                        time_match = re.search(r'time=(\d+\.\d+) ms', ping_output.decode())
                        if time_match:
                            node['ping_time'] = float(time_match.group(1))
                    else:
                        print(f'Failed to ping {node["ip6_addr"]}')

                nodes.append(node)

        # Return the information as a JSON object
        return jsonify({'output' : output.decode(),'nodes': nodes})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'error': str(e)})

@openthreadutils_bp.route('/openthread/topology/raw', methods=['GET'])
def get_openthread_topology_raw():
    """
    Retrieves the raw output of the 'ot-ctl meshdiag topology' command.
    Returns a JSON response containing the raw output.

    Example response:
    {
        "output": "raw output of the command"
    }
    """
    try:
        # Execute the command as root
        command = 'sudo ot-ctl meshdiag topology ip6-addrs'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to execute command'})

        # Return the raw output as a JSON object
        return jsonify({'output': output.decode()})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'error': str(e)})
 
@openthreadutils_bp.route('/openthread/childNumber', methods=['GET'])
def get_openthread_childNumber():
    """
    Retrieves the number of children by executing the 'child list' command.
    Returns a JSON response containing the number of children.

    Example response:
    {
        "childNumber": "5"
    }
    """
    try:
        # Execute the command
        command = 'sudo ot-ctl child list'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Parse the output and return the number of children as a JSON response
            child_list = output.decode('utf-8').strip().split()
            childNumber = str(len(child_list))
            return jsonify({'childNumber': childNumber})
        else:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to retrieve number of children'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})


@openthreadutils_bp.route('/openthread/failCounter', methods=['GET'])
def get_openthread_failCounter():
    """
    Retrieves the fail counter by executing the 'childsupervision failcounter' command.
    Returns a JSON response containing the fail counter.

    Example response:
    {
        "failCounter": "0"
    }
    """
    try:
        # Execute the command
        command = 'sudo ot-ctl childsupervision failcounter'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Parse the output and return the fail counter as a JSON response
            failCounter = output.decode('utf-8').strip().split('\r\n')[0]
            return jsonify({'failCounter': failCounter})
        else:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to retrieve fail counter'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})


@openthreadutils_bp.route('/openthread/counters/mle', methods=['GET'])
def get_openthread_counters_mle():
    """
    Retrieves the MLE counters by executing the 'counters mle' command.
    Returns a JSON response containing the MLE counters.

    Example response:
    {
        "Role Disabled": "0",
        "Role Detached": "1",
        "Role Child": "0",
        "Role Router": "0",
        "Role Leader": "0",
        "Attach Attempts": "10",
        "Partition Id Changes": "0",
        "Better Partition Attach Attempts": "0",
        "Parent Changes": "0",
        "Time Disabled Milli": "45",
        "Time Detached Milli": "188875",
        "Time Child Milli": "0",
        "Time Router Milli": "0",
        "Time Leader Milli": "0",
        "Time Tracked Milli": "188920",
        "Done": ""
    }
    """
    try:
        # Execute the command
        command = 'sudo ot-ctl counters mle'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Parse the output and return the MLE counters as a JSON response
            counters = {}
            for line in output.decode('utf-8').split('\n'):
                if line.strip() != '':
                    key_value = line.split(':')
                    if len(key_value) > 1:
                        counters[key_value[0].strip()] = key_value[1].strip()
            return jsonify(counters)
        else:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to retrieve MLE counters'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})


@openthreadutils_bp.route('/openthread/counters/nodes', methods=['GET'])
def get_openthread_counters_nodes():
    """
    Retrieves the node list count by executing the 'router list' command.
    Returns a JSON response containing the node list count.

    Example response:
    {
        "Node Count": "4"
    }
    """
    try:
        # Execute the command
        command = 'sudo ot-ctl router list'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Parse the output and return the node list count as a JSON response
            node_list = output.decode('utf-8').split('\n')[0]
            node_count = len(node_list.split())
            return jsonify({'Node Count': str(node_count)})
        else:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to retrieve node list count'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})

@openthreadutils_bp.route('/openthread/addjoiner', methods=['POST'])
def add_openthread_joiner():
    """
    Adds a joiner device with psk

    """
    try:
        from flask import request
        data = request.get_json()
        psk = data['psk']
        eui64ExtId = data['eui64ExtId']
        
        # Execute the command
        command1 = 'sudo ot-ctl commissioner start'
        process1 = subprocess.Popen(command1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process1.communicate()
        
        if process1.returncode == 0:
            command2 = 'sudo ot-ctl commissioner joiner add f4ce36' + eui64ExtId + ' ' + psk
            process2 = subprocess.Popen(command2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process2.communicate()
            if process2.returncode == 0: return "ok"
        else:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to add joiner device'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})