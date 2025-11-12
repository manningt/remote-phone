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

def send_email(recipient, subject, body=None, attachments=[]):
	#echo "body of email" | mutt -s "subject of email" joe@example.com

	if recipient is None or subject is None:
		logging.error('No recipient or subject for send_email')
		return False

	if body:
		cmd = ['echo', body]
		echo_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

	cmd = ['mutt', '-s', subject]
	for attachment in attachments:
		cmd.append('-a')
		cmd.append(attachment)
	cmd.append('--')
	cmd.append(f'{recipient}')

	mutt_process = subprocess.Popen(cmd, stdin=echo_process.stdout, stdout=subprocess.PIPE)
	echo_process.stdout.close()

	output, error = mutt_process.communicate()
	if mutt_process.returncode != 0:
		# logging.error(f'Failed to email text message: {output=}  {error=}')
		return False
	# logging.debug(f'Successfully emailed text message to {recipient}')
	return True


if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description='sends an email to recipient using subject, body, attachments')
	parser.add_argument('-r','--recipient', help='properly formatted email address', required=True)
	parser.add_argument('-s','--subject', help='subject for email', required=True)
	parser.add_argument('-b','--body', help='body of email', required=True)
	parser.add_argument('-a','--attachments', help='comma separated filepaths to include as attachments for the email', required=False)
	args = parser.parse_args()
	# print(f'{args=}')

	if args.attachments is None:
		rc = send_email(args.recipient, args.subject, args.body)
	else:
		attachment_list = args.attachments.split(',')
		rc = send_email(args.recipient, args.subject, args.body, attachment_list)

	if not rc:
		logging.error("send_email failed.")
