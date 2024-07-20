from flask import Flask
from flask_cors import CORS
import subprocess
import threading
import asyncio
import multiprocessing

from route.logutils import logutils_bp
from route.dockerutils import dockerutils_bp
from route.wifiutils import wifiutils_bp
from route.vpnutils import vpnutils_bp
from route.openthreadutils import openthreadutils_bp
from route.services import services_bp
from route.systemutils import systemutils_bp
from route.currentconfig import currentconfig_bp
from route.bangleutils import bangleutils_bp
from route.calibration import calibration_bp
from route.rooms import rooms_bp
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import threading
from flask import request
from threading import Lock

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
socketio = SocketIO(app, cors_allowed_origins="*")

# Gestisci lo stato dello streaming dei log
is_streaming_logs = False
is_streaming_ai_logs = False

# Inizializza l'elenco dei clienti attivi
active_clients = set()
clients_lock = Lock()

client_processes = {}

def stream_docker_logs():
    global is_streaming_logs
    if is_streaming_logs:
        return
    is_streaming_logs = True
    
    cmd = ["docker", "logs", "--tail", "10", "-f", "conttestserver"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    try:
        for line in iter(proc.stdout.readline, ''):
            with clients_lock:
                clients_copy = active_clients.copy()  # Make a snapshot of the set
            for client_id in clients_copy:
                socketio.emit('docker_logs', {'log': line.rstrip()}, room=client_id)
    finally:
        is_streaming_logs = False


def stream_ai_monitoring_logs():
    global is_streaming_ai_logs
    if is_streaming_ai_logs:
        return
    is_streaming_ai_logs = True

    cmd = ["docker", "logs", "--tail", "30", "-f", "ai-monitoring"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    try:
        for line in iter(proc.stdout.readline, ''):
            with clients_lock:
                clients_copy = active_clients.copy()  # Make a snapshot of the set
            for client_id in clients_copy:
                socketio.emit('ai_monitoring_logs', {'log': line.rstrip()}, room=client_id)
    finally:
        is_streaming_ai_logs = False

def stop_streaming_for_client(client_id):
    if client_id in client_processes:
        client_processes[client_id].terminate()  # Interrompi il processo
        del client_processes[client_id]
        print(f'Streaming stopped for client {client_id}')

@socketio.on('connect')
def handle_connect():
    global active_clients
    client_id = request.sid
    with clients_lock:  # Usa il lock per proteggere l'aggiunta
        active_clients.add(client_id)
        print(f'Client {client_id} connected')
        join_room(client_id)
    
        # Avvia i thread di streaming solo se è il primo cliente connesso
        if len(active_clients) == 1:
            threading.Thread(target=stream_docker_logs, daemon=True).start()
            threading.Thread(target=stream_ai_monitoring_logs, daemon=True).start()

@socketio.on('disconnect')
def handle_disconnect():
    global active_clients
    client_id = request.sid
    with clients_lock:  # Usa il lock per proteggere la rimozione
        if client_id in active_clients:
            active_clients.remove(client_id)
            print(f'Client {client_id} disconnected')
            leave_room(client_id)
            # Assicurati di interrompere lo streaming specifico per questo client
            stop_streaming_for_client(client_id)

async def ota_server_task(cwd):
	process = await asyncio.create_subprocess_shell('/bin/bash run.sh', cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE )
	stdout, stderr = await process.communicate()
	print(stdout.decode('utf-8'))
	print(stderr.decode('utf-8'))

async def install_packages_chmod(cmd, cwd):
    process = await asyncio.create_subprocess_shell(cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    print(stdout.decode('utf-8'))
    print(stderr.decode('utf-8'))

app.register_blueprint(logutils_bp)
app.register_blueprint(dockerutils_bp)
app.register_blueprint(wifiutils_bp)
app.register_blueprint(vpnutils_bp)    
app.register_blueprint(openthreadutils_bp)
app.register_blueprint(services_bp)
app.register_blueprint(systemutils_bp)
app.register_blueprint(currentconfig_bp)
app.register_blueprint(bangleutils_bp)
app.register_blueprint(calibration_bp)
app.register_blueprint(rooms_bp)

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)
    
if __name__ == "__main__":
    try:
        flask_process = multiprocessing.Process(target=run_flask)
        flask_process.start()
        loop = asyncio.get_event_loop()
        # subprocess.Popen("sudo sh -c 'sudo chmod +x ./mcumgr'",  shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tasks = [
            loop.create_task(install_packages_chmod('npm i', './route/BangleOTA/')),
            loop.create_task(install_packages_chmod('npm i -g http-server', '.')),
            loop.create_task(install_packages_chmod('chmod +x ./BangleApps/run.sh', '.')),
            loop.create_task(install_packages_chmod('chmod +x ./EspruinoApps/run.sh', '.')),
            loop.create_task(install_packages_chmod('chmod +x ./BangleApps/bin/create_apps_json.sh', '.')),
            loop.create_task(ota_server_task('./BangleApps/')),
            loop.create_task(ota_server_task('./EspruinoApps/')),
        ]

        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        pass
    finally:
        for task in tasks:
            task.cancel()
        loop.close()
	
