"""Utility functions for VM management - Refactored with new managers."""

import yaml
import logging
from typing import Dict, Any, List
from pathlib import Path
from pydantic import ValidationError

from config import Config
from app.schemas import VMConfigSchema, NetworkConfigSchema
from app.template_manager import TemplateManager
from app.git_manager import GitOperationManager, GitOperationError
from app.constants import (
    GIT_COMMIT_MESSAGE_CREATE,
    GIT_COMMIT_MESSAGE_UPDATE, 
    GIT_COMMIT_MESSAGE_DELETE,
    YAML_EXTENSION,
    PROFILE_DEFAULT
)

logger = logging.getLogger(__name__)

# Initialize managers as singletons
_template_manager = None
_git_manager = None


def get_template_manager() -> TemplateManager:
    """Get or create template manager singleton."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager


def get_git_manager(config: Config = None) -> GitOperationManager:
    """Get or create git manager singleton."""
    global _git_manager
    if _git_manager is None:
        if config is None:
            config = Config()
        _git_manager = GitOperationManager(config)
    return _git_manager


def validate_and_prepare_config(form_data: Dict[str, Any]) -> VMConfigSchema:
    """
    Validate form data and return validated schema.
    
    Args:
        form_data: Raw form data dictionary
        
    Returns:
        Validated VMConfigSchema instance
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Ensure network_config exists with defaults
        if 'network_config' not in form_data:
            form_data['network_config'] = NetworkConfigSchema().dict()
        
        # Validate using Pydantic
        config = VMConfigSchema(**form_data)
        logger.info(f"Validated configuration for VM: {config.vm_name}")
        return config
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise


def generate_yaml(
    form_data: Dict[str, Any], 
    config: Config,
    profile_name: str = PROFILE_DEFAULT
) -> str:
    """
    Generate YAML configuration using template manager.
    
    Args:
        form_data: Form data dictionary
        config: Application configuration
        profile_name: Template profile to use
        
    Returns:
        Combined YAML string (VM + Service)
        
    Raises:
        ValidationError: If form data is invalid
        Exception: If template rendering fails
    """
    logger.info(f"Generating YAML for VM: {form_data.get('vm_name')}")
    
    try:
        # Validate input
        vm_config = validate_and_prepare_config(form_data)
        
        # Convert to template-friendly dict
        context = vm_config.to_template_dict()
        context['config'] = config
        
        # Get template manager and render
        template_mgr = get_template_manager()
        yaml_content = template_mgr.render_complete_config(context, profile_name)
        
        logger.info(f"Successfully generated YAML for VM: {vm_config.vm_name}")
        return yaml_content
        
    except ValidationError as e:
        logger.error(f"Validation error generating YAML: {e}")
        raise ValueError(f"Invalid configuration: {e}")
    except Exception as e:
        logger.error(f"Error generating YAML: {e}", exc_info=True)
        raise


def commit_to_git(
    yaml_content: str, 
    vm_name: str, 
    subdirectory: str, 
    git_config: Dict[str, str]
) -> str:
    """
    Commit YAML configuration to Git repository.
    
    Args:
        yaml_content: YAML content to commit
        vm_name: Name of the VM
        subdirectory: Subdirectory in repository
        git_config: Git configuration (not used, kept for compatibility)
        
    Returns:
        Commit SHA
        
    Raises:
        GitOperationError: If commit fails
    """
    logger.info(f"Committing configuration for VM: {vm_name}")
    
    try:
        git_mgr = get_git_manager()
        
        file_name = f"{vm_name}{YAML_EXTENSION}"
        commit_message = GIT_COMMIT_MESSAGE_CREATE.format(vm_name=vm_name)
        
        commit_sha = git_mgr.commit_file(
            file_path=file_name,
            content=yaml_content,
            commit_message=commit_message,
            subdirectory=subdirectory
        )
        
        logger.info(f"Successfully committed VM configuration: {commit_sha}")
        return commit_sha
        
    except GitOperationError as e:
        logger.error(f"Git operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error committing to git: {e}", exc_info=True)
        raise GitOperationError(f"Failed to commit: {e}")


def get_vm_list(config: Config) -> List[Dict[str, Any]]:
    """
    Get list of VMs from Git repository.
    
    Args:
        config: Application configuration
        
    Returns:
        List of VM information dictionaries
    """
    logger.info("Fetching VM list from repository")
    
    try:
        git_mgr = get_git_manager(config)
        files = git_mgr.list_files(
            subdirectory=config.YAML_SUBDIRECTORY,
            extension=YAML_EXTENSION
        )
        
        vms = []
        for file_name in files:
            try:
                content = git_mgr.read_file(
                    file_path=file_name,
                    subdirectory=config.YAML_SUBDIRECTORY
                )
                
                # Parse YAML documents
                docs = list(yaml.safe_load_all(content))
                if len(docs) < 2:
                    logger.warning(f"Skipping {file_name}: Invalid document count")
                    continue
                
                vm_config = docs[0]
                service_config = docs[1]
                
                if not isinstance(vm_config, dict) or not isinstance(service_config, dict):
                    logger.error(f"Invalid YAML structure in {file_name}")
                    continue
                
                # Extract VM information
                vm_info = _extract_vm_info(vm_config, service_config)
                vms.append(vm_info)
                
            except Exception as e:
                logger.error(f"Error processing {file_name}: {e}")
                continue
        
        logger.info(f"Found {len(vms)} VMs")
        return vms
        
    except Exception as e:
        logger.error(f"Error getting VM list: {e}", exc_info=True)
        raise


def _extract_vm_info(vm_config: Dict, service_config: Dict) -> Dict[str, Any]:
    """Extract VM information from parsed YAML documents."""
    # Safely navigate nested dictionaries
    spec = vm_config.get('spec', {})
    template_spec = spec.get('template', {}).get('spec', {})
    domain = template_spec.get('domain', {})
    
    # Extract resources
    memory = domain.get('resources', {}).get('requests', {}).get('memory', 'N/A')
    cpu_cores = domain.get('cpu', {}).get('cores', 'N/A')
    
    # Extract storage from dataVolumeTemplates
    data_volume = spec.get('dataVolumeTemplates', [{}])[0]
    storage = (data_volume.get('spec', {})
               .get('storage', {})
               .get('resources', {})
               .get('requests', {})
               .get('storage', 'N/A'))
    
    image_url = (data_volume.get('spec', {})
                 .get('source', {})
                 .get('http', {})
                 .get('url', 'N/A'))
    
    # Extract tags from labels
    tags = []
    labels = spec.get('template', {}).get('metadata', {}).get('labels', {})
    for key, value in labels.items():
        if key != 'kubevirt.io/vm':
            tags.append({'key': key, 'value': value})
    
    # Extract service information
    service_annotations = service_config.get('metadata', {}).get('annotations', {})
    hostname = service_annotations.get('external-dns.alpha.kubernetes.io/hostname', 'N/A')
    address_pool = service_annotations.get('metallb.universe.tf/address-pool', 'default')
    service_type = service_config.get('spec', {}).get('type', 'N/A')
    
    return {
        'name': vm_config.get('metadata', {}).get('name', 'Unknown'),
        'cpu': cpu_cores,
        'memory': memory,
        'hostname': hostname,
        'storage': storage,
        'image': image_url,
        'address_pool': address_pool,
        'tags': tags,
        'service_type': service_type
    }


def get_vm_config(config: Config, vm_name: str) -> Dict[str, Any]:
    """
    Get VM configuration from Git repository.
    
    Args:
        config: Application configuration
        vm_name: Name of the VM
        
    Returns:
        VM configuration dictionary
        
    Raises:
        GitOperationError: If file not found or read fails
    """
    logger.info(f"Fetching configuration for VM: {vm_name}")
    
    try:
        git_mgr = get_git_manager(config)
        file_name = f"{vm_name}{YAML_EXTENSION}"
        
        content = git_mgr.read_file(
            file_path=file_name,
            subdirectory=config.YAML_SUBDIRECTORY
        )
        
        # Parse YAML documents
        docs = list(yaml.safe_load_all(content))
        if len(docs) < 2:
            raise ValueError(f"Invalid YAML structure in {file_name}")
        
        vm_config = docs[0]
        service_config = docs[1]
        
        # Extract configuration for editing
        return _parse_vm_config_for_edit(vm_config, service_config)
        
    except GitOperationError:
        raise
    except Exception as e:
        logger.error(f"Error getting VM config: {e}", exc_info=True)
        raise


def _parse_vm_config_for_edit(vm_config: Dict, service_config: Dict) -> Dict[str, Any]:
    """Parse VM configuration for editing form."""
    spec = vm_config.get('spec', {})
    template_spec = spec.get('template', {}).get('spec', {})
    domain = template_spec.get('domain', {})
    
    # Extract tags
    tags = []
    labels = spec.get('template', {}).get('metadata', {}).get('labels', {})
    for key, value in labels.items():
        if key != 'kubevirt.io/vm':
            tags.append({'key': key, 'value': value})
    
    # Get memory value
    memory_str = domain.get('resources', {}).get('requests', {}).get('memory', '1G')
    memory = int(memory_str.rstrip('G'))
    
    # Get storage
    data_volume = spec.get('dataVolumeTemplates', [{}])[0]
    storage_str = (data_volume.get('spec', {})
                   .get('storage', {})
                   .get('resources', {})
                   .get('requests', {})
                   .get('storage', '10Gi'))
    storage_size = int(storage_str.rstrip('Gi'))
    
    storage_access_mode = (data_volume.get('spec', {})
                           .get('storage', {})
                           .get('accessModes', ['ReadWriteMany'])[0])
    
    # Get service information
    service_annotations = service_config.get('metadata', {}).get('annotations', {})
    
    # Get service ports
    service_ports = []
    for port in service_config.get('spec', {}).get('ports', []):
        service_ports.append({
            'port_name': port['name'],
            'port': port['port'],
            'protocol': port['protocol'],
            'targetPort': port['targetPort']
        })
    
    # Extract user data
    volumes = template_spec.get('volumes', [])
    user_data = ''
    for volume in volumes:
        if 'cloudInitNoCloud' in volume:
            user_data = volume['cloudInitNoCloud'].get('userData', '')
            break
    
    return {
        'vm_name': vm_config.get('metadata', {}).get('name', 'unknown'),
        'tags': tags,
        'cpu_cores': domain.get('cpu', {}).get('cores', 1),
        'memory': memory,
        'storage_size': storage_size,
        'storage_class': data_volume.get('spec', {}).get('storage', {}).get('storageClassName', 'longhorn-rwx'),
        'storage_access_mode': storage_access_mode,
        'image_url': data_volume.get('spec', {}).get('source', {}).get('http', {}).get('url', ''),
        'user_data': user_data,
        'hostname': service_annotations.get('external-dns.alpha.kubernetes.io/hostname', ''),
        'address_pool': service_annotations.get('metallb.universe.tf/address-pool', ''),
        'service_ports': service_ports,
        'service_type': service_config.get('spec', {}).get('type', 'LoadBalancer')
    }


def update_vm_config(config: Config, vm_name: str, form_data: Dict[str, Any]) -> str:
    """
    Update VM configuration in Git repository.
    
    Args:
        config: Application configuration
        vm_name: Name of the VM
        form_data: Updated form data
        
    Returns:
        Commit SHA
    """
    logger.info(f"Updating configuration for VM: {vm_name}")
    
    try:
        # Generate new YAML
        yaml_content = generate_yaml(form_data, config)
        
        # Commit changes
        git_mgr = get_git_manager(config)
        file_name = f"{vm_name}{YAML_EXTENSION}"
        commit_message = GIT_COMMIT_MESSAGE_UPDATE.format(vm_name=vm_name)
        
        commit_sha = git_mgr.commit_file(
            file_path=file_name,
            content=yaml_content,
            commit_message=commit_message,
            subdirectory=config.YAML_SUBDIRECTORY
        )
        
        logger.info(f"Successfully updated VM configuration: {commit_sha}")
        return commit_sha
        
    except Exception as e:
        logger.error(f"Error updating VM config: {e}", exc_info=True)
        raise


def delete_vm_config(config: Config, vm_name: str) -> str:
    """
    Delete VM configuration from Git repository.
    
    Args:
        config: Application configuration
        vm_name: Name of the VM
        
    Returns:
        Commit SHA
    """
    logger.info(f"Deleting configuration for VM: {vm_name}")
    
    try:
        git_mgr = get_git_manager(config)
        file_name = f"{vm_name}{YAML_EXTENSION}"
        commit_message = GIT_COMMIT_MESSAGE_DELETE.format(vm_name=vm_name)
        
        commit_sha = git_mgr.delete_file(
            file_path=file_name,
            commit_message=commit_message,
            subdirectory=config.YAML_SUBDIRECTORY
        )
        
        logger.info(f"Successfully deleted VM configuration: {commit_sha}")
        return commit_sha
        
    except Exception as e:
        logger.error(f"Error deleting VM config: {e}", exc_info=True)
        raise


# Legacy function support - kept for backward compatibility
def ensure_git_clone(config: Config) -> Path:
    """
    Legacy function - ensure repository is cloned.
    
    Args:
        config: Application configuration
        
    Returns:
        Path to repository
    """
    logger.warning("Using legacy ensure_git_clone function")
    git_mgr = get_git_manager(config)
    return git_mgr.ensure_repository()
