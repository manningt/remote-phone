#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
#   "phonenumbers"
# ]
# ///

import asyncio
import sdbus
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../python-sdbus-modemmanager'))
from sdbus_async.modemmanager import MMModems, MMSms
import subprocess
import phonenumbers

import logging
LOG_FORMAT = ('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, filename='/tmp/sms_receive.log', filemode="w")
TEXT_SUBJECT_MAX_LENGTH = 64

def email_message_notification(phone_number, message, recipient):
	#echo "body of email" | mutt -s "subject of email" joe@example.com

	incoming_number_parsed = phonenumbers.parse(phone_number, None)
	if not phonenumbers.is_valid_number(incoming_number_parsed):
		logging.warning(f'Invalid incoming phone number: {phone_number}')
		incoming_number_formatted = phone_number
	else:
		incoming_number_formatted = phonenumbers.format_number(incoming_number_parsed, phonenumbers.PhoneNumberFormat.NATIONAL)

	body = f'From {incoming_number_formatted}:  {message}'
	cmd = ['echo', body]
	echo_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

	subject = f'Message from {incoming_number_formatted}  {message[:TEXT_SUBJECT_MAX_LENGTH]}'
	cmd = ['mutt', '-s', subject, recipient]
	mutt_process = subprocess.Popen(cmd, stdin=echo_process.stdout, stdout=subprocess.PIPE)
	echo_process.stdout.close()

	output, error = mutt_process.communicate()
	if mutt_process.returncode != 0:
		logging.error(f'Failed to email text message: output={output.decode()}  error={error.decode()}')
	# else:
	# 	logging.debug(f'Successfully emailed text message to {recipient}')


async def main(recipient):
	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	modem = await MMModems().get_first()
	if modem:
		logging.info('Listening for incoming SMS messages...')
		while True:
			async for path, received in modem.messaging.added:
				if received:
					sms = MMSms(path)
					phone_number = await sms.number
					message_text = await sms.text
					logging.info(f'From {phone_number}: {message_text[:TEXT_SUBJECT_MAX_LENGTH]}')
					email_message_notification(phone_number, message_text, recipient)
	else:
		logging.fatal('no modem found')


if __name__ == "__main__":
	recipient = None
	if 'EMAIL_ADDR' in os.environ:
		recipient = os.environ['EMAIL_ADDR']
		logging.debug(f'Using email recipient from environment: {recipient}')
	elif len(sys.argv) < 2:
		logging.warning(f'No email recipient specified; Usage: {sys.argv[0]} <email_recipient> -- Not sending emails.')
	else:
		recipient = sys.argv[1]

	logging.debug(f'Starting sms_receive.py  emailing: {recipient}')
	try:
		asyncio.run(main(recipient))
	except KeyboardInterrupt:
		logging.info("Exiting application by user request.")
	except Exception as e:
		logging.error(f"Fatal error in main loop: {e}")
	finally:
		# Clean up any lingering processes
		sys.exit(0)
