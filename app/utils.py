import yaml
import git
import os
import tempfile
import logging
import shutil
import subprocess
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)

# Initialize Jinja2 environment
template_dir = Path(__file__).parent / 'templates'
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    trim_blocks=True,
    lstrip_blocks=True
)

logger.info("Initializing Git utilities")

def ensure_git_clone(config):
    """
    Ensure a persistent clone of the Git repository exists.
    If the clone doesn't exist or is outdated, clone/update it.
    """
    logger.info("Ensuring Git repository is cloned")
    
    # Create the storage directory if it doesn't exist
    os.makedirs(config.GIT_CLONE_DIR, exist_ok=True)
    
    # Construct the URL with authentication
    repo_url = config.GIT_REPO_URL.rstrip('/')
    if repo_url.startswith('https://'):
        repo_url = repo_url[8:]  # Remove 'https://'
    elif repo_url.startswith('http://'):
        repo_url = repo_url[7:]  # Remove 'http://'
    auth_url = f"https://{config.GIT_USERNAME}:{config.GIT_TOKEN}@{repo_url}"
    
    # Check if the repository is already cloned
    repo_path = os.path.join(config.GIT_CLONE_DIR, 'repo')
    
    try:
        logger.debug(f"Checking Git repository at: {repo_path}")
        logger.debug(f"Using authentication URL format: https://{config.GIT_USERNAME}:****@{repo_url}")
        
        if os.path.exists(os.path.join(repo_path, '.git')):
            # Repository exists, pull latest changes
            logger.info("Updating existing repository")
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
        else:
            # Clone the repository
            logger.info("Cloning repository")
            git.Repo.clone_from(auth_url, repo_path)
        
        return repo_path
    except Exception as e:
        logger.error(f"Error ensuring Git clone: {str(e)}")
        raise

def generate_yaml(form_data, config):
    """Generate YAML configuration using Jinja2 templates."""
    logger.info(f"Generating YAML for VM: {form_data['vm_name']}")
    try:
        # Process user data
        user_data = form_data['user_data'].strip() if form_data.get('user_data') else ''
        if user_data and not user_data.startswith('#cloud-config'):
            user_data = '#cloud-config\n' + user_data

        # Prepare template data
        template_data = {
            'config': config,
            'vm_name': form_data['vm_name'],
            'cpu_cores': form_data['cpu_cores'],
            'memory': form_data['memory'],
            'user_data': user_data,
            'storage_size': form_data['storage_size'],
            'storage_class': form_data['storage_class'],
            'image_url': form_data['image_url'],
            'hostname': form_data['hostname'],
            'address_pool': form_data['address_pool'],
            'tags': form_data.get('tags', []),
            'service_ports': [
                {
                    'port_name': port['port_name'],
                    'port': port['port'],
                    'protocol': port['protocol'],
                    'targetPort': port['targetPort']
                }
                for port in form_data['service_ports']
            ],
            'service_type': form_data['service_type']
        }

        # Render templates
        vm_template = jinja_env.get_template('vm.yaml.j2')
        service_template = jinja_env.get_template('service.yaml.j2')

        # Generate YAML content
        vm_yaml = "---\n" + vm_template.render(template_data)
        service_yaml = "---\n" + service_template.render(template_data)

        return vm_yaml + "\n" + service_yaml

    except Exception as e:
        logger.error(f"Error generating YAML: {str(e)}", exc_info=True)
        raise

def commit_to_git(yaml_content, vm_name, subdirectory, git_config):
    logger.info(f"Starting Git commit process for VM: {vm_name}")
    try:
        # Use the persistent clone directory
        repo_path = os.path.join(Config.GIT_CLONE_DIR, 'repo')
        
        # Ensure the repository is up to date
        repo = git.Repo(repo_path)
        repo.remotes.origin.pull()

        # Create subdirectory path inside the repository
        yaml_path = os.path.join(repo_path, subdirectory)
        os.makedirs(yaml_path, exist_ok=True)
        logger.debug(f"Created directory: {yaml_path}")

        # Write YAML file to the correct path
        file_path = os.path.join(yaml_path, f'{vm_name}.yaml')
        with open(file_path, 'w') as f:
            f.write(yaml_content)
        logger.info(f"Written YAML file to: {file_path}")

        # Add the file using the relative path
        relative_file_path = os.path.join(subdirectory, f'{vm_name}.yaml')
        repo.index.add([relative_file_path])

        # Create commit
        commit = repo.index.commit(f'Add/Update VM configuration for {vm_name} in {subdirectory}')
        logger.info(f"Created commit: {commit.hexsha}")

        # Push changes
        logger.info("Pushing changes to remote repository")
        push_info = repo.remote().push()

        # Log push result
        for info in push_info:
            if info.flags & info.ERROR:
                raise git.GitCommandError("push", f"Failed to push to remote: {info.summary}")
            logger.info(f"Push successful: {info.summary}")

    except git.GitCommandError as e:
        logger.error(f"Git error: {str(e)}")
        raise

def get_vm_list(config):
    """Get list of VMs from Git repository."""
    logger.info("Starting to fetch VM list")
    try:
        # Ensure repository is cloned and up to date
        repo_path = ensure_git_clone(config)

        vm_dir = os.path.join(repo_path, config.YAML_SUBDIRECTORY)
        logger.debug(f"Looking for VMs in directory: {vm_dir}")

        if not os.path.exists(vm_dir):
            logger.warning(f"Directory {vm_dir} does not exist")
            return []

        vms = []
        for file in os.listdir(vm_dir):
            if file.endswith('.yaml'):
                file_path = os.path.join(vm_dir, file)
                logger.debug(f"Processing file: {file_path}")

                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        try:
                            docs = list(yaml.safe_load_all(content))
                            if docs and len(docs) >= 2:  # Ensure we have both VM and Service configs
                                vm_config = docs[0]  # First document is VM config
                                service_config = docs[1]  # Second document is Service config

                                if not isinstance(vm_config, dict) or not isinstance(service_config, dict):
                                    logger.error(f"Invalid YAML structure in {file}: VM or Service config is not a dictionary")
                                    continue

                                try:
                                    # Safely get nested values with defaults
                                    memory = vm_config.get('spec', {}).get('template', {}).get('spec', {}).get('domain', {}).get('resources', {}).get('requests', {}).get('memory', 'N/A')
                                    cpu_cores = vm_config.get('spec', {}).get('template', {}).get('spec', {}).get('domain', {}).get('cpu', {}).get('cores', 'N/A')
                                    storage = vm_config.get('spec', {}).get('dataVolumeTemplates', [{}])[0].get('spec', {}).get('storage', {}).get('resources', {}).get('requests', {}).get('storage', 'N/A')
                                    image_url = vm_config.get('spec', {}).get('dataVolumeTemplates', [{}])[0].get('spec', {}).get('source', {}).get('http', {}).get('url', 'N/A')
                                    
                                    # Extract tags from labels
                                    tags = []
                                    labels = vm_config.get('spec', {}).get('template', {}).get('metadata', {}).get('labels', {})
                                    for key, value in labels.items():
                                        if key != 'kubevirt.io/vm':  # Skip the default label
                                            tags.append({'key': key, 'value': value})

                                    vm_info = {
                                        'name': vm_config.get('metadata', {}).get('name', 'Unknown'),
                                        'cpu': cpu_cores,
                                        'memory': memory,
                                        'hostname': service_config.get('metadata', {}).get('annotations', {}).get('external-dns.alpha.kubernetes.io/hostname', 'N/A'),
                                        'storage': storage,
                                        'image': image_url,
                                        'address_pool': service_config.get('metadata', {}).get('annotations', {}).get('metallb.universe.tf/address-pool', 'default'),
                                        'tags': tags,
                                        'service_type': service_config.get('spec', {}).get('type')
                                    }
                                    vms.append(vm_info)
                                    logger.debug(f"Added VM to list: {vm_info['name']}")
                                except Exception as e:
                                    logger.error(f"Error extracting VM details from {file}: {str(e)}")
                                    continue
                            else:
                                logger.warning(f"Skipping {file}: Invalid number of YAML documents")
                        except yaml.YAMLError as e:
                            logger.error(f"Error parsing YAML in {file}: {str(e)}")
                            continue
                except Exception as e:
                    logger.error(f"Error processing file {file}: {str(e)}")
                    continue

        logger.info(f"Found {len(vms)} VMs")
        return vms

    except Exception as e:
        logger.error(f"Error getting VM list: {str(e)}")
        raise

def get_vm_config(config, vm_name):
    """Get VM configuration from Git repository."""
    # Ensure repository is cloned and up to date
    repo_path = ensure_git_clone(config)

    # Construct the subdirectory path
    subdirectory_path = os.path.join(repo_path, config.YAML_SUBDIRECTORY)
    
    # Find the correct file
    file_path = os.path.join(subdirectory_path, f"{vm_name}.yaml")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        existing_files = os.listdir(subdirectory_path)
        logger.error(f"Existing files: {existing_files}")
        raise FileNotFoundError(f"No configuration file found for VM: {vm_name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
        docs = list(yaml.safe_load_all(content))
        vm_config = docs[0]
        service_config = docs[1]

        # Verify that the metadata.name matches the requested vm_name
        if vm_config['metadata']['name'] != vm_name:
            logger.warning(f"Requested VM name {vm_name} does not match metadata name {vm_config['metadata']['name']}")

        # Extract tags from labels with safe access
        tags = []
        labels = vm_config.get('spec', {}).get('template', {}).get('metadata', {}).get('labels', {})
        for key, value in labels.items():
            if key != 'kubevirt.io/vm':  # Skip the default label
                tags.append({'key': key, 'value': value})

        # Safely get memory value
        memory_str = vm_config.get('spec', {}).get('template', {}).get('spec', {}).get('domain', {}).get('resources', {}).get('requests', {}).get('memory', '1G')
        memory = int(memory_str.rstrip('G'))

        # Safely get storage size
        storage_str = vm_config.get('spec', {}).get('dataVolumeTemplates', [{}])[0].get('spec', {}).get('storage', {}).get('resources', {}).get('requests', {}).get('storage', '10Gi')
        storage_size = int(storage_str.rstrip('Gi'))

        # Get service annotations safely
        service_annotations = service_config.get('metadata', {}).get('annotations', {})

        return {
            'vm_name': vm_config.get('metadata', {}).get('name', 'unknown'),
            'tags': tags,
            'cpu_cores': vm_config.get('spec', {}).get('template', {}).get('spec', {}).get('domain', {}).get('cpu', {}).get('cores', 1),
            'memory': memory,
            'storage_size': storage_size,
            'storage_class': vm_config.get('spec', {}).get('dataVolumeTemplates', [{}])[0].get('spec', {}).get('storage', {}).get('storageClassName', 'longhorn-rwx'),
            'image_url': vm_config.get('spec', {}).get('dataVolumeTemplates', [{}])[0].get('spec', {}).get('source', {}).get('http', {}).get('url', ''),
            'user_data': vm_config.get('spec', {}).get('template', {}).get('spec', {}).get('volumes', [{}])[1].get('cloudInitNoCloud', {}).get('userData', ''),
            'hostname': service_annotations.get('external-dns.alpha.kubernetes.io/hostname', ''),
            'address_pool': service_annotations.get('metallb.universe.tf/address-pool', ''),
            'service_ports': [
                {
                    'port_name': port['name'],  # Changed from 'name' to 'port_name' to match form field
                    'port': port['port'],
                    'protocol': port['protocol'],
                    'targetPort': port['targetPort']
                }
                for port in service_config['spec']['ports']
            ],
            'service_type': service_config.get('spec', {}).get('type')
        }

def update_vm_config(config, vm_name, form_data):
    """Update VM configuration in Git repository."""
    # Generate YAML content
    yaml_content = generate_yaml(form_data, Config)
    
    # Prepare Git configuration
    git_config = {
        'repo_url': config.GIT_REPO_URL,
        'username': config.GIT_USERNAME,
        'token': config.GIT_TOKEN
    }
    
    # Commit to Git with the metadata name
    commit_to_git(yaml_content, vm_name, config.YAML_SUBDIRECTORY, git_config)

def delete_vm_config(config, vm_name):
    """Delete VM configuration from Git repository."""
    # Ensure repository is cloned and up to date
    repo_path = ensure_git_clone(config)
    
    repo = git.Repo(repo_path)
    file_path = os.path.join(repo_path, config.YAML_SUBDIRECTORY, f"{vm_name}.yaml")
    
    if os.path.exists(file_path):
        os.remove(file_path)
        relative_file_path = os.path.join(config.YAML_SUBDIRECTORY, f"{vm_name}.yaml")
        repo.index.remove([relative_file_path])
        repo.index.commit(f"Delete VM configuration for {vm_name}")
        repo.remote().push()
    else:
        logger.warning(f"File {file_path} does not exist")
