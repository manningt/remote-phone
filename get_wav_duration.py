#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///

import wave
import sys, os

def get_wav_duration(audio_filepath):
	try:
		with wave.open(audio_filepath, 'rb') as wav_file:
			n_frames = wav_file.getnframes()
			framerate = wav_file.getframerate()
			message_duration = n_frames / float(framerate)
			print(f'Wave file {audio_filepath} duration: {message_duration:.1f} seconds (n_frames={n_frames}  framerate={framerate})')
			return message_duration
	except wave.Error as e:
		print(f'Error reading wav file {audio_filepath}: {e}', file=sys.stderr)
		return 0.0

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print(f'No email wav file specified; Usage: {sys.argv[0]}')
	else:
		audio_filepath = sys.argv[1]

	get_wav_duration(audio_filepath)
