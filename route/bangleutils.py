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