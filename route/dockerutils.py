from flask import Blueprint, jsonify, Response
import subprocess
import re

dockerutils_bp = Blueprint('docker_bp', __name__)

@dockerutils_bp.route('/docker/containers', methods=['GET'])

def get_docker_containers():
    try:
        # Esegui il comando sudo docker ps per leggere i container docker in esecuzione come root
        command = 'sudo docker ps'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Il comando è andato a buon fine, estrai le informazioni
            output = output.decode('utf-8')
            containers = output.strip().split('\n')[1:]
            docker_containers = []
            for container in containers:
                container_info = re.split(r'\s{2,}', container.strip())
                if len(container_info) >= 6:
                    if len(container_info) == 6:
                        docker_containers.append({
                            'container_id': container_info[0],
                            'image': container_info[1],
                            'command': container_info[2],
                            'created': container_info[3],
                            'status': container_info[4],
                            'names': container_info[5]
                        })
                    else:
                        docker_containers.append({
                            'container_id': container_info[0],
                            'image': container_info[1],
                            'command': container_info[2],
                            'created': container_info[3],
                            'status': container_info[4],
                            'ports': container_info[5],
                            'names': container_info[6]
                        })
            return jsonify({'docker_containers': docker_containers})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get docker containers'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})
     

@dockerutils_bp.route('/docker/containers/<container_id>', methods=['DELETE'])
def delete_docker_container(container_id):
    try:
        # Esegui il comando sudo docker rm per rimuovere il container docker come root
        command = f'sudo docker rm {container_id}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Il comando è andato a buon fine, estrai le informazioni
            output = output.decode('utf-8')
            return jsonify({'message': 'Docker container deleted successfully'})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to delete docker container'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

@dockerutils_bp.route('/docker/container/<container_id>/logs', methods=['GET'])
def get_docker_container_logs(container_id):
    try:
        # Esegui il comando sudo docker logs per leggere i log del container docker come root
        command = f'sudo docker logs --tail 20 {container_id}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
           
            return jsonify({'logs': output.decode('utf-8'), 'error': error.decode('utf-8')})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get docker container logs'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@dockerutils_bp.route('/docker/images', methods=['GET'])
def get_docker_images():
    try:
        # Esegui il comando sudo docker images per leggere le immagini docker disponibili come root
        command = 'sudo docker images'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Il comando è andato a buon fine, estrai le informazioni
            output = output.decode('utf-8')
            images = output.strip().split('\n')[1:]
            docker_images = []
            for image in images:
                image_info = image.split()
                docker_images.append({
                    'repository': image_info[0],
                    'tag': image_info[1],
                    'image_id': image_info[2],
                    'created': image_info[3],
                    'size': image_info[4]
                })
            return jsonify({'docker_images': docker_images})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get docker images'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})


@dockerutils_bp.route('/docker/container/<container_id>/download', methods=['GET'])
def get_docker_container_full_logs(container_id):
    try:
        # Esegui il comando sudo docker logs per leggere i log del container docker come root
        command = f'sudo docker logs {container_id}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Return the logs as a file attachment
            response = Response(output, mimetype='text/plain')
            response.headers.set('Content-Disposition', 'attachment', filename=f'{container_id}_logs.txt')
            return response
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to get docker container logs'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

@dockerutils_bp.route('/docker/container/<container_id>/stop', methods=['POST'])
def stop_docker_container(container_id):
    try:
        # Esegui il comando sudo docker stop per arrestare il container docker come root
        command = f'sudo docker stop {container_id}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Il comando è andato a buon fine, estrai le informazioni
            output = output.decode('utf-8')
            return jsonify({'message': 'Docker container stopped successfully'})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to stop docker container'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})

@dockerutils_bp.route('/docker/container/<container_id>/restart', methods=['POST'])
def restart_docker_container(container_id):
    try:
        # Esegui il comando sudo docker restart per riavviare il container docker come root
        command = f'sudo docker restart {container_id}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if process.returncode == 0:
            # Il comando è andato a buon fine, estrai le informazioni
            output = output.decode('utf-8')
            return jsonify({'message': 'Docker container restarted successfully'})
        else:
            # Il comando non è andato a buon fine, restituisci un messaggio di errore
            return jsonify({'error': 'Failed to restart docker container'})

    except Exception as e:
        return jsonify({'[Exception] error': str(e)})