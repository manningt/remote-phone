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

#https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Sms.html#gdbus-property-org-freedesktop-ModemManager1-Sms.State
class MMSmsState(object):
    MM_SMS_STATE_UNKNOWN   = 0
    MM_SMS_STATE_STORED    = 1
    MM_SMS_STATE_RECEIVING = 2
    MM_SMS_STATE_RECEIVED  = 3
    MM_SMS_STATE_SENDING   = 4
    MM_SMS_STATE_SENT      = 5


if __name__ == "__main__":
   sdbus.set_default_bus(sdbus.sd_bus_open_system())
   modem = MMModems().get_first()
   if modem:
      current_time = datetime.now()
      sms_list = modem.messaging.list()
      for sms_path in sms_list:
         sms = MMSms(sms_path)
         if sms.state != MMSmsState.MM_SMS_STATE_RECEIVED:
            continue
         sms_number = sms_path.split('/')[-1]
         # print(f'--- SMS {sms_path} ---')
         # remove the last 3characters from the timestamp to parse it correctly, as it contains timezone info, e.g. -07
         sms_dt = datetime.strptime(sms.timestamp[:-3], "%Y-%m-%dT%H:%M:%S")
         hours_ago = (current_time - sms_dt).total_seconds() / 3600
         print(f'SMS {sms_number}:  {sms.timestamp} {sms.number} ({hours_ago:.0f} hours ago)')
         print(f'\tText: {sms.text}\n')
         # print(f'{sms.DeliveryReportRequest=}')
         # print(f'{sms.service_category=}')
   else:
      print('no modem found')

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