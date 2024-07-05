from flask import Blueprint, jsonify, request
import os
import json
import time
from datetime import datetime, timedelta
import pymysql.cursors
import sqlite3
import subprocess

currentconfig_bp = Blueprint('currentconfig', __name__)

@currentconfig_bp.route('/current/config')
def get_current_config():
    """
    Get the current configuration from the server.

    Returns:
        Flask response: A JSON object containing the contents of the /home/pi/shared_dir/config.json file.
    """
    config_path = '/home/pi/shared_dir/config.json'

    if not os.path.exists(config_path):
        return jsonify({'error': 'Config file not found'})

    with open(config_path, 'r') as f:
        config_data = json.load(f)
        return jsonify(config_data)

@currentconfig_bp.route('/current/brconfig')
def get_current_conf():
    """
    Get the current br config.

    Returns:
        Br config configuration
    """
    try:
        with open('/home/pi/shared_dir/config.json', 'r') as file:
            data = json.load(file)
            br_info = data.get('brInfo', None)
            if br_info:
                return jsonify({"br_info": br_info})
            else:
                return jsonify({"br_info": "not configured yet"})
    except FileNotFoundError:
        return jsonify({"br_info": "not configured yet"})

@currentconfig_bp.route('/current/devices')
def get_current_devices():
    """
    Get the current devices in the network along with their battery history.

    Returns:
        Return a list of devices in the network with their battery history.
    """
    config_path = '/home/pi/shared_dir/config.json'
    device_data_path = '/home/pi/shared_dir/deviceData.json'

    if not os.path.exists(config_path):
        return jsonify({"error": "Config file not found"})

    if not os.path.exists(device_data_path):
        return jsonify({"error": "Device data file not found"})

    try:
        with open(config_path, 'r') as file:
            devices_data = json.load(file)
            devices = devices_data.get('devices', [])

        with open(device_data_path, 'r') as file:
            device_data = json.load(file)

        # Create a mapping of MAC address to battery history for quick lookup
        device_data_mapping = {}
        for data in device_data:
            mac_address = data['mac']
            if mac_address not in device_data_mapping:
                device_data_mapping[mac_address] = []
            device_data_mapping[mac_address].append(data)

        # Append battery history to each device
        for device in devices:
            mac_address = device['mac']
            if mac_address in device_data_mapping:
                device['history'] = device_data_mapping[mac_address]

        return jsonify({"devices": devices})

    except FileNotFoundError as e:
        return jsonify({"error": str(e)})
    
@currentconfig_bp.route('/current/devicesInfoOnly')
def get_current_devices_only():
    """
    Get the current devices only infos in the network.

    Returns:
        Return a list of devices in the network.
    """
    config_path = '/home/pi/shared_dir/config.json'

    if not os.path.exists(config_path):
        return jsonify({"error": "Config file not found"})

    try:
        with open(config_path, 'r') as file:
            devices_data = json.load(file)
            devices = devices_data.get('devices', [])
        
        return jsonify({"devices": devices})

    except FileNotFoundError as e:
        return jsonify({"error": str(e)})

@currentconfig_bp.route('/current/coap_brssi')
def get_coap_brssi():
    """
    Get the COAP BRSSI information from the server.

    Returns:
        Flask response: A JSON object containing the contents of the /shared_dir/coap_brssi.json file.
    """
    coap_brssi_path = '/home/pi/shared_dir/coap_brssi.json'

    if not os.path.exists(coap_brssi_path):
        return jsonify({'error': 'COAP BRSSI file not found'}), 404

    try:
        with open(coap_brssi_path, 'r') as file:
            coap_brssi_data = json.load(file)
        return jsonify(coap_brssi_data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Error decoding JSON data'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@currentconfig_bp.route('/current/devicestatus', methods=['POST'])
def update_device_status():
    """
    Updates the device status based on the provided MAC address and status.
    """
    # Legge i dati inviati dal client
    data = request.get_json()
    mac_address = data.get('macAddress')
    new_status = data.get('status')

    config_path = '/home/pi/shared_dir/config.json'

    if not os.path.exists(config_path):
        return jsonify({'error': 'Config file not found'}), 404

    try:
        # Carica i dati esistenti da config.json
        with open(config_path, 'r') as file:
            config_data = json.load(file)
        
        # Controlla se l'elenco dei dispositivi è presente
        devices = config_data.get('devices', [])
        device_found = False

        # Aggiorna lo status del dispositivo corrispondente
        for device in devices:
            if device['mac'] == mac_address:
                device['status'] = new_status
                device_found = True
                break
        
        if not device_found:
            return jsonify({'error': 'Device with specified MAC address not found'}), 404

        # Salva i dati aggiornati in config.json
        with open(config_path, 'w') as file:
            json.dump(config_data, file, indent=4)

        return jsonify({'message': 'Device status updated successfully'})

    except json.JSONDecodeError:
        return jsonify({'error': 'Error decoding JSON data'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# CHIAMATE XSITE PER DB SQL LITE
def get_db_connection():
    conn = sqlite3.connect('/home/pi/shared_dir/DATISTORICI.db') 
    conn.row_factory = sqlite3.Row  
    return conn

# CHIAMATE XSITE PER DB SQL LITE POSITIONING
def get_db_positioning_connection():
    conn = sqlite3.connect('/home/pi/shared_dir/positioning.db') 
    conn.row_factory = sqlite3.Row  
    return conn

def read_device_config():
    config_path = '/home/pi/shared_dir/config.json'
    if not os.path.exists(config_path):
        return None, "Config file not found"
    with open(config_path, 'r') as f:
        config_data = json.load(f)
        return config_data.get('devices', []), None

@currentconfig_bp.route('/current/devices_sql')
def get_current_devices_sql():
    days = request.args.get('days', default=1, type=int)  # Get 'days' from the query parameters
    devices, error = read_device_config()
    if error:
        return jsonify({"error": error}), 404

    # Type to table name mapping
    type_to_table = {
        'bs02': 'datistorici_bs02',
        'banglejs2': 'datistorici_bangle',
        'puckjs2': 'datistorici_puck'
    }

    # Calculate the date N days ago from today
    n_days_ago = datetime.now() - timedelta(days=days)
    timestamp_n_days_ago = int(n_days_ago.timestamp())  # Convert to timestamp

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for device in devices:
            device_type = device['type']
            table_name = type_to_table.get(device_type.lower())
            if not table_name:
                continue  # Skip if no valid table mapping exists

            mac_address = device['mac']
            sql_query = f"""
            SELECT * FROM {table_name}
            WHERE mac = '{mac_address}' AND timestamp >= {timestamp_n_days_ago}
            ORDER BY timestamp DESC
            """
            cursor.execute(sql_query)
            device_history = cursor.fetchall()
            device['history'] = [dict(row) for row in device_history]  # Convert rows to dictionaries
        return jsonify({"devices": devices})
    finally:
        conn.close()

@currentconfig_bp.route('/current/bangle_info')
def get_bangle_info():
    mac_address = request.args.get('macAddress')
    duration = request.args.get('duration', type=int)

    if not mac_address:
        return jsonify({"error": "MAC address is required"}), 400

    if duration is None:
        return jsonify({"error": "Duration is required"}), 400

    try:
        # Connetti al database SQLite
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calcola il timestamp di n ore fa basato sulla durata fornita
        n_hours_ago = datetime.now() - timedelta(hours=duration)
        n_hours_ago_timestamp = int(n_hours_ago.timestamp())

        # Esegui la query per ottenere i dati
        cursor.execute('''
            SELECT * FROM datistorici_positioning
            WHERE macBangle = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (mac_address, n_hours_ago_timestamp))

        # Estrapola tutti i risultati della query
        entries = cursor.fetchall()
        conn.close()

        if entries:
            # Converti i risultati in un formato JSON
            data = [dict(entry) for entry in entries]
            return jsonify(data)
        else:
            return jsonify({"error": f"No entries found for the specified MAC address within the last {duration} hours"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@currentconfig_bp.route('/current/table_counts')
def get_table_counts():
    # Funzione per ottenere statistiche dettagliate di un database specifico
    def get_db_stats(db_name, db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            # Ottieni l'elenco delle tabelle
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            table_info = {}
            total_db_size_kb = 0
            
            for table in tables:
                table_name = table['name']
                
                # Ottieni il numero di record
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()['count']
                
                # Calcola la dimensione della tabella in kilobytes
                cursor.execute(f"""
                    SELECT SUM(pgsize) as size
                    FROM dbstat
                    WHERE name = '{table_name}'
                """)
                size = cursor.fetchone()['size']
                
                table_size_kb = size / 1024 if size else 0
                total_db_size_kb += table_size_kb

                try:
                    # Ottieni il timestamp dell'ultimo salvataggio
                    cursor.execute(f"SELECT MAX(timestamp) as last_timestamp FROM {table_name}")
                    last_timestamp = cursor.fetchone()['last_timestamp']
                    if last_timestamp:
                        last_saved = datetime.fromtimestamp(int(last_timestamp)).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    last_saved = "No data"
                
                table_info[table_name] = {
                    "record": count,
                    "size": table_size_kb,
                    "lastSaved": last_saved
                }

            # Ottieni la data di creazione del database utilizzando il comando 'stat'
            if os.path.exists(db_path):
                result = subprocess.run(['stat', '-c', '%w', db_path], capture_output=True, text=True)
                creation_date = result.stdout.strip()
                if creation_date == '-':
                    # If the creation date is not available, fallback to modification date
                    creation_date = datetime.fromtimestamp(os.path.getctime(db_path)).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    creation_date = creation_date.split('.')[0]  # Truncate to seconds
                db_creation_date = creation_date
            else:
                db_creation_date = "Unknown"

            # Calcola totalActiveDays
            if db_creation_date != "Unknown":
                db_creation_datetime = datetime.strptime(db_creation_date, '%Y-%m-%d %H:%M:%S')
                total_active_days = (datetime.now() - db_creation_datetime).days
            else:
                total_active_days = 0

            
            # Calcola totalDBDimension
            total_db_dimension = f"{total_db_size_kb / 1024:.2f} MB" if total_db_size_kb > 1000 else f"{total_db_size_kb:.2f} KB"

            return {
                "dbDate": db_creation_date,
                "tableDatas": table_info,
                "totalActiveDays": total_active_days,
                "totalDBDimension": total_db_dimension
            }
        finally:
            conn.close()

    # Percorsi dei database
    historic_db_path = '/home/pi/shared_dir/DATISTORICI.db'
    positioning_db_path = '/home/pi/shared_dir/positioning.db'
    
    # Ottieni statistiche per ciascun database
    historic_stats = get_db_stats("DATISTORICI.db", historic_db_path)
    positioning_stats = get_db_stats("positioning.db", positioning_db_path)

    return jsonify({"DATISTORICI.db": historic_stats, "positioning.db": positioning_stats})
    
@currentconfig_bp.route('/current/bangle_live_connection')
def get_bangle_live_connection():
    mac_address = request.args.get('macAddress')
    duration = request.args.get('duration', type=int)

    if not mac_address:
        return jsonify({"error": "MAC address is required"}), 400

    if duration is None:
        return jsonify({"error": "Duration is required"}), 400

    try:
        # Connect to the SQLite database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calculate the timestamp of n hours ago based on the provided duration
        n_hours_ago = datetime.now() - timedelta(hours=duration)
        n_hours_ago_timestamp = int(n_hours_ago.timestamp())
        current_timestamp = int(datetime.now().timestamp())

        # Execute the query to get the data
        cursor.execute('''
            SELECT * FROM datilive_bangle
            WHERE mac = ? AND (timestampInizio >= ? OR timestampFine >= ?)
            ORDER BY timestampInizio, timestampFine
        ''', (mac_address, n_hours_ago_timestamp, n_hours_ago_timestamp))

        # Fetch all query results
        entries = cursor.fetchall()
        conn.close()

        connection_intervals = []
        if entries:
            device_types = set()
            for entry in entries:
                entry_dict = dict(entry)
                entry_type = entry_dict.get('type', 'unknown')
                device_types.add(entry_type)
                if entry_dict['timestampInizio']:
                    timestamp_inizio = int(entry_dict['timestampInizio'])
                    # Add a point one second before with status 0
                    connection_intervals.append({
                        "timestamp": timestamp_inizio - 1,
                        "status": 0,
                        "type": entry_type
                    })
                    # Add the start point with status 1
                    connection_intervals.append({
                        "timestamp": timestamp_inizio,
                        "status": 1,
                        "type": entry_type
                    })
                if entry_dict['timestampFine']:
                    timestamp_fine = int(entry_dict['timestampFine'])
                    # Add the end point with status 1
                    connection_intervals.append({
                        "timestamp": timestamp_fine,
                        "status": 1,
                        "type": entry_type
                    })
                    # Add a point one second after with status 0
                    connection_intervals.append({
                        "timestamp": timestamp_fine + 1,
                        "status": 0,
                        "type": entry_type
                    })

            # Sort the connection_intervals list by timestamp
            connection_intervals.sort(key=lambda x: x["timestamp"])

            # Check for each type if there is a point at the start of the duration
            first_entry_timestamp = connection_intervals[0]["timestamp"]
            if first_entry_timestamp > n_hours_ago_timestamp:
                for device_type in device_types:
                    connection_intervals.insert(0, {
                        "timestamp": n_hours_ago_timestamp,
                        "status": 0,
                        "type": device_type
                    })

            # Check for each type if there is a point at the end of the duration
            last_entries_by_type = {}
            for interval in connection_intervals:
                last_entries_by_type[interval['type']] = interval

            for device_type in device_types:
                last_entry = last_entries_by_type.get(device_type)
                if last_entry and last_entry['timestamp'] < current_timestamp:
                    connection_intervals.append({
                        "timestamp": current_timestamp,
                        "status": last_entry['status'],
                        "type": device_type
                    })

        else:
            # If no entries, add a single point with status 0 for each device type
            device_types = set(entry.get('type', 'unknown') for entry in entries)
            for device_type in device_types:
                connection_intervals.append({
                    "timestamp": n_hours_ago_timestamp,
                    "status": 0,
                    "type": device_type
                })
                connection_intervals.append({
                    "timestamp": current_timestamp,
                    "status": 0,
                    "type": device_type
                })

        return jsonify(connection_intervals)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import jsonify, request
from datetime import datetime, timedelta
import sqlite3

@currentconfig_bp.route('/current/livepositioning')
def get_live_positioning():
    mac_address = request.args.get('macAddress')
    duration = request.args.get('duration', type=int)

    if not mac_address:
        return jsonify({"error": "MAC address is required"}), 400

    if duration is None:
        return jsonify({"error": "Duration is required"}), 400

    try:
        conn = get_db_positioning_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, room_name, color, coordinates, floor_id, floor_name, attr1, attr2, attr3, attr4, roles, timestamp FROM rooms_info
        ''')
        room_entries = cursor.fetchall()
        room_mapping = {str(entry['id']): {key: entry[key] for key in entry.keys()} for entry in room_entries}
        
        n_hours_ago = datetime.now() - timedelta(hours=duration)
        n_hours_ago_timestamp = int(n_hours_ago.timestamp())

        cursor.execute('''
            SELECT * FROM predictions
            WHERE mac_device = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (mac_address, n_hours_ago_timestamp))

        entries = cursor.fetchall()
        conn.close()

        if entries:
            # Check if the earliest entry is after n_hours_ago_timestamp
            earliest_timestamp = int(entries[0]['timestamp'])
            data = []
            seen_ids = set()

            # If the first actual data point is later than n_hours_ago, add an unknown room entry
            if earliest_timestamp > n_hours_ago_timestamp:
                unknown_room_data = {
                    'timestamp': n_hours_ago_timestamp,
                    'predicted_room': 'Unknown Room',
                    'room_name': 'Unknown Room',
                    'floor_name': 'Unknown Floor',
                    'floor_id': 'Unknown Floor ID',
                    'confidence': '0.0'
                }
                data.append(unknown_room_data)

            for entry in entries:
                entry_id = entry['id']
                # controllo che non abbia già visto l'id
                if entry_id not in seen_ids:
                    seen_ids.add(entry_id)
                    # entry_dict è la riga della prediction
                    entry_dict = {key: entry[key] for key in entry.keys()}
                    room_id = entry_dict['predicted_room']
                    room_info = room_mapping.get(str(room_id), {'room_name': 'Unknown Room', 'floor_name': 'Unknown Floor', 'floor_id': 'Unknown Floor ID'})
                    
                    entry_dict["room_name"] = room_info["room_name"]
                    entry_dict["floor_name"] = room_info["floor_name"]
                    
                    data.append(entry_dict)

            return jsonify({"data": data, "rooms": room_mapping})
        else:
            return jsonify({"error": f"No entries found for the specified MAC address within the last {duration} hours", "rooms": room_mapping}), 404
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@currentconfig_bp.route('/current/diceface')
def get_dice_face_data():
    from flask import jsonify, request
    import sqlite3
    from datetime import datetime, timedelta

    mac_address = request.args.get('macAddress')
    duration = request.args.get('duration', type=int)

    if not mac_address:
        return jsonify({"error": "MAC address is required"}), 400

    if duration is None:
        return jsonify({"error": "Duration is required"}), 400

    # Calcola il timestamp di n ore fa basato sulla durata fornita
    n_hours_ago = datetime.now() - timedelta(hours=duration)
    n_hours_ago_timestamp = int(n_hours_ago.timestamp())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Esegui la query per ottenere i dati
        cursor.execute('''
            SELECT id, mac, face, timestamp
            FROM diceface
            WHERE mac = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (mac_address, n_hours_ago_timestamp))

        # Estrapola tutti i risultati della query e converti il timestamp in intero
        entries = [{'id': row[0], 'mac': row[1], 'face': row[2], 'timestamp': int(row[3])} for row in cursor.fetchall()]
        conn.close()

        # Verifica se ci sono dati per l'intero intervallo richiesto
        if len(entries) > 0 and (entries[0]['timestamp'] > n_hours_ago_timestamp):
            # Aggiungi un punto con valore predefinito all'inizio dell'intervallo se non ci sono dati o sono incompleti
            entries.insert(0, {'id': None, 'mac': mac_address, 'face': 0, 'timestamp': n_hours_ago_timestamp})

        # Prepara i dati per il grafico
        points = [{"id": entry['id'], "mac": entry['mac'], "face": entry['face'], "timestamp": entry['timestamp']} for entry in entries]
        return jsonify(points)
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@currentconfig_bp.route('/current/bs02_status')
def get_bs02_status():
    config_path = '/home/pi/shared_dir/config.json'
    current_time = datetime.now()

    try:
        # Carica i dati da config.json
        with open(config_path, 'r') as file:
            config_data = json.load(file)
            devices = [device for device in config_data.get('devices', []) if device['type'].lower() == 'bs02']

        # Apri una connessione al database
        conn = get_db_connection()
        cursor = conn.cursor()

        results = []
        # Verifica lo stato per ogni dispositivo bs02
        for device in devices:
            mac_address = device['mac']
            # Recupera l'ultimo dato dal database
            cursor.execute("""
                SELECT * FROM datistorici_bs02
                WHERE mac = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (mac_address,))
            last_entry = cursor.fetchone()

            if last_entry:
                # Converti timestamp UNIX in datetime
                last_timestamp = datetime.fromtimestamp(int(last_entry['timestamp']))
                delta_minutes = (current_time - last_timestamp).total_seconds() / 60

                # Definisci lo stato basato sul tempo trascorso
                if delta_minutes < 20:
                    status = 1
                elif delta_minutes < 45:
                    status = 2
                else:
                    status = 3

                battery_level = last_entry['l']
            else:
                status = 3
                battery_level = "0"

            # Aggiungi i risultati alla lista
            results.append({
                "macBS02": mac_address,
                "status": status,
                "battery": battery_level
            })

        return jsonify(results)
    
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding JSON data"}), 500
    except FileNotFoundError:
        return jsonify({"error": "Config file not found"}), 404
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@currentconfig_bp.route('/current/logdevices')
def get_log_devices():
    mac_address = request.args.get('macAddress')
    duration = request.args.get('duration', type=int)

    if not mac_address:
        return jsonify({"error": "MAC address is required"}), 400

    if duration is None:
        return jsonify({"error": "Duration is required"}), 400

    # Calculate the timestamp for the duration provided
    n_hours_ago = datetime.now() - timedelta(days=duration)
    n_hours_ago_timestamp = int(n_hours_ago.timestamp())

    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute the query to fetch log messages for the specified device and duration
        cursor.execute('''
            SELECT id, mac, type, timestamp
            FROM logdevices
            WHERE mac = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (mac_address, n_hours_ago_timestamp))

        # Fetch all query results
        entries = cursor.fetchall()
        conn.close()

        # Convert query results to a JSON-compatible format
        logs = [{'id': row['id'], 'mac': row['mac'], 'type': row['type'], 'timestamp': row['timestamp']} for row in entries]

        # Check if there are entries and handle the case where the first log is later than the start timestamp
        if len(logs) == 0:
            logs.insert(0, {'id': None, 'mac': mac_address, 'type': 'No logs before this point', 'timestamp': n_hours_ago_timestamp})

        return jsonify(logs)
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@currentconfig_bp.route('/current/devices_timestamps')
def get_devices_timestamps():
    devices, error = read_device_config()
    if (error):
        return jsonify({"error": error}), 404

    # Filter out devices of type "bs02"
    devices = [device for device in devices if device['type'].lower() != 'bs02']

    try:
        conn = get_db_connection()

        cursor = conn.cursor()

        result = {}

        for device in devices:
            mac_address = device['mac']
            last_timestamp_puck = None
            last_timestamp_positioning = None

            # Get last timestamp from datistorici_* table
            if (device['type'] == "puckjs2"):
                cursor.execute('''
                SELECT timestamp
                FROM datistorici_puck
                WHERE mac = ?
                ORDER BY timestamp DESC
                LIMIT 1
                ''', (mac_address,))
                last_timestamp_puck_row = cursor.fetchone()
                last_timestamp_puck = int(last_timestamp_puck_row['timestamp']) if last_timestamp_puck_row else None
            elif (device['type'] == "banglejs2"):
                cursor.execute('''
                SELECT timestamp
                FROM datistorici_bangle
                WHERE mac = ?
                ORDER BY timestamp DESC
                LIMIT 1
                ''', (mac_address,))
                last_timestamp_puck_row = cursor.fetchone()
                last_timestamp_puck = int(last_timestamp_puck_row['timestamp']) if last_timestamp_puck_row else None

            # Get last timestamp from datistorici_positioning table
            cursor.execute('''
                SELECT timestamp
                FROM datistorici_positioning
                WHERE macBangle = ? AND rssiBangle != 0
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (mac_address,))
            last_timestamp_positioning_row = cursor.fetchone()
            last_timestamp_positioning = int(last_timestamp_positioning_row['timestamp']) if last_timestamp_positioning_row else None

            result[mac_address] = {
                "ipv6": device.get("ipv6", ""),
                "last_timestamp_positioning": last_timestamp_positioning,
                "last_timestamp_puck": last_timestamp_puck,
                "location": device.get("location", ""),
                "name": device.get("name", ""),
                "type": device.get("type", ""),
                "user_id": device.get("user_id", ""),
                "v": device.get("v", "")
            }

        return jsonify(result)

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    finally:
        conn.close()
