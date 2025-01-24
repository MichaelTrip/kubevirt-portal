import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 4  # Fixed number of workers
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Process naming
proc_name = 'kubevirt-portal'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

# Hook points
def on_starting(server):
    """Log when server starts"""
    server.log.info("Starting KubeVirt Portal")

def worker_abort(worker):
    """Log when a worker aborts"""
    worker.log.info(f"Worker {worker.pid} aborted")
