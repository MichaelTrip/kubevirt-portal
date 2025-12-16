# Copilot Instructions for KubeVirt Portal

These rules guide AI coding agents working on this repo. Focus on the concrete patterns used here rather than generic Flask or Kube/KubeVirt advice.

## Big Picture

- Architecture: Flask app serving HTML pages and WebSockets; VM specs are generated via Jinja2 templates and committed to a Git repo. Kubernetes is queried live for cluster VM state and proxied for Console/VNC.
- Data flow (create/edit VM): `WTForms (app/forms.py)` → `VMConfigSchema (Pydantic)` → `TemplateManager` renders `vm` + `service` YAML → `GitOperationManager` writes `<vm>.yaml` under `Config.YAML_SUBDIRECTORY` and pushes.
- Separation of concerns:
  - Validation: `app/schemas.py` (Pydantic, cross-field rules, strict ranges/patterns)
  - Templating: `app/template_manager.py` with profiles in `app/templates/profiles/*.yaml`
  - Git transactions: `app/git_manager.py` (thread-safe, atomic commit + push, auto-clone/pull/reset)
  - K8s access: `app/k8s_utils.py` (list VMs, build clients)
  - Web/UI & WebSockets: `app/routes.py` (pages, SSH terminal, KubeVirt console & VNC proxies)

## Developer Workflows

- Required env vars: `GIT_REPO_URL`, `GIT_USERNAME`, `GIT_TOKEN`. `Config.validate_config()` exits early if missing (runs at import and app init).
- Local run: `python run.py` (honors `DEBUG=true`), or `FLASK_DEBUG=1 python run.py`.
- Bootstrap: `./setup-dev.sh` creates venv, installs deps, checks templates, and scaffolds `.env`.
- Docker: `docker build -t kubevirt-portal .` then `docker run -p 5000:5000 --env-file .env kubevirt-portal` (uses `gunicorn` as per `Dockerfile`).
- Kubernetes deploy: manifests under `kubernetes/` (`configmap.yaml`, `secret.yaml`, `deployment.yaml`, `service.yaml`). Port-forward with `kubectl port-forward svc/kubevirt-portal 5000:80`.

## Project Conventions

- YAML layout: One file per VM, named `<vm_name>.yaml` containing two docs separated by `---`: first the `VirtualMachine`, second the `Service`.
- Defaults/flags from `config.py`: `YAML_SUBDIRECTORY` (default `virtualmachines/`), `EXTERNAL_DNS_ENABLED`, `METALLB_ENABLED`, `CLUSTER_VMS_ENABLED`, `METALLB_DEFAULT_POOL`, `EXTERNAL_DNS_DOMAIN`.
- Namespace assumptions: API calls in `routes.py` default to namespace `virtualmachines` for VM/VMI and Service lookups.
- Service type: Only `LoadBalancer` and `ClusterIP` are exposed in the UI; schema allows `NodePort` but templates/behavior primarily target `LoadBalancer`.
- Validation is strict: service ports must be non-empty and unique by name and number; VM/storage sizes are range-checked; names must match Kubernetes DNS patterns.

## Git & Templates

- Git storage: Repo is cloned to `Config.GIT_CLONE_DIR/repo`; remote URL includes embedded credentials. Branch `main` preferred; auto-fallback to default branch.
- Transactions: Use `GitOperationManager.transaction()` semantics via helpers in `app/utils.py` to ensure atomic writes and push-or-rollback behavior.
- Templates: Base Jinja files in `app/templates/base/`; profiles in `app/templates/profiles/*.yaml` choose which templates to use and provide defaults; reusable snippets under `app/templates/snippets/`.
- Rendering entrypoint: `TemplateManager.render_complete_config(context, profile)` returns `vm + service` YAML (validated for YAML syntax).

## Kubernetes Integration

- Cluster VMs view: `k8s_utils.list_running_vms()` aggregates VMs, VMIs, and Services across namespaces; `routes.py` renders `cluster_vms.html` if `CLUSTER_VMS_ENABLED`.
- Power control: `routes.py:power_vm()` patches `spec.running` on the `VirtualMachine` CR.
- Raw YAML endpoints: `/api/vm/<name>/yaml` and `/api/service/<name>/yaml` fetch live resources (namespace default `virtualmachines`).

## Profiles & Namespace

- Profiles live in `app/templates/profiles/*.yaml` and set defaults + which templates to use.
  - `default`: `LoadBalancer`, IPv6 enabled, modest defaults.
  - `development`: `ClusterIP`, IPv6 disabled, minimal CPU/mem/storage.
  - `production`: `LoadBalancer`, IPv6 enabled, higher resources.
- Select with `TemplateManager.render_complete_config(ctx, profile_name)`; UI currently uses defaults.
- Namespace defaults: routes assume `virtualmachines` for VM/VMI/Service operations; cluster listing spans all namespaces.

## WebSockets (SSH/Console/VNC)

- SSH terminal: `GET /terminal/<vm>?host=<ip>` view; WS at `/terminal/ws` expects first message to be JSON `{"type":"auth","username":"...","password":"..."}`; then forwards keystrokes to Paramiko `invoke_shell()`.
- KubeVirt Console: `/console/<vm>` and WS `/console/ws` bridge to KubeVirt `.../virtualmachineinstances/<vm>/console`; supports JSON resize `{type:"resize", cols, rows}`; avoids setting subprotocols.
- VNC: `/vnc/<vm>` and WS `/vnc/ws` bridge to `.../vnc`; sends `Sec-WebSocket-Protocol: binary.kubevirt.io` header and auto-detects framing (channel 0/1/2/3/4).

## Example: Hostname Field Flow

- Schema: `schemas.VMConfigSchema.hostname` (DNS validation) and `service_type` gating.
- Form: `forms.VMForm.hostname`; in `routes.create_vm/edit_vm`, hostname is only passed when `service_type == 'LoadBalancer'`.
- Template: `templates/base/service-base.yaml.j2` writes `external-dns.alpha.kubernetes.io/hostname` under `metadata.annotations` only when `hostname` is set.
- Net effect: ExternalDNS hostname is active only for LoadBalancer Services; ClusterIP ignores hostname.

## Adding Features Safely

- New VM fields: Update `app/schemas.py` (validation), `app/forms.py` (inputs), and referenced templates in `app/templates/base/` and/or profile defaults. Keep schema as source of truth; `TemplateManager` consumes `VMConfigSchema.to_template_dict()`.
- New template variants: Add a profile under `app/templates/profiles/*.yaml` with `templates.vm` and `templates.service` paths; select via `TemplateManager.render_complete_config(..., profile_name)`.
- Git ops: Prefer `app/utils.py` helpers (`commit_to_git`, `update_vm_config`, `delete_vm_config`) over direct `GitOperationManager` calls for consistency.

## Common Pitfalls

- Missing env vars cause immediate process exit during import; set `.env` or export vars before running.
- `GIT_CLONE_DIR` must be writable; default `/tmp/kubevirt-portal/clones` is fine locally, use a PVC in Kubernetes.
- Strict schema rules: ensure at least one `service_port`, storage >= memory, and valid DNS-compliant names.
- Security: CSRF is disabled (`WTF_CSRF_ENABLED=False`); do not expose this app publicly without auth and proper hardening.

## Quick References

- Key files: `app/routes.py`, `app/utils.py`, `app/git_manager.py`, `app/template_manager.py`, `app/schemas.py`, `config.py`, `kubernetes/*.yaml`.
- Run dev: `python run.py` (set `DEBUG=true` in `.env` for verbose logs).
- Render a template (REPL):
  ```bash
  python - <<'PY'
  from app.template_manager import TemplateManager
  from app.schemas import VMConfigSchema, ServicePortSchema
  cfg = VMConfigSchema(vm_name='demo', cpu_cores=2, memory=4, storage_size=20,
                       storage_class='longhorn-rwx', image_url='https://example/img.qcow2',
                       service_ports=[ServicePortSchema(port_name='ssh', port=22, targetPort=22)])
  print(TemplateManager().render_complete_config(cfg.to_template_dict()))
  PY
  ```
