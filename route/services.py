import subprocess
from flask import Blueprint, jsonify

services_bp = Blueprint('services', __name__)

@services_bp.route('/services', methods=['GET'])
def get_services():
    try:
        # Esegui il comando systemctl per ottenere la lista dei servizi
        command = f'systemctl list-unit-files --type=service'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Parse the output and create a list of services
            output_lines = output.decode('utf-8').strip().split('\n')
            services_list = []

            for line in output_lines[1:]:
                split_line = line.split()
                if split_line:
                    service_name = split_line[0]
                    service_status = split_line[1]
                    service_dict = {'name': service_name, 'status': service_status}
                    services_list.append(service_dict)

            # Return the list of services as JSON
            return jsonify({'services': services_list})

        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get services list'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})
    
@services_bp.route('/services/<service_name>/status', methods=['GET'])
def get_service_status(service_name):
    try:
        # Esegui il comando systemctl per ottenere lo stato del servizio
        command = f'systemctl status {service_name}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        # Parse the output and create a dictionary
        output_lines = output.decode('utf-8').strip().split('\n')
        output_dict = {}

        for line in output_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().replace(' ', '_')
                value = value.strip()
                output_dict[key] = value

        # Return the dictionary as JSON
        return jsonify(output_dict)
    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@services_bp.route('/services/<service_name>/stop', methods=['POST'])
def stop_service(service_name):
    try:
        # Esegui il comando systemctl per fermare il servizio
        command = f'sudo systemctl stop {service_name}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': f'Failed to stop service {service_name}'})

        return jsonify({'message': f'Service {service_name} stopped successfully'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@services_bp.route('/services/<service_name>/restart', methods=['POST'])
def restart_service(service_name):
    try:
        # Esegui il comando systemctl per riavviare il servizio
        command = f'sudo systemctl restart {service_name}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': f'Failed to restart service {service_name}'})

        return jsonify({'message': f'Service {service_name} restarted successfully'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

