from flask import Blueprint, jsonify, request
import sqlite3
import json


# Define the blueprint
calibration_bp = Blueprint('calibration', __name__)

@calibration_bp.route('/calibration/get_calibration_details', methods=['GET'])
def get_calibration_details():
    # Path to the SQLite database
    database_path = '/home/pi/shared_dir/positioning.db'
    
    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Query to select all data from the calibration_details table
    query = "SELECT * FROM calibration_details"  # Make sure the table name is correct

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Define column names (adjust based on your actual table structure)
        columns = ['id', 'name', 'timestamp', 'description', 'device', 'accuracy']
        
        # Convert fetched data into a list of dictionaries to jsonify
        results = [dict(zip(columns, row)) for row in rows]
        
        # Return the results as JSON
        return jsonify(results)
    
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Close the database connection
        cursor.close()
        conn.close()

# Remember to register the blueprint in your main Flask application

@calibration_bp.route('/calibration/get_room_stats/<int:calibration_id>', methods=['GET'])
def get_room_stats(calibration_id):
    database_path = '/home/pi/shared_dir/positioning.db'
    config_path = '/home/pi/shared_dir/config.json'
    
    # Load and parse the JSON file for device information
    with open(config_path, 'r') as file:
        config_data = json.load(file)
        devices = {device['mac']: device['name'] for device in config_data['devices']}
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Updated query remains the same
    query = """
        SELECT 
    r.room_name AS stanza,
    b.mac_bs AS mac,
    ROUND(AVG(b.mean), 2) AS media_rssi,
    ROUND((100.0 * b.count / MAX(b.count) OVER(PARTITION BY b.room_id)), 2) AS percentuale_rilevazioni,
    MIN(b.min) AS minimo,
    MAX(b.max) AS massimo,
    rs.time AS tempo_secondi_stanza,
    SUM(b.count) AS count_rilevazioni
FROM 
    bs_stats b
INNER JOIN 
    rooms_info r ON b.room_id = r.id
INNER JOIN 
    calibration_details c ON b.calibration_id = c.id
INNER JOIN
    room_stats rs ON rs.calibration_id = c.id AND CAST(rs.room AS INTEGER) = r.id
WHERE 
    c.id = ?
GROUP BY 
    b.room_id, b.mac_bs, rs.time
ORDER BY                
    r.room_name, percentuale_rilevazioni DESC;

    """
    
    try:
        cursor.execute(query, (calibration_id,))
        rows = cursor.fetchall()
        
        # Include device name lookup in the result
        columns = ['stanza', 'mac', 'media_rssi', 'percentuale_rilevazioni', 'minimo', 'massimo', 'tempo_secondi_stanza', 'count_rilevazioni', 'nome_dispositivo']
        results = []
        for row in rows:
            row_list = list(row)
            device_name = devices.get(row_list[1], 'Nome non trovato')  # Lookup the device name using MAC address
            row_list.append(device_name)
            results.append(dict(zip(columns, row_list)))
        
        return jsonify(results)
    
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

