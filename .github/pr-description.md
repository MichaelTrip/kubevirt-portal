# Feature Flags Implementation and Navigation Updates

## Changes from CHANGELOG v1.3.1

### Added
- Feature flag for Cluster VMs page visibility
- Conditional navigation menu items based on feature flags
- Route protection for disabled features

### Changed
- Updated navigation menu to respect feature flags
- Improved user feedback for disabled features

## Implementation Details
This PR introduces feature flags to control access to certain functionality, particularly the Cluster VMs page. The implementation includes:

- Environment variable based feature flags
- Protected routes for disabled features
- Enhanced user feedback when attempting to access disabled features
- Updated navigation menu that dynamically shows/hides based on feature flags

## Testing Done
- Verified feature flag functionality in development environment
- Tested all navigation paths with features enabled/disabled
- Confirmed proper feedback messages for disabled features
