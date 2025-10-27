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
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename='/tmp/call_receive.log', filemode="w")
wav_file_list = ['/home/judy/current-message.wav', '/home/judy/beep.wav']

def main():
	HANGUP_TIMEOUT = 70  # seconds
	PLAY = 0
	RECORD = 1

	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	mms = MMModems()
	modem = mms.get_first()
	if modem is None:
		log.fatal('no modem found')
		return

	# clear existing calls; may not be necessary
	call_list = modem.voice.list_calls()
	if len(call_list) > 0:
		logging.debug(f'Clearing existing calls: {call_list}')
		for call_path in call_list:
			modem.voice.delete_call(call_path)

	call_list = modem.voice.list_calls()
	previous_call_list_length = len(call_list)

	logging.debug(f'listening for calls on {modem=}')
	print(f'listening for calls on {modem=}')

	while True: #loop forever to receive calls
		while True: # wait for an incoming call
			time.sleep(1)
			call_list = modem.voice.list_calls()
			if len(call_list) > previous_call_list_length:
				previous_call_list_length = len(call_list)
				# logging.debug(f'New call detected: {call_list}')
				break
		
		logging.debug(f'Handling call: {call_list[0]}')
		call = MMCall(call_list[0]) # get the most recent call; new calls are added to the beginning of the list
		logging.info(f'Incoming call from number: {call.number}, direction: {call.direction}, state: {call.state}')

		start_time = time.monotonic()
		wav_file_index = 0
		previous_call_state = None
		audio_process = [None, None]  # to hold arecord and aplay subprocesses

		while True: # monitor call state
			time.sleep(1)
			current_state = call.state_text
			if current_state != previous_call_state:
				logging.info(f'New call state: {current_state}')
			# else:
			# 	logging.debug('. ', end='')

			if current_state == 'MM_CALL_STATE_RINGING_IN':
				call.accept()

			if current_state == 'MM_CALL_STATE_ACTIVE':
				if wav_file_index < len(wav_file_list):
					if audio_process[PLAY] is None:
						play_cmd = ['aplay', '-q', '-D', 'hw:3,0', wav_file_list[wav_file_index]]
						# logging.debug(f'Starting audio playback of {wav_file_list[wav_file_index]}.')
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
						logging.debug(f'Starting recording to {recording_filepath}')
						record_cmd = ['arecord', '-q', '-f', 'S16_LE', '-D', 'hw:3,0', recording_filepath]
						audio_process[RECORD] = subprocess.Popen(record_cmd)

			if current_state == 'MM_CALL_STATE_TERMINATED':
				break

			if time.monotonic() - start_time >= HANGUP_TIMEOUT:
				logging.debug('Stopping call, hangup due to time_out.')
				modem.voice.hangup_all()
				break

			previous_call_state = current_state

		logging.debug('Stopping aplay and arecord processes.')
		if audio_process[PLAY]:
			audio_process[PLAY].terminate()
		if audio_process[RECORD]:
			audio_process[RECORD].terminate()


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		logging.info("Exiting application by user request.")
	except Exception as e:
		logging.error(f"Fatal error in main loop: {e}")
	finally:
		# 5. Clean up any lingering processes
		logging.info("Cleanup complete. Goodbye.")
		sys.exit(0)
