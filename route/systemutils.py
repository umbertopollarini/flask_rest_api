import subprocess
from flask import Blueprint, jsonify
import datetime

systemutils_bp = Blueprint('systemutils', __name__)

@systemutils_bp.route('/reboot', methods=['POST'])
def reboot_system():
    try:
        # Esegui il comando per riavviare il sistema
        command = f'sudo reboot'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode != 0:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to reboot system'})

        return jsonify({'message': 'System rebooted successfully'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})
    
@systemutils_bp.route('/get-time', methods=['GET'])
def get_time():
    try:
        # Ottieni l'orario corrente
        current_time = datetime.datetime.now()
        
        # Restituisci l'orario in formato JSON
        return jsonify({
            'time': current_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

@systemutils_bp.route('/check-voltage', methods=['GET'])
def check_voltage():
    try:
        # Ottieni l'orario di avvio del sistema
        uptime_command = "uptime -s"
        process_uptime = subprocess.Popen(uptime_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        uptime_output, uptime_error = process_uptime.communicate()
        system_start_time = datetime.datetime.strptime(uptime_output.decode().strip(), '%Y-%m-%d %H:%M:%S')

        # Esegui il comando dmesg per ottenere log relativi al voltaggio
        dmesg_command = "dmesg | grep -i voltage"
        process_dmesg = subprocess.Popen(dmesg_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        dmesg_output, dmesg_error = process_dmesg.communicate()

        if process_dmesg.returncode != 0:
            return jsonify({'error': 'Failed to fetch voltage logs'})

        # Analizza l'output e convertilo in timestamp leggibili
        output_lines = dmesg_output.decode('utf-8').strip().split('\n')
        formatted_logs = []
        for line in output_lines:
            parts = line.split(']')
            seconds_since_start = float(parts[0].strip('[').strip())
            event_time = system_start_time + datetime.timedelta(seconds=seconds_since_start)
            formatted_logs.append({
                'timestamp': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                'message': parts[1].strip()
            })

        return jsonify({
            'voltage_logs': formatted_logs
        })

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})
