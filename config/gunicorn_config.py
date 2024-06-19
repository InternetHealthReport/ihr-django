import multiprocessing

bind = "0.0.0.0:8000"  # Replace with your desired IP and port
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
timeout = 120

preload_app = True
