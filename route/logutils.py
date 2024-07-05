from flask import Blueprint, send_file, jsonify
import os

logutils_bp = Blueprint('logutils', __name__)

@logutils_bp.route('/logs/download/<filename>')
def download_log_file(filename):
    """
    Download a log file from the server.

    Args:
        filename (str): The name of the log file to download.

    Returns:
        Flask response: The log file as an attachment if it exists, or an error message if it doesn't.
    """
    log_dir = '/var/log'
    log_path = os.path.join(log_dir, filename)

    if not os.path.exists(log_path):
        return jsonify({'error': 'Log file not found'})

    return send_file(log_path, as_attachment=True)

@logutils_bp.route('/logs')
def get_log_files():
    """
    Get a list of all log files on the server.

    Returns:
        Flask response: A JSON object containing a list of all log files on the server.
    """
    log_dir = '/var/log'
    log_files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    return jsonify(log_files)

@logutils_bp.route('/logs/<filename>')
def get_log_file(filename):
    """
    Get the last 20 lines of a log file.

    Args:
        filename (str): The name of the log file to get.

    Returns:
        Flask response: The last 50 lines of the log file if it exists, or an error message if it doesn't.
    """
    log_dir = '/var/log'
    log_path = os.path.join(log_dir, filename)

    if not os.path.exists(log_path):
        return jsonify({'error': 'Log file not found'})

    with open(log_path, 'r') as f:
        lines = f.readlines()
        last_50_lines = lines[-20:]
        return jsonify(last_50_lines)
