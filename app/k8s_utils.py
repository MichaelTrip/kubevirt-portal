from kubernetes import client, config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_kubernetes_client():
    """
    Initialize and return a Kubernetes client
    Tries to load config from default locations or in-cluster config
    """
    try:
        # Try to load from kubeconfig file
        config.load_kube_config()
    except config.ConfigException:
        try:
            # If not found, try in-cluster config
            config.load_incluster_config()
        except config.ConfigException:
            logger.error("Could not load Kubernetes configuration")
            raise

    return client.CoreV1Api(), client.CustomObjectsApi()

def list_running_vms():
    """
    List all VirtualMachine resources in the cluster
    """
    try:
        core_v1, custom_api = get_kubernetes_client()

        # Use CustomObjectsApi to fetch VirtualMachines and VMIs
        group = 'kubevirt.io'
        version = 'v1'
        
        # Fetch VMs across all namespaces
        vms_list = custom_api.list_cluster_custom_object(group, version, 'virtualmachines')
        
        # Fetch VMIs across all namespaces
        vmis_list = custom_api.list_cluster_custom_object(group, version, 'virtualmachineinstances')

        # Fetch all services across all namespaces
        services = core_v1.list_service_for_all_namespaces()
        
        # Create a mapping of VM name to service details
        service_mapping = {}
        for svc in services.items:
            if svc.spec.selector and 'kubevirt.io/vm' in svc.spec.selector:
                vm_name = svc.spec.selector['kubevirt.io/vm']
                namespace = svc.metadata.namespace
                service_mapping[f"{namespace}/{vm_name}"] = svc
        
        # Create a mapping of VM name to VMI details
        vmi_mapping = {}
        for vmi in vmis_list.get('items', []):
            name = vmi['metadata']['name']
            namespace = vmi['metadata']['namespace']
            vmi_mapping[f"{namespace}/{name}"] = vmi

        processed_vms = []
        for vm in vms_list.get('items', []):
            try:
                vm_details = process_vm_details(vm, vmi_mapping, service_mapping)
                processed_vms.append(vm_details)
            except Exception as e:
                logger.warning(f"Could not process VM {vm.get('metadata', {}).get('name')}: {str(e)}")

        return processed_vms

    except Exception as e:
        logger.error(f"Error listing VMs: {str(e)}")
        return []

def process_vm_details(vm, vmi_mapping=None, service_mapping=None):
    """
    Extract and process details from a VirtualMachine resource and its VMI
    """
    metadata = vm.get('metadata', {})
    spec = vm.get('spec', {})
    status = vm.get('status', {})
    
    name = metadata.get('name', 'Unknown')
    namespace = metadata.get('namespace', 'default')
    vm_key = f"{namespace}/{name}"

    # Get associated VMI if it exists
    vmi = vmi_mapping.get(vm_key) if vmi_mapping else None

    # Determine VM running status
    running_status = status.get('printableStatus', 'Unknown')
    is_running = running_status.lower() == 'running'

    # Extract VM resources
    domain = spec.get('template', {}).get('spec', {}).get('domain', {})
    cpu = domain.get('cpu', {})
    cpu_cores = cpu.get('cores', 'N/A')
    memory = domain.get('resources', {}).get('requests', {}).get('memory', 'N/A')

    # Parse creation timestamp
    creation_time = metadata.get('creationTimestamp')
    parsed_creation_time = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M") if creation_time else 'N/A'

    # Get VMI-specific details
    vmi_details = {}
    if vmi:
        vmi_status = vmi.get('status', {})
        
        # Get node name where VMI is running
        node_name = vmi.get('status', {}).get('nodeName', 'N/A')
        
        # Get IP addresses
        interfaces = vmi_status.get('interfaces', [])
        ip_addresses = []
        for iface in interfaces:
            if 'ipAddress' in iface:
                ip_addresses.append(iface['ipAddress'])
            if 'ipAddresses' in iface:
                ip_addresses.extend(iface['ipAddresses'])
        
        # Get phase and conditions
        phase = vmi_status.get('phase', 'N/A')
        conditions = vmi_status.get('conditions', [])
        ready_condition = next((c for c in conditions if c['type'] == 'Ready'), {})
        is_ready = ready_condition.get('status') == 'True'

        vmi_details = {
            'node': node_name,
            'ip_addresses': ip_addresses,
            'phase': phase,
            'ready': is_ready,
            'conditions': conditions
        }

    # Get service details if available
    service_details = {}
    service = service_mapping.get(vm_key) if service_mapping else None
    if service:
        external_ips = []
        if service.status.load_balancer.ingress:
            for ingress in service.status.load_balancer.ingress:
                if hasattr(ingress, 'ip'):
                    external_ips.append(ingress.ip)
        
        ports = []
        for port in service.spec.ports:
            ports.append({
                'name': port.name,
                'port': port.port,
                'protocol': port.protocol,
                'target_port': port.target_port
            })

        service_details = {
            'external_ips': external_ips,
            'cluster_ip': service.spec.cluster_ip,
            'ports': ports,
            'type': service.spec.type
        }

    return {
        'name': name,
        'namespace': namespace,
        'running': is_running,
        'cpu_cores': cpu_cores,
        'memory': memory,
        'labels': metadata.get('labels', {}),
        'created': parsed_creation_time,
        'vmi': vmi_details,
        'service': service_details
    }
