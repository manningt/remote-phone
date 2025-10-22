#!/usr/bin/env python
import sys, os
import time
import subprocess

import logging
# LOG_FORMAT = "%(asctime)s %(funcName) %(lineno)d %(levelname)s: %(message)s"
# the -6 and -04d do left alignment in the log output
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename='/home/judy/py_set_qpwmc.log', filemode="w")

def log_subprocess_output(pipe):
   start_time = time.time()
   for line in iter(pipe.readline, b''): # b'\n'-separated lines
      logging.debug(f'subprocess output: {line.decode().strip()}')
      if time.time() - start_time > 40:
         logging.debug('timeout reached, stopping subprocess output logging')
         return
      # if 'RSSI (LTE):' in line.decode():
      #    logging.info(f'got RSSI (LTE) line from subprocess: {line.decode().strip()}')
      #    return

def set_qpcmv():
   logging.debug('before stopping MM service')
   cmd = ['sudo', 'systemctl', 'stop', 'ModemManager.service']
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logging.error(f'Failed to stop ModemManager: output={output.decode()}  error={error.decode()}')
      sys.exit(1)
   else:
      logging.debug(f'Stopped ModemManager service: output={output.decode()}  error={error.decode()}')
   # print(f'stop MM: q output={output.decode()}  error={error.decode()}')

   cmd = ['sudo', 'ModemManager', '--debug']
   debug_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   logging.debug(f'Started ModemManager in debug mode; PID={debug_process.pid}')
   with debug_process.stdout:
      log_subprocess_output(debug_process.stdout)
   # this process will run until we kill 

   # sending the command in the following format gets an error, so using a shell script instead
   # cmd = ['sudo', 'mmcli', '-m', '0', '--command=\'+QPCMV=1,2\'']
   cmd = ['/home/judy/repos/remote-phone/set_qpwmc_mode.sh']
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logging.fatal(f'Failed to set QPCMV: output={output.decode().rstrip()}  error={error.decode().rstrip()}')
   else:
      # verify the setting
      # cmd = ['mmcli', '-m', '0', '--command=\'+QPCMV?\'']
      cmd = ['/home/judy/repos/remote-phone/get_qpwmc_mode.sh']
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      output, error = process.communicate()
      if '+QPCMV: 1,2' in output.decode():
         logging.info('QPCMV successfully set to 1,2')
      logging.debug(f'get QPCMV: output={output.decode().rstrip()}  error={error.decode()}')

   debug_process.terminate()
   debug_process.wait()

   cmd = ['sudo', 'systemctl', 'start', 'ModemManager.service']
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logging.error(f'Failed to start ModemManager: output={output.decode().rstrip()}  error={error.decode()}')
   else:
      logging.debug('Started ModemManager service')


if __name__ == "__main__":
	try:
		set_qpcmv()
	except KeyboardInterrupt:
		logging.info("Exiting application by user request.")
	except Exception as e:
		logging.error(f"Fatal error in main loop: {e}")
