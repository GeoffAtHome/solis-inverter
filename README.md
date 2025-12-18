# solis-inverter
Home assistant custom component for **Solis RAI-3K-48ES-5G Inverter**

I have modified the SolarMon to work directly with a Solis RAI-3K-48ES-5G. 

To be clear, the Solis RAI-3K-48ES-5G has onboard Wifi - it DOES NOT need a WiFi stick. What is required is that the inverter is visible on your LAN.

I ran the Solis TechView apk in an Android emulator and monitored the network traffic with Wireshark.

Basically reads/writes registers in a similar way to modbus. I don’t really know modbus but the registers appear to be the same as in this [document](https://www.scss.tcd.ie/Brian.Coghlan/Elios4you/RS485_MODBUS-Hybrid-BACoghlan-201811228-1854.pdf).


## Solis TechView_1.1.0_Apkpure.apk
The APK will ONLY WORK is directly connect to the WiFi access point (SSID: AP-xxxxxx, Password: solis100). The default password for the direct connect is admin, admin.

On the web interface setup up the Network Setting->Network Connection 2 Setting to:
**Protocol:** TCP Server
**Local Port:** 8000 ← this is what is used by the integration.

### Passwords for APK:
**advanced user:** solis123456
**installer:** solis123

## Installation
Both the `solis` and `solis_direct` folders need to be placed in Home Assistant `custom_components` folder.

## Configuration
Once added, restart Home Assistant and add the "solis" as a new integration.

## YAML scripts
They are a few scripts for doing stuff on your inverter:
* `inverter set time charging parameters.yaml` - sets the inverter time charging and discharging start and end times
* `inverter set time.yaml` - sets the inverter time from Home Assistant time
* `inverter timed charging on.yaml` - turns on timed changing on
* `inverter timed charging off.yaml` - turns off timed changing off

These have been tested on the invert I have. Use at your own risk.

# Improvements
Happy to take feedback and PRs.

Python is not my language of choice and this leaves a lot to be desired. It works but no tests have been written. My testing has basically seeing the packets sent in WireShark and ensuring I could create the some information via Home Assistant.

# Credits
Thanks to [SolarMon](https://github.com/StephanJoubert/home_assistant_solarman). My code is a rip-off from this code base and modified to work with a **Solis RAI-3K-48ES-5G** . Why **SolarMon** this will not work with the inverter I have beats me which is why I wrote this code.