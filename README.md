# Overview
The objective is to use a Small Board Computer (SBC) with an attached cellular modem to act as both as (1) a cellular to WiFi router/gateway and (2) a telephone answering machine.  The example use-case is to have the SBC+modem at a business that does not have on-premises staff.  Instead, the answering machine records the message and emails the audio file so that it can be responded to remotely.  This system replaces a VoIP phone service by using a lower-cost cellular plan. Other services, such as a web-server, can be installed on the SBC. Lastly, the software on the SBC is under your control instead of a gateway manufacturer's control.

The software uses the [D-Bus](https://en.wikipedia.org/wiki/D-Bus) to interact with the modem.  D-Bus uses [Polkit](https://en.wikipedia.org/wiki/Polkit) for access control of the modem.  The default configuration of Polkit only allows local users (logged into the desktop) to send/receive calls and SMS.  A Polkit rules file needs to be created to allow the modem to be used by a daemon process.

There are modem specific configuration parameters that need to be applied.  This example uses an Quectel EC25 mounted onto a Mini PCI-E to USB Adapter with SIM Card Slot.  In order to have the modem audio channels work with [ALSA](https://en.wikipedia.org/wiki/Advanced_Linux_Sound_Architecture), PWM mode has to be set using an AT command.  This can only be performed when the [ModemManager](https://modemmanager.org) is launched with the --debug flag. The EC25's PWM mode is not persisted, so it has to be set when the SBC boots. A script is provided to do that, alsong with a systemd user service.

# Installation
- the python scripts use [uv](https://docs.astral.sh/uv/getting-started/installation/) to fetch the required modules.
- clone https://github.com/zhanglongqi/python-sdbus-modemmanager
- mutt is used to send email when an SMS and voice mail is received. [Mutt installation](https://linuxconfig.org/how-to-install-configure-and-use-mutt-with-a-gmail-account-on-linux)
    - a gmail account with an app password can be used.  The app password can be obtained at https://support.google.com/accounts/answer/185833?hl=en
    - Mutt uses a configuration file:  ~/.mutt/muttrc which stores the smtp_url & smtp_password, along with other config info.  Here is an example:
```
set copy = no

set from = "answering.machine@sargenthouse.org"
set realname = "SHM Answering Machine"

set ssl_force_tls = yes

# Smtp settings
set smtp_url = "smtp://foo.bar@gmail.com@smtp.gmail.com:587"
set smtp_pass = "xxxx xxxx xxxx xxxx"
```
   - To test:
    ```echo "email from mutt" | mutt -s "mutt test N" <your_email>```



# Answering Machine
These python scripts use sdbus_block/async.modemmanager to send and receive SMS messages.

