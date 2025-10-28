#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///

import logging
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
import subprocess
import sys, os

def email_sms(number, text, recipient):
	#echo "body of email" | mutt -s "subject of email" joe@example.com

	body = f'From {number}:  {text}'
	cmd = ['echo', body]
	echo_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

	subject = f'SMS from {number}'
	cmd = ['mutt', '-s', subject, f'{recipient}']
	mutt_process = subprocess.Popen(cmd, stdin=echo_process.stdout, stdout=subprocess.PIPE)
	echo_process.stdout.close()

	output, error = mutt_process.communicate()
	if mutt_process.returncode != 0:
		print(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
		# logging.error(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
	else:
		print(f'Successfully emailed text message to {recipient}')


if __name__ == "__main__":
	recipient = None
	if len(sys.argv) < 2:
		print(f'No email recipient specified; Usage: {sys.argv[0]} <email_recipient>\n\tNot sending emails.')
	else:
		recipient = sys.argv[1]

	number = "1234567890"
	text = "This is a test message."
	email_sms(number, text, recipient)
