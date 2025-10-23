#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
#   "jsonpickle>=2.2.0",
# ]
# ///

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../python-sdbus-modemmanager'))
import sdbus
import time
from sdbus_block.modemmanager import MMCall, MMModems
import subprocess

import logging
# LOG_FORMAT = "%(asctime)s %(funcName) %(lineno)d %(levelname)s: %(message)s"
# the -6 and -04d do left alignment in the log output
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


# async def main():
def main():
	hangup_timeout = 70  # seconds
	start_time = time.monotonic()
	
	audio_process = [None, None]  # to hold arecord and aplay processes
	PLAY = 0
	RECORD = 1

	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	mms = MMModems()
	modem = mms.get_first()
	if modem is None:
		print('no modem found')
		return

	logging.debug(f'listening for calls on {modem=}')

	# clear existing calls
	call_list = modem.voice.list_calls()
	if len(call_list) > 0:
		logging.info(f'Clearing existing calls: {call_list}')
		for call_path in call_list:
			modem.voice.delete_call(call_path)

	while True:
		time.sleep(1)
		call_list = modem.voice.list_calls()
		if len(call_list) > 0:
			logging.info(f'{call_list=}')
			break

	call = MMCall(call_list[0])
	logging.info(f'Incoming call from number: {call.number}, direction: {call.direction}, state: {call.state}')

	call.accept()
	logging.debug('Call accepted.')

	while True:
		time.sleep(1)
		current_state = call.state_text
		print(f'Current call state: {current_state}')

		if current_state == 'MM_CALL_STATE_ACTIVE':
			# the following is not working, audio_port and audio_format are always empty
			# 	print(f'Audio port: {call.audio_port}   Audio format: {call.audio_format}')
			if audio_process[PLAY] is None:
				play_cmd = ['aplay', '-D', 'hw:3,0', '/home/judy/BlueShadowsOnTheTrail_8k.wav']
				print(f'Starting audio playback.')
				audio_process[PLAY] = subprocess.Popen(play_cmd)

			if audio_process[RECORD] is None:
				record_cmd = ['arecord', '-f', 'S16_LE', '-D', 'hw:3,0', '/home/judy/recording2.wav']
				audio_process[RECORD] = subprocess.Popen(record_cmd)

		if current_state == 'MM_CALL_STATE_TERMINATED':
			print('stopping aplay and arecord processes.')
			if audio_process[PLAY]:
				audio_process[PLAY].terminate()
			if audio_process[RECORD]:
				audio_process[RECORD].terminate()
			break

		if time.monotonic() - start_time >= hangup_timeout:
			print('Stopping call, hangup time_out.')
			if audio_process[PLAY]:
				audio_process[PLAY].terminate()
			if audio_process[RECORD]:
				audio_process[RECORD].terminate()
			modem.voice.hangup_all()
			break



if __name__ == "__main__":
	try:
		# asyncio.run(main())
		main()
	except KeyboardInterrupt:
		logging.info("Exiting application by user request.")
	except Exception as e:
		logging.error(f"Fatal error in main loop: {e}")
	finally:
		# 5. Clean up any lingering processes
      #   stop_audio_capture()
		logging.info("Cleanup complete. Goodbye.")
		sys.exit(0)
