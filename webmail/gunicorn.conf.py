# Gunicorn configuration file for Webmail Application
import multiprocessing

# Server socket
bind = "0.0.0.0:26000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 350
keepalive = 2

# Process naming
proc_name = "webmail"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Server mechanics
reload = False
preload_app = False
sendfile = True
reuse_port = True
chdir = "/home/jose/webmail_improvmx/webmail"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Webmail application server is ready. Listening on %s", server.address)

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    pass

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")