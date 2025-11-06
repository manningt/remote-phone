# Overview
The objective is to use a Small Board Computer (SBC) with an attached cellular modem to act as both as (1) a cellular to WiFi router/gateway and (2) a telephone answering machine.  The example use-case is to have the SBC+modem at a business that does not have on-premises staff.  Instead, the answering machine records the message and emails the audio file so that it can be responded to remotely.  This system replaces a VoIP phone service by using a lower-cost cellular plan. Other services, such as a web-server, can be installed on the SBC. Lastly, the software on the SBC is under your control instead of a gateway manufacturer's control.

The software uses the [D-Bus](https://en.wikipedia.org/wiki/D-Bus) to interact with the modem.  D-Bus uses [Polkit](https://en.wikipedia.org/wiki/Polkit) for access control of the modem.  The default configuration of Polkit only allows local users (logged into the desktop) to send/receive calls and SMS.  A Polkit rules file needs to be created to allow the modem to be used by a daemon process.

There are modem specific configuration parameters that need to be applied.  This example uses an Quectel EC25 mounted onto a Mini PCI-E to USB Adapter with SIM Card Slot.  In order to have the modem audio channels work with [ALSA](https://en.wikipedia.org/wiki/Advanced_Linux_Sound_Architecture), PWM mode has to be set using an AT command.  This can only be performed when the [ModemManager](https://modemmanager.org) is launched with the --debug flag. The EC25's PWM mode is not persisted, so it has to be set when the SBC boots. The script ```set_qpwmc_mode.py``` is provided to do that, alsong with a systemd user service.

# Installation
## Python
- the python scripts use [uv](https://docs.astral.sh/uv/getting-started/installation/) to fetch the required modules.
- clone https://github.com/zhanglongqi/python-sdbus-modemmanager

## Polkit configuration
To enable using the cellular phone in a program, a rule has to be added:
```
sudo vi /etc/polkit-1/rules.d/126-modemmanager-voice-allow.rules
```
The following 2 rules should be put in the file to allow a user to perform voice and sms without authetication:
```
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.ModemManager1.Voice" &&
        subject.user == "YourUserName") {
        return polkit.Result.YES;
    }
});

polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.ModemManager1.Messaging" && subject.user == "YourUserName") {
        return polkit.Result.YES;
    }
});
```
and then restart the polkit service: ```sudo systemctl restart polkit.service```

## EC25 modem setup
USB Audio Class (UAC) mode needs to be enabled, as per the following commands.  _Before_ doing the commands, type ```ls /dev/snd/``` to see the sound devices before enabling UAC mode.  When ModemManager is run in debug mode, it writes _a lot_ of log messages to the terminal.
```
sudo systemctl stop ModemManager
sudo /usr/sbin/ModemManager --debug
```
In different terminal session:
```
sudo mmcli -m 0 --command='+QCFG="USBCFG",0x2C7C,0x0125,1,1,1,1,1,0,1'
sudo mmcli -m 0 --command='+QCFG="USBCFG"'
sudo systemctl restart ModemManager
```
In the terminal session where ModemManager is running in debug mode then type Control-C.
Then restart the ModemManager: ```sudo systemctl stop ModemManager```

After doing the commands, type ```ls /dev/snd/``` again.  Addition devices, e.g. controlC3 pcmC3D0c pcmC3D0p should now be present.

## Email
- mutt is used to send email when an SMS and voice mail is received. Here is how to do [Mutt installation](https://linuxconfig.org/how-to-install-configure-and-use-mutt-with-a-gmail-account-on-linux)
    - a gmail account with an app password can be used.  The app password can be obtained at https://support.google.com/accounts/answer/185833?hl=en
    - Mutt uses a configuration file:  ~/.mutt/muttrc which stores the smtp_url & smtp_password, along with other config info.  Here is an example:
```
set copy = no

set from = "email.id@domain.org"
set realname = "My Answering Machine"

set ssl_force_tls = yes

# Smtp settings
set smtp_url = "smtp://foo.bar@gmail.com@smtp.gmail.com:587"
set smtp_pass = "xxxx xxxx xxxx xxxx"
```
To test:
    ```echo "email from mutt" | mutt -s "mutt test N" <your_email>```

## systemd service files
The EMAIL_ADDR variable used by the python scripts under systemd control is configured using [environment.d](https://www.freedesktop.org/software/systemd/man/latest/environment.d.html).  The following shell commands enable sms/voice_call_receive.py scripts to run on startup:
```
mkdir .config/systemd/user
cp ~/repos/remote-phone/*service .config/systemd/user
mkdir .config/environment.d
echo "EMAIL_ADDR=email.address@your.com" >  .config/environment.d/10-remote-phone.conf
systemctl --user enable set_qpwmc.service
systemctl --user enable voice_call_receive.service
systemctl --user enable sms_receive.service
```
