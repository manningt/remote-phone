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
from get_wav_duration import get_wav_duration
import wave

import logging
# LOG_FORMAT = "%(asctime)s %(funcName) %(lineno)d %(levelname)s: %(message)s"
# the -6 and -04d do left alignment in the log output
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename='/tmp/call_receive.log', filemode="w")
home_path = os.path.expanduser("~")
messages_path = os.path.join(home_path, 'messages')
wav_file_list = [os.path.join(home_path, 'current-message.wav'), os.path.join(home_path, 'beep.wav')]

def email_message_notification(phone_number, audio_filepath, recipient):
	#echo "body of email" | mutt -s "subject of email" joe@example.com
	try:
		with wave.open(audio_filepath, 'rb') as wav_file:
			# metadata = wav_file.getparams()
			# logging.debug(f'Wave file {audio_filepath} metadata: {metadata}')
			framerate = wav_file.getframerate()
			n_frames = wav_file.getnframes()
			message_duration = n_frames / float(framerate)
			logging.debug(f'Wave file {audio_filepath} duration: {message_duration:.1f} seconds (n_frames={n_frames}  framerate={framerate})')
	except wave.Error as e:
		logging.warning(f'Error reading wav file {audio_filepath}: {e}')
		message_duration = 0.0

	# return

	transcription = "Transcription TBD"
	body = f'From {phone_number}:  {transcription}'
	cmd = ['echo', body]
	echo_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

	subject = f'Message from {phone_number} - Duration: {message_duration:.0f} seconds'
	cmd = ['mutt', '-s', subject, f'{recipient}']
	mutt_process = subprocess.Popen(cmd, stdin=echo_process.stdout, stdout=subprocess.PIPE)
	echo_process.stdout.close()

	output, error = mutt_process.communicate()
	if mutt_process.returncode != 0:
		logging.error(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
		# logging.error(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
	else:
		logging.debug(f'Successfully emailed text message to {recipient}')


def main(recipient):
	HANGUP_TIMEOUT = 70  # seconds
	PLAY = 0
	RECORD = 1

	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	mms = MMModems()
	modem = mms.get_first()
	if modem is None:
		logging.fatal('no modem found - quiting')
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
						recording_filepath = os.path.join(messages_path, f"message-{now.strftime('%Y-%m-%d_%H-%M-%S')}.wav")
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
		if recipient:
			email_message_notification(call.number, recording_filepath, recipient)


if __name__ == "__main__":
	recipient = None
	if len(sys.argv) < 2:
		logging.warning(f'No email recipient specified; Usage: {sys.argv[0]} <email_recipient>\n\tNot sending emails.')
		print(f'No email recipient specified; Usage: {sys.argv[0]} <email_recipient>\n\tNot sending emails.')
	else:
		recipient = sys.argv[1]

	main(recipient)
	# try:
	# 	main(recipient)
	# except KeyboardInterrupt:
	# 	logging.info("Exiting application by user request.")
	# except Exception as e:
	# 	logging.error(f"Fatal error in main loop: {e}")
	# finally:
	# 	# 5. Clean up any lingering processes
	# 	logging.info("Cleanup complete. Goodbye.")
	# 	sys.exit(0)
