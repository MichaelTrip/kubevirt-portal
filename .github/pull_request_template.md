# Feature: Optional MetalLB and ExternalDNS Integration

## Description
This PR adds optional integration with MetalLB and ExternalDNS, allowing for more flexible network configuration of virtual machines.

### Added
- ExternalDNS Integration:
  - Enable with `EXTERNAL_DNS_ENABLED=true`
  - Automatically manages DNS records for VMs
  - Configurable through hostname field in VM creation
  - Adds `external-dns.alpha.kubernetes.io/hostname` annotation to Services
  - Example: `external-dns.alpha.kubernetes.io/hostname: myvm.example.com`

- MetalLB Integration:
  - Enable with `METALLB_ENABLED=true`
  - Provides LoadBalancer services for VMs
  - Configurable IP address pools via annotations
  - Adds `metallb.universe.tf/address-pool` annotation to Services
  - Example: `metallb.universe.tf/address-pool: production-pool`

### Changed
- Improved error handling for Git operations
- Better feedback for configuration issues
- Updated documentation for new environment variables
- Enhanced service configuration options
- Improved network integration capabilities

## Testing Done
- Verified MetalLB integration with test VM deployments
- Confirmed ExternalDNS record creation
- Tested both features in isolation and together
- Validated error handling for misconfigured scenarios

## Notes
- Both features are optional and disabled by default
- Configuration is done via environment variables
- Existing deployments without these features will continue to work as before
