#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "sdbus>=0.14.0",
# ]
# ///

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../python-sdbus-modemmanager'))
# sys.path.append('/home/judy/repos/python-sdbus-modemmanager')
import sdbus
from sdbus_block.modemmanager import MMModems

if __name__ == "__main__":
	if len(sys.argv) != 3:
		print(f'{sys.argv[0]} <number> <text>')
		exit(1)

	sdbus.set_default_bus(sdbus.sd_bus_open_system())
	modem = MMModems().get_first()
	if modem:
		sms = modem.messaging.create_sms(sys.argv[1], sys.argv[2])
		sms.send()
		# delete from sent messages
		modem.messaging.delete_sms(sms)
	else:
		print('no modem found')
