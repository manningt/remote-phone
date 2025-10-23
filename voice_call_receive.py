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
from sdbus_block.modemmanager import MMCall, MMModems
import sdbus
import time
import datetime
import subprocess

import logging
# LOG_FORMAT = "%(asctime)s %(funcName) %(lineno)d %(levelname)s: %(message)s"
# the -6 and -04d do left alignment in the log output
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
wav_file_list = ['/home/judy/SHM-AnsweringMessage-closed-short.wav', '/home/judy/beep.wav']

# async def main():
def main():
	hangup_timeout = 70  # seconds
	start_time = time.monotonic()
	wav_file_index = 0
	previous_call_state = None
	
	audio_process = [None, None]  # to hold arecord and aplay processes
	PLAY = 0
	RECORD = 1

	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	mms = MMModems()
	modem = mms.get_first()
	if modem is None:
		log.fatal('no modem found')
		return

	logging.debug(f'listening for calls on {modem=}')

	# clear existing calls
	call_list = modem.voice.list_calls()
	if len(call_list) > 0:
		logging.debug(f'Clearing existing calls: {call_list}')
		for call_path in call_list:
			modem.voice.delete_call(call_path)

	while True:
		time.sleep(1)
		call_list = modem.voice.list_calls()
		if len(call_list) > 0:
			# logging.debug(f'added call: {call_list=}')
			break

	call = MMCall(call_list[0])
	logging.info(f'Incoming call from number: {call.number}, direction: {call.direction}, state: {call.state}')

	call.accept()
	logging.debug('Call accepted.')

	while True:
		time.sleep(1)
		current_state = call.state_text
		if current_state != previous_call_state:
			logging.info(f'New call state: {current_state}')
		# else:
		# 	logging.debug('. ', end='')

		if current_state == 'MM_CALL_STATE_ACTIVE':
			# the following is not working, audio_port and audio_format are always empty
			# 	print(f'Audio port: {call.audio_port}   Audio format: {call.audio_format}')
			if wav_file_index < len(wav_file_list):
				if audio_process[PLAY] is None:
					play_cmd = ['aplay', '-D', 'hw:3,0', wav_file_list[wav_file_index]]
					logging.debug(f'Starting audio playback of {wav_file_list[wav_file_index]}.')
					audio_process[PLAY] = subprocess.Popen(play_cmd)
				else:
					if audio_process[PLAY].poll() is not None:
						logging.debug(f'Finished aplay of {wav_file_list[wav_file_index]}')
						wav_file_index += 1
						audio_process[PLAY] = None
			else:
				if audio_process[RECORD] is None:
					now = datetime.datetime.now()
					recording_filepath = f"/home/judy/messages/message-{now.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
					logging.debug('Starting recording to {recording_filepath}')
					record_cmd = ['arecord', '-f', 'S16_LE', '-D', 'hw:3,0', recording_filepath]
					audio_process[RECORD] = subprocess.Popen(record_cmd)

		if current_state == 'MM_CALL_STATE_TERMINATED':
			logging.info('stopping aplay and arecord processes.')
			if audio_process[PLAY]:
				audio_process[PLAY].terminate()
			if audio_process[RECORD]:
				audio_process[RECORD].terminate()
			break

		if time.monotonic() - start_time >= hangup_timeout:
			logging.debug('Stopping call, hangup time_out.')
			if audio_process[PLAY]:
				audio_process[PLAY].terminate()
			if audio_process[RECORD]:
				audio_process[RECORD].terminate()
			modem.voice.hangup_all()
			break
	
		previous_call_state = current_state


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
