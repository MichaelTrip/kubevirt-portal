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
import ssl
from kubernetes import client as k8s_client
import websocket

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def vm_list():
    try:
        logger.info("Fetching VM list")
        vms = get_vm_list(Config)
        version = get_git_version()
        return render_template('vm_list.html', vms=vms, config=Config, version=version)
    except Exception as e:
        logger.error(f"Error getting VM list: {str(e)}")
        flash(f"Error getting VM list: {str(e)}", 'error')
        return render_template('vm_list.html', vms=[], config=Config)

@main.route('/create', methods=['GET', 'POST'])
def create_vm():
    form = VMForm()
    if request.method == 'GET':
        form.subdirectory.data = Config.YAML_SUBDIRECTORY
        # Set default address pool if MetalLB is enabled
        if Config.METALLB_ENABLED:
            form.address_pool.data = Config.METALLB_DEFAULT_POOL
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

            # Only include hostname and address_pool for LoadBalancer service type
            service_type = form.service_type.data
            hostname = form.hostname.data if service_type == 'LoadBalancer' else None
            address_pool = form.address_pool.data if service_type == 'LoadBalancer' else None

            form_data = {
                'vm_name': form.vm_name.data,
                'tags': tags_data,
                'cpu_cores': form.cpu_cores.data,
                'memory': form.memory.data,
                'storage_size': form.storage_size.data,
                'storage_class': form.storage_class.data,
                'image_url': form.image_url.data,
                'user_data': form.user_data.data,
                'hostname': hostname,
                'address_pool': address_pool,
                'service_ports': service_ports_data,
                'service_type': service_type
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
            # Align defaults with create flow
            form.subdirectory.data = Config.YAML_SUBDIRECTORY
            if Config.METALLB_ENABLED and not (form.address_pool.data or (vm_config or {}).get('address_pool')):
                form.address_pool.data = Config.METALLB_DEFAULT_POOL
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

            # Only include hostname and address_pool for LoadBalancer service type
            service_type = form.service_type.data
            hostname = form.hostname.data if service_type == 'LoadBalancer' else None
            address_pool = form.address_pool.data if service_type == 'LoadBalancer' else None

            form_data = {
                'vm_name': vm_name,
                'tags': tags_data,
                'cpu_cores': form.cpu_cores.data,
                'memory': form.memory.data,
                'storage_size': form.storage_size.data,
                'storage_class': form.storage_class.data,
                'image_url': form.image_url.data,
                'user_data': form.user_data.data,
                'hostname': hostname,
                'address_pool': address_pool,
                'service_ports': service_ports_data,
                'service_type': service_type
            }

            if 'preview' in request.form:
                yaml_content = generate_yaml(form_data, Config)
                return render_template('edit_vm.html', form=form, vm_name=vm_name, preview_yaml=yaml_content)

            yaml_content = generate_yaml(form_data, Config)
            update_vm_config(Config, vm_name, form_data)
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
    if not Config.CLUSTER_VMS_ENABLED:
        flash('Cluster VMs feature is not enabled', 'warning')
        return redirect(url_for('main.vm_list'))
    try:
        vms = list_running_vms()
        version = get_git_version()
        return render_template('cluster_vms.html', vms=vms, version=version)
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
    embedded = request.args.get('embedded', '0') == '1'
    if not host:
        flash('No host IP provided', 'error')
        return redirect(url_for('main.cluster_vms'))
    return render_template('terminal.html', vm_name=vm_name, host=host, embedded=embedded)


@main.route('/console/<vm_name>')
def console(vm_name):
    """Web-based KubeVirt serial console (proxied via API)"""
    namespace = request.args.get('namespace', 'virtualmachines')
    embedded = request.args.get('embedded', '0') == '1'
    return render_template('console.html', vm_name=vm_name, namespace=namespace, embedded=embedded)


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


@sock.route('/console/ws')
def console_websocket(ws):
    """WebSocket proxy to KubeVirt VM serial console subresource"""
    vm_name = request.args.get('vm_name')
    namespace = request.args.get('namespace', 'virtualmachines')

    if not vm_name:
        ws.send("Error: vm_name is required")
        return

    # Ensure Kubernetes config is loaded
    try:
        get_kubernetes_client()
    except Exception as e:
        ws.send(f"Error loading Kubernetes config: {str(e)}")
        return

    # Prepare upstream KubeVirt console websocket URL
    api = k8s_client.ApiClient()
    cfg = api.configuration
    host = cfg.host  # e.g., https://10.96.0.1
    scheme = 'wss' if host.startswith('https') else 'ws'
    base = host.split('://', 1)[1]
    upstream_url = f"{scheme}://{base}/apis/subresources.kubevirt.io/v1/namespaces/{namespace}/virtualmachineinstances/{vm_name}/console"

    # Validate that VMI exists to fail fast with clear message
    try:
        _, custom_api = get_kubernetes_client()
        custom_api.get_namespaced_custom_object(
            group="kubevirt.io",
            version="v1",
            namespace=namespace,
            plural="virtualmachineinstances",
            name=vm_name
        )
    except Exception as e:
        ws.send(f"\r\nConsole error: VMI {namespace}/{vm_name} not found or inaccessible: {str(e)}\r\n")
        return

    headers = []
    # Prefer API key with prefix (e.g., 'Bearer <token>')
    try:
        token_with_prefix = cfg.get_api_key_with_prefix('authorization')
    except Exception:
        token_with_prefix = None
    if token_with_prefix:
        headers.append(f"Authorization: {token_with_prefix}")

    sslopt = {}
    if cfg.verify_ssl:
        sslopt['cert_reqs'] = ssl.CERT_REQUIRED
        if cfg.ssl_ca_cert:
            sslopt['ca_certs'] = cfg.ssl_ca_cert
    else:
        sslopt['cert_reqs'] = ssl.CERT_NONE

    # Support client certificate authentication
    if getattr(cfg, 'cert_file', None) and getattr(cfg, 'key_file', None):
        sslopt['certfile'] = cfg.cert_file
        sslopt['keyfile'] = cfg.key_file

    upstream = None
    try:
        # Inform client about target
        try:
            ws.send(f"Connecting to {namespace}/{vm_name}...\r\n")
        except Exception:
            pass
        # Do NOT pass subprotocols: some API servers do not echo them and
        # websocket-client will reject the handshake if any are specified.
        upstream = websocket.create_connection(
            upstream_url,
            header=headers,
            sslopt=sslopt,
            timeout=10
        )

        def pump_upstream():
            try:
                while True:
                    data = upstream.recv()
                    if data is None:
                        break
                    # KubeVirt console uses channel framing over binary WS
                    if isinstance(data, bytes) and len(data) > 0:
                        ch = data[0]
                        payload = data[1:]
                        # stdout (1) and stderr (2)
                        if ch in (1, 2):
                            try:
                                ws.send(payload.decode('utf-8', 'ignore'))
                            except Exception:
                                # Fallback: send as replacement char
                                ws.send('\ufffd')
                        elif ch == 3:
                            # error channel
                            try:
                                ws.send(("\r\nConsole error: " + payload.decode('utf-8', 'ignore') + "\r\n"))
                            except Exception:
                                ws.send("\r\nConsole error\r\n")
                        else:
                            # ignore other channels (stdin=0, resize=4)
                            pass
                    else:
                        # Text frames: forward directly
                        if isinstance(data, (bytes, bytearray)):
                            try:
                                ws.send(data.decode('utf-8', 'ignore'))
                            except Exception:
                                ws.send('\ufffd')
                        else:
                            ws.send(str(data))
            except Exception as e:
                try:
                    ws.send(f"\r\nConsole error: upstream receive failed: {str(e)}\r\n")
                except Exception:
                    pass

        t = threading.Thread(target=pump_upstream)
        t.daemon = True
        t.start()

        while True:
            msg = ws.receive()
            if msg is None:
                break
            try:
                # Support simple JSON messages for control (resize)
                if isinstance(msg, str):
                    try:
                        obj = json.loads(msg)
                        if isinstance(obj, dict) and obj.get('type') == 'resize':
                            payload = json.dumps({
                                'Width': int(obj.get('cols', obj.get('width', 80))),
                                'Height': int(obj.get('rows', obj.get('height', 24)))
                            }).encode('utf-8')
                            framed = bytes([4]) + payload
                            upstream.send(framed, opcode=websocket.ABNF.OPCODE_BINARY)
                            continue
                    except Exception:
                        # Not JSON or invalid control, treat as stdin
                        pass
                # Default: stdin channel (0)
                msg_bytes = msg.encode('utf-8') if isinstance(msg, str) else msg
                framed = bytes([0]) + msg_bytes
                upstream.send(framed, opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                try:
                    ws.send(f"\r\nConsole error: upstream send failed: {str(e)}\r\n")
                except Exception:
                    pass
                break
    except Exception as e:
        try:
            ws.send(f"\r\nConsole error: {str(e)}\r\n")
        except Exception:
            pass
    finally:
        try:
            if upstream:
                upstream.close()
        except Exception:
            pass


@main.route('/vnc/<vm_name>')
def vnc(vm_name):
    """Web-based VNC viewer for KubeVirt VMI"""
    namespace = request.args.get('namespace', 'virtualmachines')
    embedded = request.args.get('embedded', '0') == '1'
    return render_template('vnc.html', vm_name=vm_name, namespace=namespace, embedded=embedded)


@sock.route('/vnc/ws')
def vnc_websocket(ws):
    """WebSocket proxy to KubeVirt VNC subresource"""
    vm_name = request.args.get('vm_name')
    namespace = request.args.get('namespace', 'virtualmachines')

    if not vm_name:
        ws.send("VNC error: vm_name is required")
        return

    # Ensure Kubernetes config is loaded
    try:
        get_kubernetes_client()
    except Exception as e:
        ws.send(f"VNC error: Kubernetes config not loaded: {str(e)}")
        return

    # Build upstream VNC URL
    api = k8s_client.ApiClient()
    cfg = api.configuration
    host = cfg.host
    scheme = 'wss' if host.startswith('https') else 'ws'
    base = host.split('://', 1)[1]
    upstream_url = f"{scheme}://{base}/apis/subresources.kubevirt.io/v1/namespaces/{namespace}/virtualmachineinstances/{vm_name}/vnc"

    # Validate VMI exists
    try:
        _, custom_api = get_kubernetes_client()
        custom_api.get_namespaced_custom_object(
            group="kubevirt.io",
            version="v1",
            namespace=namespace,
            plural="virtualmachineinstances",
            name=vm_name
        )
    except Exception as e:
        ws.send(f"VNC error: VMI {namespace}/{vm_name} not found or inaccessible: {str(e)}")
        return

    headers = []
    try:
        token_with_prefix = cfg.get_api_key_with_prefix('authorization')
    except Exception:
        token_with_prefix = None
    if token_with_prefix:
        headers.append(f"Authorization: {token_with_prefix}")
    # Hint upstream to use raw binary subprotocol without enforcing at client
    headers.append("Sec-WebSocket-Protocol: binary.kubevirt.io")

    sslopt = {}
    if cfg.verify_ssl:
        sslopt['cert_reqs'] = ssl.CERT_REQUIRED
        if cfg.ssl_ca_cert:
            sslopt['ca_certs'] = cfg.ssl_ca_cert
    else:
        sslopt['cert_reqs'] = ssl.CERT_NONE
    if getattr(cfg, 'cert_file', None) and getattr(cfg, 'key_file', None):
        sslopt['certfile'] = cfg.cert_file
        sslopt['keyfile'] = cfg.key_file

    upstream = None
    mode_channel = None  # Detect framing after first upstream frame
    try:
        try:
            ws.send(f"Connecting VNC to {namespace}/{vm_name}...\r\n")
        except Exception:
            pass

        upstream = websocket.create_connection(
            upstream_url,
            header=headers,
            sslopt=sslopt,
            timeout=10
        )

        # Pump upstream -> client
        def pump_upstream():
            nonlocal mode_channel
            try:
                while True:
                    data = upstream.recv()
                    if data is None:
                        break
                    if isinstance(data, (bytes, bytearray)) and len(data) > 0:
                        # Detect framing on first packet
                        if mode_channel is None:
                            mode_channel = (data[0] in (0,1,2,3,4))
                        if mode_channel:
                            ch = data[0]
                            payload = data[1:]
                            if ch in (1, 2):
                                ws.send(payload)
                            elif ch == 3:
                                # Error channel as text
                                try:
                                    ws.send(("VNC error: " + payload.decode('utf-8', 'ignore')))
                                except Exception:
                                    ws.send("VNC error")
                            else:
                                # ignore other channels
                                pass
                        else:
                            # Raw VNC bytes
                            ws.send(data)
                    else:
                        # Text frame
                        try:
                            ws.send(str(data))
                        except Exception:
                            pass
            except Exception as e:
                try:
                    ws.send(f"VNC error: upstream receive failed: {str(e)}", binary=False)
                except Exception:
                    pass

        t = threading.Thread(target=pump_upstream)
        t.daemon = True
        t.start()

        # Client -> upstream
        while True:
            msg = ws.receive()
            if msg is None:
                break
            try:
                if isinstance(msg, str):
                    # noVNC may send control messages; forward as text
                    upstream.send(msg)
                else:
                    # Binary
                    if mode_channel:
                        framed = bytes([0]) + msg
                        upstream.send(framed, opcode=websocket.ABNF.OPCODE_BINARY)
                    else:
                        upstream.send(msg, opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                try:
                    ws.send(f"VNC error: upstream send failed: {str(e)}", binary=False)
                except Exception:
                    pass
                break
    except Exception as e:
        try:
            ws.send(f"VNC error: {str(e)}", binary=False)
        except Exception:
            pass
    finally:
        try:
            if upstream:
                upstream.close()
        except Exception:
            pass

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

@main.route('/api/vmi/<vm_name>/status', methods=['GET'], endpoint='vmi_status_api')
def vmi_status_api(vm_name):
    """Return lightweight status for VM/VMI to drive UI polling.
    Includes VM spec.running, VMI phase, node, and IPs if available.
    Namespace defaults to 'virtualmachines'.
    """
    namespace = request.args.get('namespace', 'virtualmachines')
    try:
        core_v1, custom_api = get_kubernetes_client()
        # VM spec.running
        spec_running = None
        try:
            vm = custom_api.get_namespaced_custom_object(
                group="kubevirt.io",
                version="v1",
                namespace=namespace,
                plural="virtualmachines",
                name=vm_name
            )
            spec_running = bool(vm.get('spec', {}).get('running'))
        except Exception:
            # VM may not exist or be inaccessible
            spec_running = None

        # VMI phase and details
        vmi_phase = None
        node = None
        ip_addresses = []
        ready = None
        primary_ip = None
        try:
            vmi = custom_api.get_namespaced_custom_object(
                group="kubevirt.io",
                version="v1",
                namespace=namespace,
                plural="virtualmachineinstances",
                name=vm_name
            )
            vmi_phase = vmi.get('status', {}).get('phase')
            node = vmi.get('status', {}).get('nodeName')
            interfaces = vmi.get('status', {}).get('interfaces', [])
            if isinstance(ip_addresses, list):
                # Collect IP + IPs fields from interfaces
                ips = []
                for itf in interfaces:
                    if 'ip' in itf and itf['ip']:
                        ips.append(itf['ip'])
                        if not primary_ip:
                            primary_ip = itf['ip']
                    if 'ips' in itf and isinstance(itf['ips'], list):
                        ips.extend([ip for ip in itf['ips'] if ip])
                ip_addresses = ips
            else:
                ip_addresses = []
            # Ready condition
            conditions = vmi.get('status', {}).get('conditions', [])
            if isinstance(conditions, list):
                for cond in conditions:
                    if cond.get('type') == 'Ready':
                        ready = (cond.get('status') == 'True')
                        break
        except Exception:
            # VMI may not exist during scheduling/stop
            vmi_phase = None
            node = None
            ip_addresses = []
            ready = None
            primary_ip = None

        payload = {
            'vm_name': vm_name,
            'namespace': namespace,
            'spec_running': spec_running,
            'vmi_phase': vmi_phase,
            'node': node,
            'ip_addresses': ip_addresses,
            'primary_ip': primary_ip,
            'ready': ready,
        }
        return Response(json.dumps(payload), mimetype='application/json')
    except Exception as e:
        logger.error(f"Error getting VMI status for {vm_name}: {str(e)}")
        return str(e), 500

@main.route('/api/vmi/<vm_name>/status', methods=['GET'])
def get_vmi_status(vm_name):
    """Return minimal status info for the VMI associated with a VM.
    Defaults to namespace 'virtualmachines'.
    """
    try:
        namespace = request.args.get('namespace', 'virtualmachines')
        core_v1, custom_api = get_kubernetes_client()
        # Try to read the VMI; it exists only when VM is (or was) running
        try:
            vmi = custom_api.get_namespaced_custom_object(
                group="kubevirt.io",
                version="v1",
                namespace=namespace,
                plural="virtualmachineinstances",
                name=vm_name
            )
        except Exception:
            vmi = None

        # Also get the VM to read spec.running quickly
        try:
            vm = custom_api.get_namespaced_custom_object(
                group="kubevirt.io",
                version="v1",
                namespace=namespace,
                plural="virtualmachines",
                name=vm_name
            )
        except Exception:
            vm = None

        resp = {
            'vm_name': vm_name,
            'namespace': namespace,
            'spec_running': bool(vm and vm.get('spec', {}).get('running', False)),
            'vmi_phase': None,
            'node': None,
            'ip_addresses': []
        }
        if vmi:
            status = vmi.get('status', {})
            resp['vmi_phase'] = status.get('phase')
            # node name
            resp['node'] = status.get('nodeName')
            # Collect IPs
            addrs = []
            for iface in status.get('interfaces', []) or []:
                if 'ipAddress' in iface:
                    addrs.append(iface['ipAddress'])
                if 'ipAddresses' in iface and isinstance(iface['ipAddresses'], list):
                    addrs.extend([ip for ip in iface['ipAddresses'] if ip])
            resp['ip_addresses'] = addrs
        return Response(json.dumps(resp), mimetype='application/json')
    except Exception as e:
        logger.error(f"Error getting VMI status: {str(e)}")
        return str(e), 500

def get_git_version():
    """Get the current git version (tag or commit hash)"""
    try:
        repo = git.Repo(search_parent_directories=True)
        # First try to get the latest tag pointing to HEAD
        tags = [tag for tag in repo.tags if tag.commit == repo.head.commit]
        if tags:
            # Return the most recent tag
            return str(tags[-1])
        # If no tag found, fall back to commit hash
        return repo.head.object.hexsha[:7]
    except Exception as e:
        logger.error(f"Error getting git version: {str(e)}")
        return "unknown"

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
