#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
# ]
# ///

import wave
import sys

def get_wav_duration(wav_filename):
	try:
		with wave.open(wav_filename, 'r') as wav_file:
			duration = wav_file.getnframes() / wav_file.getframerate()
			return duration
	except Exception as e:
		print(f"Error reading {wav_filename}: {e}")
		return None

def get_filename_sys_argv():
	if len(sys.argv) < 2:
		print("Please provide a filename as a command-line argument")
		sys.exit(1)
	else:
		return sys.argv[1]


if __name__ == "__main__":
	wav_filename = get_filename_sys_argv()
	duration = get_wav_duration(wav_filename)
	if duration is not None:
		print(f'{wav_filename} is {duration:.1f} seconds long')
	else:
		print(f'Could not determine duration of {wav_filename}')
