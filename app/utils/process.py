import subprocess
import sys
import os
from threading import Thread
import logging

logger = logging.getLogger(__name__)

def run_script_async(script_path, args):
    try:
        cmd = [sys.executable, script_path] + args
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(script_path)
        )
        
        def monitor_process():
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                logger.error(f"Script failed with error: {stderr.decode()}")
            else:
                logger.info(f"Script completed successfully: {stdout.decode()}")
                
        Thread(target=monitor_process).start()
        return process.pid
        
    except Exception as e:
        logger.error(f"Failed to start script: {str(e)}")
        raise