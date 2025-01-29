from flask import Blueprint, render_template, flash, redirect, url_for, request, Response
import json
from flask_sock import Sock
import paramiko
import select
import threading
from app import sock
from app.forms import VMForm
from app.utils import (generate_yaml, commit_to_git, get_vm_list,
                      get_vm_config, delete_vm_config, update_vm_config)
from app.k8s_utils import list_running_vms, get_kubernetes_client
import yaml
from config import Config
import logging
import git

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def vm_list():
    try:
        logger.info("Fetching VM list")
        vms = get_vm_list(Config)
        return render_template('vm_list.html', vms=vms, config=Config)
    except Exception as e:
        logger.error(f"Error getting VM list: {str(e)}")
        flash(f"Error getting VM list: {str(e)}", 'error')
        return render_template('vm_list.html', vms=[], config=Config)

@main.route('/create', methods=['GET', 'POST'])
def create_vm():
    form = VMForm()
    if request.method == 'GET':
        form.subdirectory.data = Config.YAML_SUBDIRECTORY
    if form.validate_on_submit():
        try:
            # Debug logging for service ports
            logger.info("=== Processing Form Submission ===")
            logger.info(f"Number of service ports: {len(form.service_ports)}")

            # Process service ports data
            service_ports_data = []
            for port in form.service_ports:
                port_data = {
                    'port_name': port.port_name.data,
                    'port': port.port.data,
                    'protocol': port.protocol.data,
                    'targetPort': port.targetPort.data
                }
                logger.info(f"Processing port: {port_data}")
                service_ports_data.append(port_data)

            # Process tags data
            tags_data = []
            for tag in form.tags:
                tag_data = {
                    'key': tag.key.data,
                    'value': tag.value.data
                }
                tags_data.append(tag_data)

            form_data = {
                'vm_name': form.vm_name.data,
                'tags': tags_data,
                'cpu_cores': form.cpu_cores.data,
                'memory': form.memory.data,
                'storage_size': form.storage_size.data,
                'storage_class': form.storage_class.data,
                'image_url': form.image_url.data,
                'user_data': form.user_data.data,
                'hostname': form.hostname.data,
                'address_pool': form.address_pool.data,
                'service_ports': service_ports_data
            }

            logger.info(f"Processed service ports: {service_ports_data}")

            if 'preview' in request.form:
                yaml_content = generate_yaml(form_data, Config)
                return render_template('create_vm.html', form=form, preview_yaml=yaml_content)

            yaml_content = generate_yaml(form_data, Config)

            git_config = {
                'repo_url': Config.GIT_REPO_URL,
                'username': Config.GIT_USERNAME,
                'token': Config.GIT_TOKEN
            }

            subdirectory = form.subdirectory.data or Config.YAML_SUBDIRECTORY

            commit_to_git(yaml_content, form_data['vm_name'], subdirectory, git_config)
            logger.info(f"Successfully created and committed VM configuration for {form_data['vm_name']}")

            flash('VM configuration created and committed successfully!', 'success')
            return redirect(url_for('main.vm_list'))

        except Exception as e:
            error_msg = f"Error creating VM configuration: {str(e)}"
            logger.error(error_msg, exc_info=True)
            flash(error_msg, 'error')
    else:
        if form.errors:
            logger.error(f"Form validation errors: {form.errors}")

    return render_template('create_vm.html', form=form, config=Config)

@main.route('/edit/<vm_name>', methods=['GET', 'POST'])
def edit_vm(vm_name):
    try:
        if request.method == 'GET':
            vm_config = get_vm_config(Config, vm_name)
            form = VMForm(data=vm_config)
            return render_template('edit_vm.html', form=form, vm_name=vm_name, config=Config)

        form = VMForm()
        if form.validate_on_submit():
            service_ports_data = []
            for port in form.service_ports:
                port_data = {
                    'port_name': port.port_name.data,
                    'port': port.port.data,
                    'protocol': port.protocol.data,
                    'targetPort': port.targetPort.data
                }
                service_ports_data.append(port_data)

            # Process tags data
            tags_data = []
            for tag in form.tags:
                tag_data = {
                    'key': tag.key.data,
                    'value': tag.value.data
                }
                tags_data.append(tag_data)

            form_data = {
                'vm_name': vm_name,
                'tags': tags_data,
                'cpu_cores': form.cpu_cores.data,
                'memory': form.memory.data,
                'storage_size': form.storage_size.data,
                'storage_class': form.storage_class.data,
                'image_url': form.image_url.data,
                'user_data': form.user_data.data,
                'hostname': form.hostname.data,
                'address_pool': form.address_pool.data,
                'service_ports': service_ports_data
            }

            if 'preview' in request.form:
                yaml_content = generate_yaml(form_data, Config)
                return render_template('edit_vm.html', form=form, vm_name=vm_name, preview_yaml=yaml_content)

            yaml_content = generate_yaml(form_data, Config)
            git_config = {
                'repo_url': Config.GIT_REPO_URL,
                'username': Config.GIT_USERNAME,
                'token': Config.GIT_TOKEN
            }
            commit_to_git(yaml_content, vm_name, Config.YAML_SUBDIRECTORY, git_config)
            flash('VM configuration updated successfully!', 'success')
            return redirect(url_for('main.vm_list'))

    except Exception as e:
        logger.error(f"Error editing VM configuration: {str(e)}", exc_info=True)
        flash(f"Error editing VM configuration: {str(e)}", 'error')
        return redirect(url_for('main.vm_list'))

@main.route('/delete/<vm_name>', methods=['POST'])
def delete_vm(vm_name):
    try:
        delete_vm_config(Config, vm_name)
        flash(f'VM configuration for {vm_name} deleted successfully!', 'success')
    except Exception as e:
        logger.error(f"Error deleting VM configuration: {str(e)}", exc_info=True)
        flash(f"Error deleting VM configuration: {str(e)}", 'error')
    return redirect(url_for('main.vm_list'))

@main.route('/cluster-vms', methods=['GET'])
def cluster_vms():
    """List VMs running in the Kubernetes cluster"""
    try:
        vms = list_running_vms()
        return render_template('cluster_vms.html', vms=vms)
    except Exception as e:
        logger.error(f"Error getting cluster VM list: {str(e)}")
        flash(f"Error getting cluster VM list: {str(e)}", 'error')
        return render_template('cluster_vms.html', vms=[])

@main.route('/api/vm/<vm_name>/yaml', methods=['GET'])
def get_vm_yaml(vm_name):
    """Get raw YAML for a VM"""
    try:
        core_v1, custom_api = get_kubernetes_client()
        vm = custom_api.get_namespaced_custom_object(
            group="kubevirt.io",
            version="v1",
            namespace="virtualmachines",  # You might want to make this configurable
            plural="virtualmachines",
            name=vm_name
        )
        return yaml.dump(vm, default_flow_style=False)
    except Exception as e:
        logger.error(f"Error getting VM YAML: {str(e)}")
        return str(e), 500

@main.route('/terminal/<vm_name>')
def terminal(vm_name):
    """Web-based SSH terminal"""
    host = request.args.get('host')
    if not host:
        flash('No host IP provided', 'error')
        return redirect(url_for('main.cluster_vms'))
    return render_template('terminal.html', vm_name=vm_name, host=host)


def init_ssh_client():
    """Initialize SSH client with password authentication only"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client

@sock.route('/terminal/ws')
def ssh_websocket(ws):
    """WebSocket handler for SSH terminal"""
    host = request.args.get('host')
    port = int(request.args.get('port', 22))
    client = None
    channel = None
    
    try:
        ws.send("\r\nWaiting for authentication...\r\n")
        # Wait for authentication message
        auth_message = ws.receive()
        if not auth_message:
            ws.send("\r\nError: No authentication message received\r\n")
            return
            
        try:
            auth_data = json.loads(auth_message)
            ws.send("\r\nAuthentication message received...\r\n")
        except json.JSONDecodeError:
            ws.send("\r\nError: Invalid authentication message format\r\n")
            return
            
        if auth_data.get('type') != 'auth':
            ws.send("\r\nError: Authentication required\r\n")
            return
            
        username = auth_data.get('username')
        password = auth_data.get('password')
        
        if not username or not password:
            ws.send("\r\nError: Username and password required\r\n")
            return
        
        try:
            ws.send(f"\r\nAttempting SSH connection to {host}...\r\n")
            client = init_ssh_client()
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
                banner_timeout=60
            )
            ws.send("\r\nSSH connection established...\r\n")
            
            channel = client.invoke_shell(term='xterm')
            channel.settimeout(0)  # Non-blocking mode
            ws.send("\r\nShell channel opened...\r\n")
            ws.send("\r\nConnected!\r\n")
        except Exception as e:
            ws.send(f"\r\nSSH Connection Error: {str(e)}\r\n")
            return
    
        def send_data():
            try:
                while True:
                    r, _, _ = select.select([channel], [], [], 0.1)
                    if r:
                        data = channel.recv(1024)
                        if not data:
                            break
                        ws.send(data.decode())
            except Exception as e:
                ws.send(f"\r\nError in data thread: {str(e)}\r\n")
                
        sender = threading.Thread(target=send_data)
        sender.daemon = True
        sender.start()
    
        while True:
            data = ws.receive()
            if not data:
                break
            if channel:
                channel.send(data)
        
    except Exception as e:
        ws.send(f"\r\nWebSocket Error: {str(e)}\r\n")
    finally:
        if channel:
            channel.close()
        if client:
            client.close()

@main.route('/api/vm/<vm_name>/power/<action>', methods=['POST'])
def vm_power(vm_name, action):
    """Power on/off a VM"""
    try:
        if action not in ['start', 'stop']:
            return "Invalid action", 400
            
        power_vm(vm_name, action)
        return "Success", 200
    except Exception as e:
        logger.error(f"Error controlling VM power: {str(e)}")
        return str(e), 500

@main.route('/api/service/<service_name>/yaml', methods=['GET'])
def get_service_yaml(service_name):
    """Get raw YAML for a Service"""
    try:
        core_v1, _ = get_kubernetes_client()
        service = core_v1.read_namespaced_service(
            name=service_name,
            namespace="virtualmachines"  # You might want to make this configurable
        )
        return yaml.dump(service.to_dict(), default_flow_style=False)
    except Exception as e:
        logger.error(f"Error getting Service YAML: {str(e)}")
        return str(e), 500

def power_vm(vm_name, action):
    """Power on/off a VM"""
    try:
        _, custom_api = get_kubernetes_client()
        
        # Get current VM state
        vm = custom_api.get_namespaced_custom_object(
            group="kubevirt.io",
            version="v1",
            namespace="virtualmachines",
            plural="virtualmachines",
            name=vm_name
        )
        
        # Update running state based on action
        vm['spec']['running'] = action == 'start'
        
        # Apply the update
        custom_api.patch_namespaced_custom_object(
            group="kubevirt.io",
            version="v1",
            namespace="virtualmachines",
            plural="virtualmachines",
            name=vm_name,
            body=vm
        )
        
        return True
    except Exception as e:
        logger.error(f"Error {action}ing VM {vm_name}: {str(e)}")
        raise
