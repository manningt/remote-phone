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

def email_message_notification(phone_number, audio_filepath, message_duration, recipient):
	#echo "body of email" | mutt -s "subject of email" joe@example.com

	transcription = "Transcription TBD"
	body = f'From {phone_number}:  {transcription}'
	cmd = ['echo', body]
	echo_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

	try:
		subject = f'Message from {phone_number} - Duration: {message_duration:.1f} seconds'
	except:
		subject = f'Message from {phone_number}'
	cmd = ['mutt', '-s', subject, '-a', audio_filepath, '--', recipient]
	mutt_process = subprocess.Popen(cmd, stdin=echo_process.stdout, stdout=subprocess.PIPE)
	echo_process.stdout.close()

	output, error = mutt_process.communicate()
	if mutt_process.returncode != 0:
		logging.error(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
		# logging.error(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
	# else:
	# 	logging.debug(f'Successfully emailed text message to {recipient}')


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
						if wav_file_index == 1 and audio_process[RECORD] is None:
							# Start recording after the first message is played
							now = datetime.datetime.now()
							message_filename = f"message-{now.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
							wav_recording_filepath = os.path.join('/tmp', message_filename)
							logging.debug(f'Starting recording to {wav_recording_filepath}')
							cmd = ['arecord', '-q', '-f', 'S16_LE', '-D', 'hw:3,0', wav_recording_filepath]
							try:
								audio_process[RECORD] = subprocess.Popen(cmd)
							except Exception as e:
								logging.error(f'Failed to start arecord process: {e}')
					else:
						if audio_process[PLAY].poll() is not None:
							logging.debug(f'Finished aplay of {wav_file_list[wav_file_index]}')
							wav_file_index += 1
							audio_process[PLAY] = None

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
			mp3_ok = False
			logging.debug(f'Processing {wav_recording_filepath} for email notification.')
			if os.path.exists(wav_recording_filepath):
				mp3_recording_filepath = os.path.join(home_path, messages_path, message_filename.replace('.wav', '.mp3'))
				cmd = ['ffmpeg', '-hide_banner', '-i', wav_recording_filepath, mp3_recording_filepath]
				try:
					# FFmpeg outputs information to stderr for status messages, warnings, and errors, 
					# while stdout is reserved for the actual data being processed
					ffmpeg_process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
					_, error = ffmpeg_process.communicate()
					if ffmpeg_process.returncode != 0:
						logging.error(f'Failed generate mp3 with ffmpeg: error={error.decode()}')
					else:
						mp3_ok = True
				except Exception as e:
					logging.error(f'Failed to start ffmpeg_process {e}')
			else:
				logging.error(f'WAV recording file not found: {wav_recording_filepath}')
				
			if mp3_ok:
				message_duration = 0.0
				# logging.debug(f'Successfully created mp3 file: {mp3_recording_filepath}')
				for line in error.decode().splitlines():
					# logging.debug(line)
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
				email_message_notification(call.number, mp3_recording_filepath, message_duration, recipient)


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
