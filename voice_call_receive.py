#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
#   "phonenumbers"
# ]
# ///

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../python-sdbus-modemmanager'))
from sdbus_block.modemmanager import MMCall, MMModems
import sdbus
import time
import datetime
import subprocess
import phonenumbers
from test_email import send_email

import logging
# reference: https://docs.python.org/3/howto/logging-cookbook.html#logging-cookbook
# the following is to avoid logging to the journal; only log to a file:
logger = logging.getLogger('my_logger')
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
# Create a file handler
file_handler = logging.FileHandler('/tmp/call_receive.log', mode='w')
file_handler.setLevel(logging.INFO)
# Create a formatter and set it for the handler
# the -6 and -04d do left alignment in the log output
formatter = logging.Formatter('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
file_handler.setFormatter(formatter)
# Add the handler to the logger
logger.addHandler(file_handler)
logger.propagate = False  # Prevent propagation to the console

home_path = os.path.expanduser("~")
messages_path = os.path.join(home_path, 'messages')
wav_file_list = [os.path.join(home_path, 'current-message.wav'), os.path.join(home_path, 'beep.wav')]


def main(recipient):
	HANGUP_TIMEOUT = 70  # seconds
	PLAY = 0
	RECORD = 1

	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	mms = MMModems()
	modem = mms.get_first()
	if modem is None:
		logger.fatal('no modem found - quiting')
		sys.exit(1)

	# clear existing calls; may not be necessary
	call_list = modem.voice.list_calls()
	if len(call_list) > 0:
		logger.debug(f'Clearing existing calls: {call_list}')
		for call_path in call_list:
			modem.voice.delete_call(call_path)

	call_list = modem.voice.list_calls()
	previous_call_list_length = len(call_list)

	my_phone_number = modem.own_numbers[0]
	if my_phone_number[0] != '+':
		my_phone_number = '+' + my_phone_number		
	my_number_parsed = phonenumbers.parse(my_phone_number, None)
	if not phonenumbers.is_valid_number(my_number_parsed):
		logger.warning(f'Invalid phone number: {my_phone_number}')
		my_number_formatted = my_phone_number
	else:
		my_number_formatted = phonenumbers.format_number(my_number_parsed, phonenumbers.PhoneNumberFormat.NATIONAL)

	startup_msg = f'{modem.model} - listening for calls coming to {my_number_formatted}; '# on {modem}; '
	if recipient:
		startup_msg += f'will email: {recipient}'
	else:
		startup_msg += 'no email recipient specified.'
	logger.info(startup_msg)
	print(startup_msg)

	while True: #loop forever to receive calls
		while True: # wait for an incoming call
			time.sleep(1)
			try:
				call_list = modem.voice.list_calls()
				if len(call_list) > previous_call_list_length:
					previous_call_list_length = len(call_list)
					# logger.debug(f'New call detected: {call_list}')
					break
			except Exception as e:
				logger.fatal(f'Failed to poll modem for call list: {e}')
				sys.exit(1)
		
		logger.debug(f'Handling call: {call_list[0]}')
		call = MMCall(call_list[0]) # get the most recent call; new calls are added to the beginning of the list
		logger.info(f'Incoming call from number: {call.number}, direction: {call.direction}, state: {call.state}')

		start_time = time.monotonic()
		wav_file_index = 0
		previous_call_state = None
		audio_process = [None, None]  # to hold arecord and aplay subprocesses
		wav_recording_filepath = None
		mp3_ok = False

		while True: # monitor call state
			time.sleep(1)
			current_state = call.state_text
			if current_state != previous_call_state:
				logger.info(f'New call state: {current_state}')
			# else:
			# 	logger.debug('. ', end='')

			if current_state == 'MM_CALL_STATE_RINGING_IN':
				call.accept()

			if current_state == 'MM_CALL_STATE_ACTIVE':
				if wav_file_index < len(wav_file_list):
					if audio_process[PLAY] is None:
						play_cmd = ['aplay', '-q', '-D', 'hw:3,0', wav_file_list[wav_file_index]]
						# logger.debug(f'Starting audio playback of {wav_file_list[wav_file_index]}.')
						audio_process[PLAY] = subprocess.Popen(play_cmd)
						if wav_file_index == 1 and audio_process[RECORD] is None:
							# Start recording after the first message is played
							now = datetime.datetime.now()
							message_filename = f"message-{now.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
							wav_recording_filepath = os.path.join('/tmp', message_filename)
							logger.debug(f'Starting recording to {wav_recording_filepath}')
							cmd = ['arecord', '-q', '-f', 'S16_LE', '-D', 'hw:3,0', wav_recording_filepath]
							try:
								audio_process[RECORD] = subprocess.Popen(cmd)
							except Exception as e:
								logger.error(f'Failed to start arecord process: {e}')
					else:
						if audio_process[PLAY].poll() is not None:
							logger.debug(f'Finished aplay of {wav_file_list[wav_file_index]}')
							wav_file_index += 1
							audio_process[PLAY] = None

			if current_state == 'MM_CALL_STATE_TERMINATED':
				break

			if time.monotonic() - start_time >= HANGUP_TIMEOUT:
				logger.info('Stopping call, hangup due to time_out.')
				modem.voice.hangup_all()
				break

			previous_call_state = current_state

		logger.debug('Stopping aplay and arecord processes.')
		if audio_process[PLAY]:
			audio_process[PLAY].terminate()
		if audio_process[RECORD]:
			audio_process[RECORD].terminate()
		if not wav_recording_filepath:
			logger.info("No voice message left")
		if recipient and wav_recording_filepath:
			logger.debug(f'Processing {wav_recording_filepath} for email notification.')
			if os.path.exists(wav_recording_filepath):
				mp3_recording_filepath = os.path.join(home_path, messages_path, message_filename.replace('.wav', '.mp3'))
				cmd = ['ffmpeg', '-hide_banner', '-i', wav_recording_filepath, mp3_recording_filepath]
				try:
					# FFmpeg outputs information to stderr for status messages, warnings, and errors, 
					# while stdout is reserved for the actual data being processed
					ffmpeg_process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
					_, error = ffmpeg_process.communicate()
					if ffmpeg_process.returncode != 0:
						logger.error(f'Failed to generate mp3 with ffmpeg: {error=}')
					else:
						mp3_ok = True
				except Exception as e:
					logger.error(f'Failed to start ffmpeg_process {e}')
			else:
				logger.error(f'WAV recording file not found: {wav_recording_filepath}')
				
			if mp3_ok:
				message_duration = 0.0
				# logger.debug(f'Successfully created mp3 file: {mp3_recording_filepath}')
				for line in error.decode().splitlines():
					# logger.debug(line)
					if 'time=' in line:
						size = line.split('size=')[1].split()[0]
						if size.lower() == '0kb':
							pass
						else:
							timestamp = line.split('time=')[1].split()[0]
							timestamp_list = timestamp.split(':')
							hours = int(timestamp_list[0])
							minutes = int(timestamp_list[1])
							seconds = float(timestamp_list[2])
							message_duration = (minutes * 60) + seconds
				# email_message_notification(call.number, mp3_recording_filepath, message_duration, recipient)
				
				try:
					incoming_number_parsed = phonenumbers.parse(call.number, None)
					if not phonenumbers.is_valid_number(incoming_number_parsed):
						logger.warning(f'Invalid incoming phone number: {call.number}')
						incoming_number_formatted = call.number
					else:
						incoming_number_formatted = phonenumbers.format_number(incoming_number_parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
				except Exception as e:
					logger.warning(f'Error parsing incoming phone number {call.number}: {e}')
					incoming_number_formatted = call.number

				try:
					subject = f'Voice mail from {incoming_number_formatted}  ({message_duration:.0f} seconds)'
				except:
					subject = f'Voice mail from {incoming_number_formatted}'
				body = subject # in the future add a transcription
				send_email(recipient, subject, body, [mp3_recording_filepath])
				logger.info(f'sent email: {recipient=} {subject=}')

if __name__ == "__main__":
	recipient = None
	if 'EMAIL_ADDR' in os.environ:
		recipient = os.environ['EMAIL_ADDR']
		logger.debug(f'Using email recipient from environment: {recipient}')
	elif len(sys.argv) < 2:
		logger.warning(f'No email recipient specified; Usage: {sys.argv[0]} <email_recipient> -- Not sending emails.')
	else:
		recipient = sys.argv[1]

	main(recipient)
	# try:
	# 	main(recipient)
	# except KeyboardInterrupt:
	# 	logger.info("Exiting application by user request.")
	# except Exception as e:
	# 	logger.error(f"Fatal error in main loop: {e}")
	# finally:
	# 	# 5. Clean up any lingering processes
	# 	logger.info("Cleanup complete. Goodbye.")
	# 	sys.exit(0)
