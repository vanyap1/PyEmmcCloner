from threading import Thread
import time
import threading
import random
import string
import re
import os
import time
import subprocess
import shlex
import pty
from threading import Thread


class DiskAsyncService:
    def __init__(self, procInfoCb=None, statusCb=None):
        self.procInfoCb = procInfoCb
        self.statusCb = statusCb
        self.process = None
        self.task_status = "Idle"
        self.task_thread = None
        self.stop_requested = False
        self.targetDev = None
        self.rootFsImageDump = None
        self.inventoryFile = None
        self.preconfigScript = None
        self.current_task = None
        self.lock = threading.Lock()
        self.ubootPath = "boot/"
        self.inventoryFilesPath = "inventory/"
        self.preconfigScriptsPath = "preConfigScr/"
        self.buiderScripts = None #"diskPrepare.sh"
        self.work_dir = "diskBuilder"
        self.imagesPath = "rootfsimgs"
        self.result = "idle"
        self.logs_dir = os.path.join(self.work_dir, "rootfsimgs")
        self.log_filename = os.path.join(self.logs_dir, f"disk_task_{int(time.time())}.log")
        self._clear_logs()
    
    def _clear_logs(self):
        """Clear old log files in the logs directory."""

        
        if os.path.exists(self.logs_dir):
            for filename in os.listdir(self.logs_dir):
                file_path = os.path.join(self.logs_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"Deleted old log: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        else:
            os.makedirs(self.logs_dir)
            print(f"Created logs directory: {self.logs_dir}")


    def perform_async_task(self, script=None, targetDev=None, rootFsImageDump=None, checkFilesBefore=True):
        with self.lock:
            self.buiderScripts = script
            if targetDev is None or rootFsImageDump is None:
                print("Target device or root filesystem image dump not specified.")
                self.result = "error"
            if self.buiderScripts == None:
                print("Builder script not defined.")
                self.result = "error"
                return {"status": "Error: Builder script not defined", "current_task": None}
            if self.task_thread and self.task_thread.is_alive():
                print(f"Task is already running: {self.current_task}")
                return {"status": "Task is already running", "current_task": self.current_task}
            
            if not os.path.exists(f"/dev/{targetDev}"):
                print(f"Target device /dev/{targetDev} does not exist.")
                self.result = "error"
                return {"status": "Error: Target device does not exist", "current_task": None}
            if not os.path.exists(f"{self.work_dir}/{self.imagesPath}/{rootFsImageDump}") and checkFilesBefore:
                print(f"Root filesystem zip {rootFsImageDump} does not exist.")
                self.result = "error"
                return {"status": "Error: Root filesystem zip does not exist", "current_task": None}
            

            self.targetDev = f"/dev/{targetDev}"
            self.rootFsImageDump = rootFsImageDump
            self.current_task = f"{self.targetDev}"
            self.stop_requested = False
            self.task_status = "Starting"
            self.result = "none"
            self.log_filename = os.path.join(self.logs_dir, f"{rootFsImageDump}.log")
            self.task_thread = Thread(target=self._run_task)
            self.task_thread.daemon = True
            self.task_thread.start()
            return {"status": "Task started", "current_task": self.current_task}

    def _getFileLen(self, fileName) -> int:
        try:
            return os.path.getsize(f"{self.work_dir}/{self.imagesPath}/{fileName}")
        except (FileNotFoundError, OSError):
            return 0
    def _calcPercent(self, written, total) -> int:
        try:
            written = int(written)
            total = int(total)

            if total <= 0 or written < 0:
                return 0

            return int((written / total) * 100)
        except Exception:
            return 0

    def _run_task(self):
        self.task_status = "In Progress"
        self._progressInfoShort = ""
        self.result = "undone"
        logs_dir = os.path.join(self.work_dir, "logs")
        

        self.cmd = f'bash {self.buiderScripts} -d {self.targetDev} -a {self.rootFsImageDump}'
        print(self.cmd)
        fileSize = self._getFileLen(self.rootFsImageDump)
        with open(self.log_filename, 'w') as log_file:
            log_file.write(f"Task started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"Command: {self.cmd}\n")
            log_file.write(f"Working directory: {self.work_dir}\n")
            log_file.write("="*50 + "\n")
        master_fd, slave_fd = pty.openpty()
        start_time = time.time()
        self.process = subprocess.Popen(shlex.split(self.cmd), stdout=slave_fd, stderr=subprocess.STDOUT, close_fds=True, cwd=self.work_dir)
        os.close(slave_fd)
        with open(self.log_filename, 'a') as log_file:
            while True:
                try:
                    if self.stop_requested:
                        log_file.write("\n>>> Task stopped by user <<<\n")
                        self.process.terminate()
                        time.sleep(0.5)
                        if self.process.poll() is None:
                            self.process.kill()
                        break

                    output = os.read(master_fd, 1024).decode('utf-8', errors='replace')
                    if output:
                        
                        
                        #print(re.sub(r'[^\x20-\x7E]', ',', output2))
                        datapart = output.replace("(", "").replace(",", "").replace("\r", "").replace(")", "").split(" ")
                        print("dp: ", datapart, " len:", len(datapart))
                        if len(datapart) == 11:
                            self._progressInfoShort = f"{datapart[2]}{datapart[3]}; {datapart[9]}{datapart[10]}; {datapart[7]}{datapart[8]}; progress%: {self._calcPercent(datapart[0], fileSize)}"
                            self.task_status = self._progressInfoShort 
                        else:
                            self.task_status = f"In Progress - {output.strip()}"

                        
                        print(f">>>: {self._progressInfoShort}")
                        #print(output, end='')
                        self.procInfoCb(self._progressInfoShort)
                        log_file.write(output)
                        log_file.flush()
                    if self.process.poll() is not None:
                        break
                except Exception as e:               
                    break
            log_file.write(f"Task ended at: {time.strftime('%Y-%m-%d %H:%M:%S')}; Process duration: {time.time() - start_time:.2f} seconds\n")
        os.close(master_fd)
        retcode = self.process.wait()
        print(f"Process finished with return code: {retcode}")
        
        if self.stop_requested:
            #self.task_status = "Stopped"
            self.result = "stopped"
            self.statusCb("stopped")
            self.procInfoCb(f"stopped; {self.task_status}")
            print(f"Task stopped: {self.current_task}")
            return
        
        if retcode != 0:
            self.task_status = "Error"
            self.result = "error"
            print(f"Async task failed: {self.current_task}")
            self.statusCb("error")
            self.procInfoCb(f"error; {self.task_status}")
            return
        self.task_status = "Completed"
        self.result = "success"
        self.procInfoCb("Completed")
        self.statusCb("success")
        print(f"Completed async task: {self.current_task}")

    def stop_task(self):
        if self.task_thread and self.task_thread.is_alive():
            print(f"Stopping task: {self.current_task}")
            self.stop_requested = True
            
            self.task_thread.join(timeout=5.0)
            
            if self.task_thread.is_alive() and self.process:
                print("Force killing process...")
                try:
                    self.process.kill()
                except:
                    pass
            
            return True
        else:
            print("No active task to stop")
            return False
    
    def get_task_status(self):
        return {
            "current_task": self.current_task,
            "status": self.task_status,
            "is_running": self.task_thread.is_alive() if self.task_thread else False,
            "result": self.result   
        }
    
    def is_task_running(self):
        return self.task_thread and self.task_thread.is_alive()


if __name__ == "__main__":
    
    def cb_print(output):
        print(f"Callback Output: {output}")
    def status_print(status):
        print(f"Status Update: {status}")

    service = DiskAsyncService(cb_print, status_print)
    targetScriptDiskBuilder = "diskPrepare.sh"  # Example script path
    targetScriptImageDumper = "imgPrepare.sh"
    targetDev = "mmca"  # Example target device
    rootFsImageMaster = "sdhRootFsDump.img"  # Example root filesystem zip path
    rootFsImageDump = "sdhRootFsDump.img"  # Example root filesystem zip path


    print("\nEnter 'w' to begin task disk write, 'r' to begin task image dump, 's' to check status, 't' to stop task, 'q' to quit.")
    while True:
        
        cmd = input("\ncmd: ").strip().lower()
        if cmd == "w":
            print(f"\n1. Starting for device: {targetDev}, rootFsImage: {rootFsImageMaster}")
            service.perform_async_task(targetScriptDiskBuilder, targetDev, rootFsImageMaster, True)
        if cmd == "r":
            print(f"\n1. Starting for device: {targetDev}, rootFsImage: {rootFsImageDump}")
            service.perform_async_task(targetScriptImageDumper, targetDev, rootFsImageDump, False)

        if cmd == "s":
            status = service.get_task_status()
            print(f"Status: {status['status']} | Task: {status['current_task']} | Running: {status['is_running']} | Result: {status['result']}")
        if cmd == "q":
            service.stop_task()
            print("Exiting...")
            break
        if cmd == "t":
            service.stop_task()
            print("Stop requested.")
        
        #if not status['is_running']:
        #    print("Task completed. Running again...")
        #    service.perform_async_task(f"/dev/sd{random.choice(string.ascii_lowercase)}", rootFsImageDump)