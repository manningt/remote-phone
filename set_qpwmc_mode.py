#!/usr/bin/env python
import sys, os
import time
import subprocess

import logging
# LOG_FORMAT = "%(asctime)s %(funcName) %(lineno)d %(levelname)s: %(message)s"
# the -6 and -04d do left alignment in the log output
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


def set_qpcmv():
   logging.debug('before stopping MM service')
   mm_stop_cmd = ['sudo', 'systemctl', 'stop', 'ModemManager.service']
   process = subprocess.Popen(mm_stop_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      logging.error(f'Failed to stop ModemManager: output={output.decode()}  error={error.decode()}')
      return
   else:
      logging.debug('Stopped ModemManager service')
   # print(f'stop MM: q output={output.decode()}  error={error.decode()}')

   logging.debug('before starting MM in debug mode')
   mm_debug_cmd = ['sudo', 'ModemManager', '--debug']
   debug_process = subprocess.Popen(mm_debug_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   logging.debug(f'Started ModemManager in debug mode; PID={debug_process.pid}')
   # this process will run until we kill 
   
   print('waiting for ModemManager to start', end='')
   for _ in range(10):
      print(' .', end='', flush=True)
      time.sleep(1)
   print(' .')
   
   logging.debug('before setting QPCMV')
   set_qpcmv_cmd = ['sudo', 'mmcli', '-m', '0', "--command='+QPCMV=1,2'"]
   process = subprocess.Popen(set_qpcmv_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   output, error = process.communicate()
   if process.returncode != 0:
      print(f'Failed to set QPCMV: output={output.decode()}  error={error.decode()}')
      return

   debug_process.kill()


if __name__ == "__main__":
	try:
		set_qpcmv()
	except KeyboardInterrupt:
		logging.info("Exiting application by user request.")
	except Exception as e:
		logging.error(f"Fatal error in main loop: {e}")
