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

import jsonpickle
import json
from pprint import pprint

hangup_timeout = 20  # seconds

def dump_object_properties(obj):
    for attr in dir(obj):
        try:
            print(f"{attr} = {getattr(obj, attr)}")
        except AttributeError:
            print(f"{attr} = ?")

def main(phone_number):
	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	mms = MMModems()
	modem = mms.get_first()
	if modem is None:
		print('no modem found')
		return
	# print(f'Exist calls: {modem.voice.list_calls()}')

	properties = {'number': ('s', phone_number)}
	call_path = modem.voice.create_call(properties)

	# print('--- Call Path  ---')
	# dump_object_properties(call_path)
	# print('\n--- modem.voice  ---')
	# dump_object_properties(modem.voice)
	# serialized = jsonpickle.encode(call_path)
	# print(f'Call_path object:\n{json.dumps(json.loads(serialized), indent=3)}')

	print(f'\n --- Call list after create: {modem.voice.list_calls()}')

	call = MMCall(call_path)
	# serialized = jsonpickle.encode(call)
	# print(f'Call object:\n{json.dumps(json.loads(serialized), indent=3)}')
	# serialized = jsonpickle.encode(call.state)
	# print(f'Call.state object:\n{json.dumps(json.loads(serialized), indent=3)}')

	# print(f'\n--- call:')
	# print(f'{pprint(dir(call))}\n')
	# print(f'\n--- call state:')
	# print(f'{pprint(dir(call.state))}\n')

	print('\n --- Call properties ---')
	print(f'Number: {call.number}   State value: {call.state}, name: {call.state_text}')
	print(f'State reason value: {call.state_reason}, name: {call.state_reason_text}')
	print(f'Direction value: {call.direction}, name: {call.direction_text}')

	print('--- Start call ---')
	start_time = time.monotonic()
	call.start()
	audio_process = None
	while True:
		time.sleep(1)
		current_state = call.state_text
		print(f'Current call state: {current_state}')

		if current_state == 'MM_CALL_STATE_ACTIVE':
			# the following is not working, audio_port and audio_format are always empty
			# 	print(f'Audio port: {call.audio_port}   Audio format: {call.audio_format}')
			if audio_process is None:
				play_cmd = ['aplay', '-D', 'hw:3,0', '/home/judy/BlueShadowsOnTheTrail_8k.wav']
				# play_cmd = ['speaker-test', '-t', 'pink', '-c1', '-r8000', '-D', 'hw:3,0']
				audio_process = subprocess.Popen(play_cmd)

		if current_state == 'MM_CALL_STATE_TERMINATED':
			if audio_process:
				audio_process.terminate()
			break

		# Hangup call.
		if time.monotonic() - start_time >= hangup_timeout:
			print('Stopping call, hangup time.')
			if audio_process:
				audio_process.terminate()
			modem.voice.hangup_all()
			break
	print('--- Stop call ---')

	modem.voice.delete_call(call_path)
	print(f'Call list after delete: {modem.voice.list_calls()}')


if __name__ == '__main__':
	if len(sys.argv) != 2:
		print(f'{sys.argv[0]} <number>')
		exit(1)

	main(sys.argv[1])
