import yaml
import git
import os
import tempfile
import logging
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

logger = logging.getLogger(__name__)

# Initialize Jinja2 environment
template_dir = Path(__file__).parent / 'templates'
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    trim_blocks=True,
    lstrip_blocks=True
)

def generate_yaml(form_data):
    """Generate YAML configuration using Jinja2 templates."""
    logger.info(f"Generating YAML for VM: {form_data['vm_name']}")
    try:
        # Process user data
        user_data = form_data['user_data'].strip()
        if not user_data.startswith('#cloud-config'):
            user_data = '#cloud-config\n' + user_data

        # Prepare template data
        template_data = {
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
            ]
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
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.debug(f"Created temporary directory: {temp_dir}")

            # Construct the URL with authentication
            auth_url = f"https://{git_config['username']}:{git_config['token']}@{git_config['repo_url'].replace('https://', '')}"
            logger.info(f"Cloning repository using authenticated URL")

            # Clone the repository
            repo = git.Repo.clone_from(
                auth_url,
                temp_dir
            )

            # Create subdirectory path inside the temporary directory
            yaml_path = os.path.join(temp_dir, subdirectory)
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
            commit = repo.index.commit(f'Add VM configuration for {vm_name} in {subdirectory}')
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
    except Exception as e:
        logger.error(f"Unexpected error during Git operations: {str(e)}")
        raise

def get_vm_list(config):
    """Get list of VMs from Git repository."""
    logger.info("Starting to fetch VM list")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.debug(f"Created temporary directory: {temp_dir}")

            # Construct the URL with authentication
            auth_url = f"https://{config.GIT_USERNAME}:{config.GIT_TOKEN}@{config.GIT_REPO_URL.replace('https://', '')}"
            logger.info("Cloning repository")

            repo = git.Repo.clone_from(auth_url, temp_dir)

            vm_dir = os.path.join(temp_dir, config.YAML_SUBDIRECTORY)
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
                            docs = list(yaml.safe_load_all(content))
                            if docs and len(docs) >= 2:  # Ensure we have both VM and Service configs
                                vm_config = docs[0]  # First document is VM config
                                service_config = docs[1]  # Second document is Service config

                                # Extract memory value and convert to standard format
                                memory = vm_config['spec']['template']['spec']['domain']['resources']['requests']['memory']

                                # Extract tags from labels
                                tags = []
                                labels = vm_config['spec']['template']['metadata']['labels']
                                for key, value in labels.items():
                                    if key != 'kubevirt.io/vm':  # Skip the default label
                                        tags.append({'key': key, 'value': value})

                                vm_info = {
                                    'name': vm_config['metadata']['name'],
                                    'cpu': vm_config['spec']['template']['spec']['domain']['cpu']['cores'],
                                    'memory': memory,
                                    'hostname': service_config['metadata']['annotations'].get('external-dns.alpha.kubernetes.io/hostname', 'N/A'),
                                    'storage': vm_config['spec']['dataVolumeTemplates'][0]['spec']['storage']['resources']['requests']['storage'],
                                    'image': vm_config['spec']['dataVolumeTemplates'][0]['spec']['source']['http']['url'],
                                    'address_pool': service_config['metadata']['annotations'].get('metallb.universe.tf/address-pool', 'default'),
                                    'tags': tags
                                }
                                vms.append(vm_info)
                                logger.debug(f"Added VM to list: {vm_info['name']}")
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
    with tempfile.TemporaryDirectory() as temp_dir:
        auth_url = f"https://{config.GIT_USERNAME}:{config.GIT_TOKEN}@{config.GIT_REPO_URL.replace('https://', '')}"
        repo = git.Repo.clone_from(auth_url, temp_dir)

        file_path = os.path.join(temp_dir, config.YAML_SUBDIRECTORY, f"{vm_name}.yaml")
        with open(file_path, 'r') as f:
            content = f.read()
            docs = list(yaml.safe_load_all(content))
            vm_config = docs[0]
            service_config = docs[1]

            # Extract tags from labels
            tags = []
            labels = vm_config['spec']['template']['metadata']['labels']
            for key, value in labels.items():
                if key != 'kubevirt.io/vm':  # Skip the default label
                    tags.append({'key': key, 'value': value})

            return {
                'vm_name': vm_config['metadata']['name'],
                'tags': tags,
                'cpu_cores': vm_config['spec']['template']['spec']['domain']['cpu']['cores'],
                'memory': int(vm_config['spec']['template']['spec']['domain']['resources']['requests']['memory'].rstrip('G')),
                'storage_size': int(vm_config['spec']['dataVolumeTemplates'][0]['spec']['storage']['resources']['requests']['storage'].rstrip('Gi')),
                'storage_class': vm_config['spec']['dataVolumeTemplates'][0]['spec']['storage']['storageClassName'],
                'image_url': vm_config['spec']['dataVolumeTemplates'][0]['spec']['source']['http']['url'],
                'user_data': vm_config['spec']['template']['spec']['volumes'][1]['cloudInitNoCloud']['userData'],
                'hostname': service_config['metadata']['annotations']['external-dns.alpha.kubernetes.io/hostname'],
                'address_pool': service_config['metadata']['annotations']['metallb.universe.tf/address-pool'],
                'service_ports': [
                    {
                        'port_name': port['name'],  # Changed from 'name' to 'port_name' to match form field
                        'port': port['port'],
                        'protocol': port['protocol'],
                        'targetPort': port['targetPort']
                    }
                    for port in service_config['spec']['ports']
                ]
            }

def delete_vm_config(config, vm_name):
    """Delete VM configuration from Git repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        auth_url = f"https://{config.GIT_USERNAME}:{config.GIT_TOKEN}@{config.GIT_REPO_URL.replace('https://', '')}"
        repo = git.Repo.clone_from(auth_url, temp_dir)

        file_path = os.path.join(temp_dir, config.YAML_SUBDIRECTORY, f"{vm_name}.yaml")
        if os.path.exists(file_path):
            os.remove(file_path)
            repo.index.remove([os.path.join(config.YAML_SUBDIRECTORY, f"{vm_name}.yaml")])
            repo.index.commit(f"Delete VM configuration for {vm_name}")
            repo.remote().push()

def update_vm_config(config, vm_name, form_data):
    """Update VM configuration in Git repository."""
    yaml_content = generate_yaml(form_data)
    git_config = {
        'repo_url': config.GIT_REPO_URL,
        'username': config.GIT_USERNAME,
        'token': config.GIT_TOKEN
    }
    commit_to_git(yaml_content, vm_name, config.YAML_SUBDIRECTORY, git_config)

