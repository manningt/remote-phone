#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
# ]
# ///

import logging
# LOG_FORMAT = "%(asctime)s %(funcName) %(lineno)d %(levelname)s: %(message)s"
# the -6 and -04d do left alignment in the log output
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename='/tmp/call_receive.log', filemode="w")
import subprocess
import sys, os
import tempfile

def email_sms(number, text, recipient):
	#echo "body of email" | mutt -s "subject of email" tom@manningetal.com

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
