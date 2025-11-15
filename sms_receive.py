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
from datetime import datetime, timedelta, timezone
from test_email import send_email

import logging
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('/tmp/sms_receive.log', mode='w')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] L%(lineno)04d %(levelname)-3s: %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.propagate = False  # Prevent propagation to the console

TEXT_SUBJECT_MAX_LENGTH = 64

async def main(recipient):
	start_ts = datetime.now()
	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	modem = await MMModems().get_first()
	if modem is None:
		logger.fatal('no modem found - quitting')
		sys.exit(1)

	startup_msg = f'Listening for SMS; '
	if recipient:
		startup_msg += f'will email: {recipient}'
	else:
		startup_msg += 'no email recipient specified.'
	logger.info(startup_msg)
	print(startup_msg)

	while True:
		async for path, received in modem.messaging.added:
			if received:
				sms = MMSms(path)
				phone_number = await sms.number
				message_text = await sms.text
				# logger.debug(f'{message_text=}')
				message_dt = await sms.timestamp

				# timezone for SMS messages from Mint are in Pacific Time Zone format, e.g. -07
				tz_offset = message_dt[-3:]
				sms_tz_offset = 3
				start_tz_offset = int(tz_offset)+sms_tz_offset
				sms_ts_not_utc = datetime.strptime(message_dt[:-3], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=int(sms_tz_offset))
				start_ts_not_utc = start_ts + timedelta(hours=int(start_tz_offset))
				# print(f'{type(sms_ts_not_utc)=} {sms_ts_not_utc} {type(start_ts_not_utc)=} {start_ts_not_utc}')
				if sms_ts_not_utc < start_ts_not_utc:
					logger.debug(f'Skipping old message received at {message_dt}')
					continue
				try:
					incoming_number_parsed = phonenumbers.parse(phone_number, None)
					if not phonenumbers.is_valid_number(incoming_number_parsed):
						logger.warning(f'Invalid incoming phone number: {phone_number}')
						incoming_number_formatted = phone_number
					else:
						incoming_number_formatted = phonenumbers.format_number(incoming_number_parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
				except Exception as e:
					logger.warning(f'Error parsing incoming phone number {phone_number}: {e}')
					incoming_number_formatted = phone_number

				intro = f'SMS from {phone_number} @ {message_dt}:'
				abbreviated_message = message_text.strip().replace("\\r\\n", "  ")
				subject = f'{intro} {abbreviated_message[:TEXT_SUBJECT_MAX_LENGTH]}'
				body = f'{intro}  {message_text}'
				send_email(recipient, subject, body)
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

	asyncio.run(main(recipient))

	# try:
	# 	asyncio.run(main(recipient))
	# except KeyboardInterrupt:
	# 	logger.info("Exiting application by user request.")
	# except Exception as e:
	# 	logger.error(f"Fatal error in main loop: {e}")
	# finally:
	# 	# Clean up any lingering processes
	# 	sys.exit(0)
