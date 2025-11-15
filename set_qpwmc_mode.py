#!/usr/bin/env python
# this script needs to be run with sudo to have permission to stop/start ModemManager and run mmcli commands
import sys, os
import time
import subprocess

import logging
logger = logging.getLogger('my_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('/tmp/py_set_qpwmc.log', mode='w')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.propagate = False  # Prevent propagation to the console

def log_subprocess_output(pipe):
   start_time = time.time()
   for line in iter(pipe.readline, b''): # b'\n'-separated lines
      logger.debug(f'subprocess output: {line.decode().strip()}')
      if time.time() - start_time > 40:
         logger.debug('timeout reached, stopping subprocess output logging')
         return
      # if 'RSSI (LTE):' in line.decode():
      #    logger.info(f'got RSSI (LTE) line from subprocess: {line.decode().strip()}')
      #    return

def set_qpcmv():
   logger.debug('before stopping MM service')
   cmd = ['systemctl', 'stop', 'ModemManager.service']
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logger.error(f'Failed to stop ModemManager: output={output.decode()}  error={error.decode()}')
      sys.exit(1)
   else:
      logger.info(f'Stopped ModemManager service: output={output.decode()}  error={error.decode()}')
   # print(f'stop MM: q output={output.decode()}  error={error.decode()}')

   cmd = ['ModemManager', '--debug']
   debug_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   logger.info(f'Started ModemManager in debug mode; PID={debug_process.pid}')
   with debug_process.stdout:
      log_subprocess_output(debug_process.stdout)
   # this process will run until it is terminated (below)

   # sending the command in the following format gets an error, so using a shell script instead
   # cmd = ['sudo', 'mmcli', '-m', '0', '--command=\'+QPCMV=1,2\'']
   cmd = ['set_qpwmc_mode.sh']
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logger.fatal(f'Failed to set QPCMV: {output=}  {error=}')
   else:
      # verify the setting
      # cmd = ['mmcli', '-m', '0', '--command=\'+QPCMV?\'']
      cmd = ['/home/judy/repos/remote-phone/get_qpwmc_mode.sh']
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      output, error = process.communicate()
      if '+QPCMV: 1,2' in output.decode():
         logger.info('QPCMV successfully set to 1,2')
      logger.debug(f'get QPCMV: {output=}  {error=}')

   debug_process.terminate()
   debug_process.wait()

   cmd = ['systemctl', 'start', 'ModemManager.service']
   process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logger.error(f'Failed to start ModemManager: {output=}  {error=}')
   else:
      logger.info('Started ModemManager service')


if __name__ == "__main__":
	try:
		set_qpcmv()
	except KeyboardInterrupt:
		logger.info("Exiting application by user request.")
	except Exception as e:
		logger.error(f"Fatal error in main loop: {e}")
