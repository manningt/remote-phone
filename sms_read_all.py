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
from sdbus_block.modemmanager import MMModems, MMSms
from datetime import datetime
from enum import Enum
import argparse

#https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Sms.html#gdbus-property-org-freedesktop-ModemManager1-Sms.State
class MMSmsState(Enum):
    MM_SMS_STATE_UNKNOWN   = 0
    MM_SMS_STATE_STORED    = 1
    MM_SMS_STATE_RECEIVING = 2
    MM_SMS_STATE_RECEIVED  = 3
    MM_SMS_STATE_SENDING   = 4
    MM_SMS_STATE_SENT      = 5

def populate_sms_list():
   sdbus.set_default_bus(sdbus.sd_bus_open_system())
   modem = MMModems().get_first()
   sms_list = []
   if modem:
      try:
         sms_list = modem.messaging.list()
      except Exception as e:
         print(f'Error retrieving SMS list: {e} for modem {modem.path}')
         modem = None
   else:
      print('No modem found')
   return modem, sms_list


def print_received_sms(sms_list=[], max_count=100):
   current_time = datetime.now()
   counter = 0
   for sms_path in sms_list:
      sms = MMSms(sms_path)
      if sms.state != MMSmsState.MM_SMS_STATE_RECEIVED.value:
         continue
      sms_id = sms_path.split('/')[-1]
      # print(f'--- SMS {sms_path} ---')
      # remove the last 3characters from the timestamp to parse it correctly, as it contains timezone info, e.g. -07
      sms_dt = datetime.strptime(sms.timestamp[:-3], "%Y-%m-%dT%H:%M:%S")
      hours_ago = (current_time - sms_dt).total_seconds() / 3600
      state_name = MMSmsState(sms.state).name.split('MM_SMS_STATE_')[-1].capitalize()
      print(f'SMS {sms_id}:  {sms.timestamp} {sms.number} {state_name} ({hours_ago:.0f} hours ago)')
      print(f'\tText: {sms.text}\n')
      # print(f'{sms.DeliveryReportRequest=}')
      # print(f'{sms.service_category=}')
      counter += 1
      if counter >= max_count:
         break

def delete_received_sms(modem, sms_list, from_number=None):
   if from_number is None:
      return
   print(f'Deleting messages from number: {from_number}')
   for sms_path in sms_list:
      sms = MMSms(sms_path)
      # print(f'{type(sms.number)=} {type(from_number)=}') 
      if from_number != '*' and from_number not in sms.number: # or sms.state != MMSmsState.MM_SMS_STATE_RECEIVED.value:
         continue
      sms_id = sms_path.split('/')[-1]
      sms_dt = datetime.strptime(sms.timestamp[:-3], "%Y-%m-%dT%H:%M:%S")
      state_name = MMSmsState(sms.state).name.split('MM_SMS_STATE_')[-1].capitalize()
      y_n = input(f'Delete {sms_id}: {sms_dt} {sms.number} {state_name} {sms.text[:30]}... ? (y/n/q) ')
      if y_n.lower() == 'q':
         return
      if y_n.lower() == 'y':
         print(f'Deleting SMS {sms_id} from {from_number}')
         try:
            modem.messaging.delete_sms(sms)
         except Exception as e:
            print(f'Error deleting SMS {sms_id}: {e}')

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description='list, read, delete SMS messages on ModemManager modems')
   parser.add_argument('-d','--delete', help='Delete messages from this number', required=False)
   args = vars(parser.parse_args())
   # print(f'{args=}')

   modem, sms_list = populate_sms_list()
   if modem and len(sms_list) > 0:
      if 'delete' in args and args['delete']:
         delete_received_sms(modem, sms_list, from_number=args['delete'])
      else:
         print_received_sms(sms_list)


'''
State                  readable   u
PduType                readable   u
Number                 readable   s
Text                   readable   s
Data                   readable   ay
SMSC                   readable   s
Validity               readable   (uv)
Class                  readable   i
TeleserviceId          readable   u
ServiceCategory        readable   u
DeliveryReportRequest  readable   b
MessageReference       readable   u
Timestamp              readable   s
DischargeTimestamp     readable   s
DeliveryState          readable   u
Storage                readable   u
'''