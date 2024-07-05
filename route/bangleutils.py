# BEGIN: 

from flask import Blueprint, jsonify, request
import subprocess
import re
import sys
import asyncio
from bleak import BleakClient, BleakError
import threading
import aiofiles
import json

bangleutils_bp = Blueprint('bangleutils', __name__)
bangle_metadata_filename = "./BangleApps/apps/widnextercare/metadata.json"
puck_metadata_filename = "./EspruinoApps/apps.json"

def get_latest_bangle_ver():
	with open(bangle_metadata_filename, 'r') as mf:
		metadata = json.loads(mf.read())
		return metadata["version"]

def get_latest_puck_ver():
	with open(puck_metadata_filename, 'r') as mf:
		metadata = json.loads(mf.read())
		return metadata[0]["version"]

@bangleutils_bp.route('/getlatestv', methods=['POST'])
def getlatestv():
    """
    Get latest version of Bangle/puck

    """
    try:
        from flask import request
        data = request.get_json()
        dev_type = data['dev_type']
        
        if dev_type == 'bangle':
            v = get_latest_bangle_ver()
        elif dev_type == 'puck':
            v = get_latest_puck_ver()    
        print(v)
        return jsonify({'v': v})
    
    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})


@bangleutils_bp.route('/bangle/ota', methods=['POST'])
def bangle_ota():
    """
    Ota update Bangle device

    """
    try:
        from flask import request
        data = request.get_json()
        mac = data['mac']
        lang = data.get('lang', '')
        justUpdateLang = data.get('justUpdateLang', '')
        
        # Avvia la funzione run in un thread separato e attendi il suo completamento
        thread = threading.Thread(target=run_sync, args=(b"reset(false);\n", mac,))
        thread.start()
        thread.join()
                
        # Execute the command
        print(f'bangle ota {mac}')
        sys.stdout.flush()
        command1 = '/root/.nvm/versions/node/v18.20.2/bin/node index.js ' + mac + ((' 0 0 ' + lang + ' 1') if (justUpdateLang != '') else '' )
        process1 = subprocess.Popen(command1, shell=True, cwd='./route/BangleOTA/', stderr=subprocess.PIPE)
        _, error = process1.communicate()
        
        thread = threading.Thread(target=run_sync, args=(b"E.reboot();\n", mac,))
        thread.start()
        thread.join()
        
        if process1.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to ota update bangle: ' + error.decode('utf-8')})
        else:
            return jsonify({'message': 'Bangle ota update completed'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})


@bangleutils_bp.route('/puck/ota', methods=['POST'])
def puck_ota():
    """
    Ota update Puck device

    """
    try:
        from flask import request
        data = request.get_json()
        mac = data['mac']
        lang = 'puck'
        
        # Execute the command
        print(f'puck ota {mac}')
        sys.stdout.flush()
        
        # Avvia la funzione run in un thread separato e attendi il suo completamento
        thread = threading.Thread(target=run_sync, args=(b"reset(false);\n", mac,))
        thread.start()
        thread.join()
        
        command1 = '/root/.nvm/versions/node/v18.20.2/bin/node index.js ' + mac + ' 0 0 ' + lang
        process1 = subprocess.Popen(command1, shell=True, cwd='./route/BangleOTA/', stderr=subprocess.PIPE)
        _, error = process1.communicate()
        
        thread = threading.Thread(target=run_sync, args=(b"E.reboot();\n", mac,))
        thread.start()
        thread.join()
        
        if process1.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to ota update bangle: ' + error.decode('utf-8')})
        else:
            return jsonify({'message': 'Bangle ota update completed'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})
    
@bangleutils_bp.route('/updatetime', methods=['POST'])
def update_time():
    """
    Update time of bangle/puck

    """
    try:
        from flask import request
        data = request.get_json()
        mac = data['mac']
        dev_type = data['dev_type']
        
        # Execute the command
        print(f'update time {mac}')
        sys.stdout.flush()
        command1 = '/root/.nvm/versions/node/v18.20.2/bin/node updatetime.js ' + mac + ' ' + dev_type
        process1 = subprocess.Popen(command1, shell=True, cwd='./route/BangleOTA/', stderr=subprocess.PIPE)
        _, error = process1.communicate()
        if process1.returncode != 0:
            # Return an error message if the command failed
            return jsonify({'error': 'Failed to ota update bangle: ' + error.decode('utf-8')})
        else:
            return jsonify({'message': 'Bangle ota update completed'})

    except Exception as e:
        # Return an error message if an exception occurred
        return jsonify({'[Exception] error': str(e)})

def uart_data_received(sender, data):
    print("RX> {0}".format(data))
    
async def run(cmd, address, attempt=1):
    # variabili per hard reset
    UUID_NORDIC_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    UUID_NORDIC_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
    max_attempts = 5

    print(f"Tentativo {attempt} di connessione a {address}...")
    client = BleakClient(address)

    try:
        await client.connect()
        print("Connected")
        await client.start_notify(UUID_NORDIC_RX, uart_data_received)
        print("Writing command")
        await client.write_gatt_char(UUID_NORDIC_TX, cmd, True)
        print("Waiting for data")
        await asyncio.sleep(1.5)  # Attesa per eventuali dati in arrivo
        #await client.write_gatt_char(UUID_NORDIC_TX, command3, True)
        #print("Waiting for data")
        #await asyncio.sleep(1.5)  # Attesa per eventuali dati in arrivo
        await client.stop_notify(UUID_NORDIC_RX)
    except BleakError as e:
        if ("org.bluez.Error.InProgress" in str(e) or "bleak.exc.BleakDeviceNotFoundError" in str(e)) and attempt < max_attempts:
            print("Operazione in corso, attendere...")
            await asyncio.sleep(1)  # attendi un secondo
            await run(cmd, address, attempt + 1)  # incrementa il contatore dei tentativi e riprova
        else:
            print(f"Errore durante la connessione: {e}")
            if attempt == max_attempts:
                print("Raggiunto il numero massimo di tentativi. Connessione fallita.")
            raise
    finally:
        if client.is_connected:
            print("Disconnecting...")
            await client.disconnect()
            print("Disconnected")
        await asyncio.sleep(5)  # Questo sleep aggiuntivo assicura un'attesa dopo la disconnessione, se necessario

def run_sync(cmd, address):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run(cmd, address))
    loop.close()