# scheduler_wrapper.py
import time
import importlib
import sys
import os

module_name = os.environ.get("SCHEDULED_WORKER_MODULE")
interval = int(os.environ.get("SCHEDULED_WORKER_INTERVAL", "3600"))

if not module_name:
    raise ValueError("SCHEDULED_WORKER_MODULE is not defined")

print(f"🚀 Starting scheduled worker: {module_name} every {interval}s")

def run():
    if module_name is None:
        raise ValueError("No environment variable SCHEDULED_WORKER_MODULE was defined")
    
    mod = importlib.import_module(module_name)
    if hasattr(mod, "main"):
        mod.main()
    else:
        raise AttributeError(f"Module {module_name} must define a 'main()' function")

while True:
    print(f"⏱️ Running task: {module_name}")
    run()
    print(f"✅ Done running {module_name}. Sleeping for {interval}s...\n")
    time.sleep(interval)