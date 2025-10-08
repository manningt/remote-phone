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
from datetime import datetime
import sdbus
from sdbus_block.modemmanager import MMModems, MMCall

if __name__ == "__main__":
   sdbus.set_default_bus(sdbus.sd_bus_open_system())
   modem = MMModems().get_first()
   if modem:
      current_time = datetime.now()
      call_list = modem.voice.list_calls()
      if len(call_list) == 0:
         print(f'No calls at this time: {current_time}')
      else:
         for call_path in call_list:
            print(f'--- Call: {call_path} ---')
            call = MMCall(call_path)
            print(f'State value: {call.state}, name: {call.state_text}')
            print(f'State reason value: {call.state_reason}, name: {call.state_reason_text}')
            print(f'Direction value: {call.direction}, name: {call.direction_text}')
            # print(f'Multiparty: {call.multiparty}')
            print(f'Number: {call.number}')
            print(f'Audio port: {call.audio_port}')
            print(f'Audio format: {call.audio_format}\n') 

   else:
      print('no modem found')
