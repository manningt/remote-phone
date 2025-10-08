#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
# ]
# ///

import asyncio
import sdbus
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '../python-sdbus-modemmanager'))
from sdbus_async.modemmanager import MMModems, MMSms

async def main():
	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	modem = await MMModems().get_first()
	if modem:
		async for path, received in modem.messaging.added:
			if received:
				sms = MMSms(path)
				print(f'From {await sms.number}: {await sms.text}')
	else:
		print('no modem found')


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logging.info("Exiting application by user request.")
	except Exception as e:
		logging.error(f"Fatal error in main loop: {e}")
	finally:
		# Clean up any lingering processes
		sys.exit(0)
