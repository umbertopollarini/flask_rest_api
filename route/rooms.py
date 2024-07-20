from flask import Blueprint, jsonify, request
import sqlite3
import json
import datetime
import netifaces
import base64
from firebase_admin import credentials, firestore, initialize_app

# Define the blueprint
rooms_bp = Blueprint('rooms', __name__)
cred = credentials.Certificate('/home/pi/flaskrestapi/config_fb.json')
default_app = initialize_app(cred)
db = firestore.client()

@rooms_bp.route('/rooms/configurations')
def get_room_configurations():
    # Path to the SQLite database
    database_path = '/home/pi/shared_dir/positioning.db'
    
    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Query to check if the 'rooms_info' table exists
    table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='rooms_info';"
    
    try:
        cursor.execute(table_check_query)
        if cursor.fetchone():
            # If the table exists, fetch all its contents
            fetch_query = "SELECT * FROM rooms_info"
            cursor.execute(fetch_query)
            rows = cursor.fetchall()

            # Define column names (adjust these based on your actual table structure)
            columns = ['id', 'room_name', 'color', 'coordinates', 'floor_id', 'floor_name', 'attr1', 'attr2', 'attr3', 'attr4', 'roles',  'timestamp', 'floor_image']
            
            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['floor_image']:
                    row_dict['floor_image'] = base64.b64encode(row_dict['floor_image']).decode('utf-8')
                else:
                    row_dict['floor_image'] = None
                results.append(row_dict)
            return jsonify(results)
        else:
            # If the table does not exist
            return jsonify({"info": "There is no room and floor yet!"}), 200
    
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Close the database connection
        cursor.close()
        conn.close()

def get_mac_address(interface):
    try:
        mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
        return mac
    except KeyError:
        return None
        
@rooms_bp.route('/rooms/addfloor', methods=['POST'])
def add_floor():
    # Path to the SQLite database
    database_path = '/home/pi/shared_dir/positioning.db'
    
    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Query to check if the 'rooms_info' table exists, if not, create it
    table_creation_query = """
    CREATE TABLE IF NOT EXISTS rooms_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT,
        color TEXT,
        coordinates TEXT,
        floor_id TEXT,
        floor_name TEXT,
        attr1 TEXT, 
        attr2 TEXT, 
        attr3 TEXT, 
        attr4 TEXT, 
        roles TEXT,
        timestamp TEXT,
        floor_image BLOB
    );
    """
    
    # Execute table creation and check if the table was just created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms_info';")
    table_exists = cursor.fetchone()
    
    cursor.execute(table_creation_query)
    
    if not table_exists:
        # Table didn't exist and was created, now insert default row
        cursor.execute("""
        INSERT INTO rooms_info (id, room_name, color, coordinates, floor_id, floor_name, attr1, attr2, attr3, attr4, roles, timestamp, floor_image)
        VALUES (0, 'External', NULL, NULL, NULL, 'External', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
        """)

    # Get floor details from request
    floordetails = json.loads(request.form['floordetails'])
    floor_image_file = request.files['floorImage'] if 'floorImage' in request.files else None
    devices = json.loads(request.form.get('devices', '[]'))
    floor_image_data = floor_image_file.read()
    
    try:
        inserted_ids = []
        # Insert each floor detail into the database
        insert_query = """
        INSERT INTO rooms_info (room_name, color, coordinates, floor_id, floor_name, roles, attr1, attr2, attr3, attr4, timestamp, floor_image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        for detail in floordetails:
            cursor.execute(insert_query, (
                detail['room_name'],
                detail['color'],
                detail['coordinates'],
                detail['floor_id'],
                detail['floor_name'],
                json.dumps(detail['roles']),
                json.dumps(devices),
                None,
                None,
                None,
                str(round(datetime.datetime.now().timestamp())),
                floor_image_data
            ))
            inserted_ids.append(cursor.lastrowid)
        conn.commit()
        
        # Load organization_id from config
        with open('/home/pi/shared_dir/config.json', 'r') as config_file:
            config = json.load(config_file)
            organization_id = config['organization_id']
        
        # Get the MAC address of eth0
        mac_eth0 = get_mac_address('eth0')

        if not mac_eth0:
            return jsonify({"error": "Could not retrieve MAC address for eth0"}), 500

        # Update Firebase
        area_map = {str(inserted_ids[i]): str(floordetails[i]['room_name']) for i in range(len(floordetails))}
        firebase_path = f"organization/{str(organization_id)}/network/{str(mac_eth0)}/calibration/current/piani/{str(detail['floor_id'])}"
        doc_ref = db.document(firebase_path)
        doc_ref.set({"area": area_map, "nome": str(detail['floor_name'])}, merge=True)

        # Return success message
        return jsonify({"success": "Floor details added successfully."}), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        # Close the database connection
        cursor.close()
        conn.close()

@rooms_bp.route('/rooms/floors')
def get_floors():
    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        # Verifica che la tabella esista
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms_info';")
        if cursor.fetchone():
            # Estrae tutti i dati
            cursor.execute("SELECT * FROM rooms_info")
            rows = cursor.fetchall()
            columns = ['id', 'room_name', 'color', 'coordinates', 'floor_id', 'floor_name', 'attr1', 'attr2', 'attr3', 'attr4', 'roles', 'timestamp', 'floor_image']
            
            floors = {}
            for row in rows:
                row_dict = dict(zip(columns, row))
                # Controlla se l'immagine del piano esiste e la decodifica in base64 se presente
                if row_dict['floor_image']:
                    row_dict['floor_image'] = base64.b64encode(row_dict['floor_image']).decode('utf-8')
                else:
                    row_dict['floor_image'] = None

                # Raggruppa le informazioni per nome del piano
                floor_name = row_dict['floor_name']
                if floor_name in floors:
                    floors[floor_name]['areas'].append(row_dict)
                else:
                    floors[floor_name] = {
                        "floor_name": floor_name,
                        "id": row_dict['floor_id'],
                        "piantina": row_dict['floor_image'],
                        "timestamp": row_dict['timestamp'],
                        "areas": [row_dict]
                    }
                    
            # Converti i dati in una lista di oggetti per ogni piano
            floors_list = list(floors.values())
            return jsonify(floors_list)
        else:
            return jsonify({"info": "No room and floor data available."}), 200

    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@rooms_bp.route('/rooms/lastposition')
def get_last_positions():
    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Calcola il timestamp per 2 minuti fa
    two_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=2)
    two_minutes_ago_timestamp = two_minutes_ago.timestamp()

    try:
        # Verifica che la tabella esista
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions';")
        if cursor.fetchone():
            # Estrae i dati degli ultimi 2 minuti
            cursor.execute("""
                SELECT id, mac_device, predicted_room, confidence, timestamp
                FROM predictions
                WHERE timestamp >= ?
            """, (two_minutes_ago_timestamp,))
            rows = cursor.fetchall()

            # Se non ci sono righe, ritorna un messaggio appropriato
            if not rows:
                return jsonify({"info": "No data available for the last 2 minutes."}), 200

            # Altrimenti, prepara e ritorna i dati
            columns = ['id', 'mac_device', 'predicted_room', 'confidence', 'timestamp']
            results = [dict(zip(columns, row)) for row in rows]
            return jsonify(results)

        else:
            return jsonify({"info": "No predictions data available."}), 200

    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@rooms_bp.route('/rooms/deletefloor', methods=['POST'])
def delete_floor():
    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        # Get the floor_id from the request
        floor_id = request.json.get('id')
        if not floor_id:
            return jsonify({"error": "Floor ID is required"}), 400

        # Load organization_id from config to construct Firebase path
        with open('/home/pi/shared_dir/config.json', 'r') as config_file:
            config = json.load(config_file)
            organization_id = config['organization_id']

        # Get the MAC address of eth0
        mac_eth0 = get_mac_address('eth0')

        if not mac_eth0:
            return jsonify({"error": "Could not retrieve MAC address for eth0"}), 500

        # Construct Firebase path
        firebase_path = f"organization/{organization_id}/network/{mac_eth0}/calibration/current/piani/{floor_id}"

        # Delete the records with the specified floor_id in SQLite
        delete_query = "DELETE FROM rooms_info WHERE floor_id = ?"
        cursor.execute(delete_query, (floor_id,))
        conn.commit()

        # Delete the document in Firebase
        doc_ref = db.document(firebase_path)
        doc_ref.delete()

        return jsonify({"success": "Floor deleted successfully."}), 200

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Failed to delete the Firestore document: " + str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rooms_bp.route('/rooms/trackmovements', methods=['GET'])
def track_movements():
    mac_address = request.args.get('macAddress')
    duration_hours = request.args.get('duration', type=int)
    
    if not mac_address or duration_hours is None:
        return jsonify({"error": "MAC address and duration are required"}), 400
    
    # Convert hours to seconds for the timestamp calculation
    now = datetime.datetime.now()
    time_threshold = now - datetime.timedelta(hours=duration_hours)
    timestamp_threshold = time_threshold.timestamp()

    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        # Verify that the necessary tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions';")
        if not cursor.fetchone():
            return jsonify({"info": "Predictions data not available."}), 200
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms_info';")
        if not cursor.fetchone():
            return jsonify({"info": "Room information not available."}), 200
        
        # Fetch movements for the given MAC address within the specified time range
        query = """
        SELECT p.timestamp, r.room_name
        FROM predictions p
        JOIN rooms_info r ON p.predicted_room = r.id
        WHERE p.mac_device = ? AND p.timestamp >= ?
        ORDER BY p.timestamp DESC;
        """
        cursor.execute(query, (mac_address, timestamp_threshold))
        movements = cursor.fetchall()
        
        # Check if there are movements
        if not movements:
            return jsonify({"info": "No movements found for the given parameters."}), 200
        
        # Prepare data to be returned
        results = [{
            "room_name": movement[1],
            "timestamp": datetime.datetime.fromtimestamp(int(movement[0])).strftime('%Y-%m-%d %H:%M:%S')
        } for movement in movements]
        
        return jsonify(results)
    
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@rooms_bp.route('/rooms/iconroles', methods=['POST'])
def set_icon_roles():
    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rolesinfo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT UNIQUE,
            icon TEXT,
            attr1 TEXT,
            attr2 TEXT,
            attr3 TEXT,
            timestamp TEXT
        );
    """)

    # Get role and iconId from the request
    role = request.json.get('role')
    icon = request.json.get('iconId')

    if not role or not icon:
        return jsonify({"error": "Role and iconId are required"}), 400

    try:
        # Check if the role already exists in the database
        cursor.execute("SELECT icon FROM rolesinfo WHERE role = ?", (role,))
        existing_icon = cursor.fetchone()
        
        if existing_icon:
            # Update the existing role's icon
            cursor.execute("UPDATE rolesinfo SET icon = ?, timestamp = ? WHERE role = ?",
                           (icon, str(round(datetime.datetime.now().timestamp())), role))
        else:
            # Insert the new role and icon into the database
            cursor.execute("""
                INSERT INTO rolesinfo (role, icon, attr1, attr2, attr3, timestamp)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (role, icon, None, None, None, str(round(datetime.datetime.now().timestamp()))))
        
        conn.commit()
        return jsonify({"success": "Role icon updated successfully."}), 201 if not existing_icon else 200
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@rooms_bp.route('/rooms/geticonsroles', methods=['GET'])
def get_icons_roles():
    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        # Check if the 'rolesinfo' table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rolesinfo';")
        if not cursor.fetchone():
            return jsonify({"info": "No rolesinfo data available."}), 200
        
        # Fetch all rows from the 'rolesinfo' table
        fetch_query = "SELECT * FROM rolesinfo"
        cursor.execute(fetch_query)
        rows = cursor.fetchall()

        # Define column names based on the table structure
        columns = ['id', 'role', 'icon', 'attr1', 'attr2', 'attr3', 'timestamp']
        results = [dict(zip(columns, row)) for row in rows]
        
        return jsonify(results)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@rooms_bp.route('/rooms/geticonmac', methods=['GET'])
def get_icon_mac():
    # Carica i dati dal file config.json
    with open('/home/pi/shared_dir/config.json', 'r') as config_file:
        config = json.load(config_file)
    devices = config.get('devices', [])

    # Connetti al database SQLite
    database_path = '/home/pi/shared_dir/positioning.db'
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Verifica l'esistenza della tabella 'rolesinfo' e recupera le informazioni sulle icone dei ruoli
    cursor.execute("SELECT role, icon FROM rolesinfo")
    roles_icons = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Prepara i risultati filtrando solo i dispositivi non di tipo 'bs02' e mappando le icone basate sui ruoli
    filtered_devices = [
        {
            "mac": device['mac'],
            "name": device['name'],
            "role": device.get('role'),
            "icon": roles_icons.get(device.get('role'), 'HelpOutlineIcon')  # Usa 'HelpOutlineIcon' se il ruolo non è trovato
        }
        for device in devices if device['type'] != 'bs02'
    ]

    # Chiude la connessione al database
    cursor.close()
    conn.close()

    return jsonify(filtered_devices)
