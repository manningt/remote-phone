# Overview
These are instructions to configure a linux based SBC to function as a cellular to Wifi gateway. This example used a Raspberry Pi 4 with Debian bookworm and/or trixie.  Two makes of cellular modems were tested: a Quectel EC25 and a Sierra Wireless MC7455.  Both were used with a mini-PCE to USB adapter with a SIM slot.

# Preparation
Flash an OS image for the SBC. I used [Raspberry Pi OS Full](https://www.raspberrypi.com/software/operating-systems/) in order to have a complete set of software utilities.  The WiFi configuration in 'Settings' in the Raspberry Pi Imager were not used to be able to use the built-in Wifi as an Access Point rather than a station.  I used ssh over ethernet to setup the gateway, although a terminal on the Desktop, or the Network Manager GUI could be used.

# network manager setup
## create the cellular connection
A single command is used to enable the cellular modem.  The NetworkManager in the latest Debian releases discovers and configures the modem.
```
sudo nmcli c add type gsm ifname '*' con-name <YourName> apn <Carrier's APN> autoconnect yes
```
Issues particular to your modem or carrier may arise.  For example the Sierra Networks MC7455 needed to have the APN configured using AT commands; this occurred when changing SIM cards on the modem.  To issue AT commands, the ModemManager had to stopped and run in debug mode:
```
sudo systemctl stop ModemManager.service
sudo ModemManager --debug
# in other window:
sudo mmcli -m 0 --command='+CGDCONT?'
#response: '+CGDCONT: 1,"IPV4V6","wholesale","0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0",0,0,0,0'
sudo mmcli -m 0 --command='+CGDCONT=1,"IP","mnet"'
#could try IPV4V6 instead of IP
sudo mmcli -m 0 --command='+CGDCONT?'
#response: '+CGDCONT: 1,"IP","mnet","0.0.0.0",0,0,0,0'
```
## create the WiFi connection as an Access Point
```
sudo nmcli connection add type wifi \
 con-name wifi-ap \
 ifname wlan0 \
 wifi.mode ap \
 wifi.ssid <YourSSID> \
 wifi-sec.key-mgmt wpa-psk \
 wifi-sec.psk <WiFiPassword> \
 ipv4.method shared \
 ipv6.method shared
```
# configure a firewall
Using [UFW](https://linuxopsys.com/set-up-firewall-with-ufw-on-ubuntu) as an example:
```
sudo ufw default allow outgoing
sudo ufw default deny incoming
sudo ufw default allow routed
sudo ufw allow in on tailscale0
sudo ufw allow in on eth0
sudo ufw allow in on wlan0
sudo ufw logging low
sudo ufw enable
sudo ufw status verbose
```
The rules are to have the firewall refuse connections from the cellular network, but accept anything from the ethernet or wireless LAN.  There is on-line documentation about enabling forwarding or having more complicated rules, but the above simple rules seem to work.
# verification/status commands
```
$ nmcli dev   # example output:
DEVICE         TYPE      STATE                   CONNECTION         
eth0           ethernet  connected               Wired connection 1 
cdc-wdm0       gsm       connected               speedt             
lo             loopback  connected (externally)  lo                 
wlan0          wifi      disconnected            --                 
p2p-dev-wlan0  wifi-p2p  disconnected            --                 

$ ip r
default via 33.27.170.174 dev wwan0 proto static metric 700 
10.42.0.0/24 dev wlan0 proto kernel scope link src 10.42.0.1 metric 600 
33.27.170.172/30 dev wwan0 proto kernel scope link src 33.27.170.173 metric 700
```