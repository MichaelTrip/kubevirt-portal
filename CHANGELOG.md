# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2025-01-30

### Added
- Feature flag for Cluster VMs page visibility
- Conditional navigation menu items based on feature flags
- Route protection for disabled features

### Changed
- Updated navigation menu to respect feature flags
- Improved user feedback for disabled features

## [1.3.0] - 2025-01-29

### Added
- Support for custom storage access modes
- Configurable Git clone directory
- Enhanced environment variable validation
- ExternalDNS Integration:
  - Enable with `EXTERNAL_DNS_ENABLED=true`
  - Automatically manages DNS records for VMs
  - Configurable through hostname field in VM creation
  - Supports multiple DNS providers via ExternalDNS
  - Adds `external-dns.alpha.kubernetes.io/hostname` annotation to Services
  - Example: `external-dns.alpha.kubernetes.io/hostname: myvm.example.com`
- MetalLB Integration:
  - Enable with `METALLB_ENABLED=true`
  - Provides LoadBalancer services for VMs
  - Configurable IP address pools via annotations
  - Adds `metallb.universe.tf/address-pool` annotation to Services
  - Example: `metallb.universe.tf/address-pool: production-pool`
  - Supports both layer 2 and BGP modes
  - Automatic IP allocation for VM services

### Changed
- Improved error handling for Git operations
- Better feedback for configuration issues
- Updated documentation for new environment variables
- Enhanced service configuration options
- Improved network integration capabilities

## [1.2.1] - 2025-01-29

### Added
- Enhanced error handling for SSH terminal connections
- Improved validation for service port configurations
- Better feedback for Git operations status

### Changed
- Optimized Git repository synchronization
- Updated UI feedback messages
- Improved logging for debugging purposes

### Fixed
- SSH terminal connection stability issues
- Service port validation edge cases
- Git repository locking conflicts

## [1.2.0] - 2025-01-29

### Added
- Web-based SSH terminal access to VMs
- Power management controls (start/stop) for VMs
- Live VM status monitoring in cluster view
- YAML configuration viewer for both VMs and Services
- Enhanced service port management with protocol selection
- Improved tag management system

### Changed
- Updated UI with dark theme support
- Enhanced error handling and user feedback
- Improved Git repository management
- Better cloud-init integration
- More detailed VM status information

### Fixed
- Service port handling in form submissions
- Git repository synchronization issues
- VM configuration validation
- WebSocket connection stability

## [1.1.0] - 2025-01-24

### Added
- Enhanced cluster VM monitoring:
  - Real-time VM status tracking
  - Node placement information
  - IP address monitoring
  - Service status integration
  - YAML configuration viewer
- Improved UI/UX:
  - Dual view modes (card/table) with persistence
  - Enhanced VM details display
  - Better service port management
  - Improved tag management interface
- Technical improvements:
  - Comprehensive logging system
  - Enhanced error handling
  - Better Kubernetes integration
  - Improved Git operations reliability

## [1.0.0] - 2025-01-24

### Added
- Initial release with complete VM management functionality:
  - Create, edit, and delete VM configurations
  - Git-based configuration storage
  - Kubernetes integration for live VM status
  - Web UI with card and table views
  - Service port management
  - Tag management
  - Cloud-init integration
  - Storage class support
  - MetalLB integration
  - YAML preview functionality
