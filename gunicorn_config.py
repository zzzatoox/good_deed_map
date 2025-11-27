# Gunicorn configuration
import multiprocessing

bind = "127.0.0.1:8000"
# Reduce workers for hackathon - 2-4 workers is enough
workers = min(4, multiprocessing.cpu_count() * 2 + 1)
worker_class = "sync"
timeout = 120
keepalive = 5
# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100
# Increase worker connections for mobile traffic
worker_connections = 1000
accesslog = "-"
errorlog = "-"
loglevel = "info"
