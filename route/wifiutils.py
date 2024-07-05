# BEGIN: 8f7d3h4j5k6l
from flask import Blueprint, jsonify, request
import subprocess
import re

wifiutils_bp = Blueprint('wifiutils', __name__)

@wifiutils_bp.route('/wifi/scan', methods=['GET'])
def get_wifi_scan():
    try:
        # Esegui il comando sudo iwlist wlan0 scan per leggere le reti wifi disponibili come root
        command = 'sudo iwlist wlan0 scan'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Il comando è andato a buon fine, estrai le informazioni
            output = output.decode('utf-8')
            networks = re.findall(r'Cell \d+ - Address: ([^\n]+).*?ESSID:"([^"]*)".*?Channel:(\d+).*?Signal level=(-\d+)', output, re.DOTALL)
            wifi_networks = []
            for network in networks:
                address, ssid, channel, signal_level = network
                wifi_networks.append({
                    'address': address,
                    'ssid': ssid,
                    'channel': int(channel),
                    'signal_level': int(signal_level)
                })
            return jsonify({'wifi_networks': wifi_networks})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to scan for wifi networks'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

@wifiutils_bp.route('/wifi/new', methods=['POST'])
def append_wifi_config():
    try:
        data = request.get_json() # type: ignore
        ssid = data['ssid']
        psk = data['psk']

        # Append the new network to the wpa_supplicant.conf file
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a') as f:
            f.write(f'\nnetwork={{\n\tssid="{ssid}"\n\tpsk="{psk}"\n}}\n')

        # Restart the networking service to apply the changes
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd.service'])

        return jsonify({'message': 'Wifi configuration added successfully'})

    except Exception as e:
        return jsonify({'error': str(e)})
    
@wifiutils_bp.route('/wifi/configurations', methods=['GET'])
def get_wifi_list_config():
    file_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
    
    try:
        # Esegui il comando sudo cat per leggere il contenuto del file come root
        command = f'sudo cat {file_path}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            config_content = output.decode('utf-8')
            networks = re.findall(r'network={([^}]*)}', config_content)

            wifi_networks = []
            for network in networks:
                ssid_match = re.search(r'ssid="([^"]*)"', network)
                psk_match = re.search(r'psk="([^"]*)"', network)

                if ssid_match and psk_match:
                    ssid = ssid_match.group(1)
                    psk = psk_match.group(1)
                    wifi_networks.append({'ssid': ssid, 'psk': psk})

            return jsonify(wifi_networks)

        else:
            # Il file non esiste, restituisci un messaggio di errore
            return jsonify({'error': 'Config file not found'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


# END: 8f7d3h4j5k6l

@wifiutils_bp.route('/wifi/configurations/raw', methods=['GET'])
def get_wireguard_raw_config():
    file_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
    
    try:
        # Esegui il comando sudo cat per leggere il contenuto del file come root
        command = f'sudo cat {file_path}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        return jsonify({'config': output.decode('utf-8')})
    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@wifiutils_bp.route('/wifi/configurations', methods=['POST'])
def override_wifi_config():
    file_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
    
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
    
@wifiutils_bp.route('/wifi/restart', methods=['POST'])
def restart_wifi():
    try:
        # Esegui il comando sudo systemctl per riavviare il servizio wifi
        command = 'sudo systemctl restart wpa_supplicant.service'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to restart wifi'})

        return jsonify({'message': 'Wifi restarted successfully'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@wifiutils_bp.route('/wifi/interface', methods=['GET'])
def get_interface():
    try:
        # Esegui il comando ip route per ottenere la tabella di routing e filtrare l'interfaccia di default
        command = "ip route | awk '/^default/ {print $5}'"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get interface'})

        # Restituisci l'interfaccia di default
        return jsonify({'interface': output.decode().strip()})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})