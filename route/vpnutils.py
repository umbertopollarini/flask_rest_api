# BEGIN: 1a2b3c4d5e6f

from flask import Blueprint, jsonify, request
import subprocess
vpnutils_bp = Blueprint('vpnutils', __name__)

@vpnutils_bp.route('/vpn/configurations', methods=['GET'])
def get_wireguard_config():
    file_path = '/etc/wireguard/wg0.conf'
    
    try:
        # Esegui il comando sudo cat per leggere il contenuto del file come root
        command = f'sudo cat {file_path}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            config_content = output.decode('utf-8')
            config_lines = config_content.strip().split('\n')

            config_dict = {}
            current_section = None

            for line in config_lines:
                line = line.strip()

                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    config_dict[current_section] = {}
                elif '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    config_dict[current_section][key] = value

            return jsonify(config_dict)
        else:
            # Il file non esiste, restituisci un messaggio di errore
            return jsonify({'error': 'Config file not found'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@vpnutils_bp.route('/vpn/configurations/raw', methods=['GET'])
def get_wireguard_raw_config():
    file_path = '/etc/wireguard/wg0.conf'
    
    try:
        # Esegui il comando sudo cat per leggere il contenuto del file come root
        command = f'sudo cat {file_path}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        return jsonify({'config': output.decode('utf-8')})
    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@vpnutils_bp.route('/vpn/configurations', methods=['POST'])
def set_wireguard_config():
    file_path = '/etc/wireguard/wg0.conf'
    
    try:
        # Get the configuration from the request body
        from flask import request

        data = request.get_json() # type: ignore
        
        config = data['config']

        # Esegui il comando sudo cat per leggere il contenuto del file come root
        command = f'echo "{config}" | sudo tee {file_path}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to set VPN configuration'})

        return jsonify({'message': 'VPN configuration set successfully'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

# END: 1a2b3c4d5e6f

@vpnutils_bp.route('/vpn/status', methods=['GET'])
def get_wireguard_status():
    try:
        # Esegui il comando sudo wg per ottenere lo stato del servizio
        command = f'sudo wg'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
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

        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get VPN status'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

@vpnutils_bp.route('/vpn/restart', methods=['POST'])
def restart_wireguard():
    try:
        # Esegui il comando sudo wg per ottenere lo stato del servizio
        command = f'sudo wg-quick down wg0 || true && sudo wg-quick up wg0'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to restart VPN'})

        return jsonify({'message': 'VPN restarted successfully'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})
    
   
@vpnutils_bp.route('/vpn/speedtest', methods=['GET'])
def get_wireguard_speedtest():
    try:
        # Esegui il comando speedtest-cli per ottenere la velocità della connessione
        command = f'speedtest-cli --simple --secure'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
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

        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get VPN speedtest'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

# END: 1a2b3c4d5e6f

