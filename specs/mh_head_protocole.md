# WIP

# Moving head light protocol

## Ports

UDP: 1234
HTTP: 81

## HTTP Requests

GET /infos
returns:
Http 200
{
    wifi_ssid: str, # Wifi SSID
    ip: str, # 192.168.XXX.XXX
    firmware_version: str, # 0.0.1 etc
    platform: str, # ESP32, Arduino Uno R3 etc
}

POST /resetPacketIDs
returns:
Http 200
{
    success: bool, # Should always be true
}

## UDP Packets

UDP ping
send: ping
receive: pong

UDP Packet:
Packet_ID;args (in format key=value separated by ;)
If the device receives an udp packet with an ID less than any previous packet receives, it will ignore it.

Arguments:
Servos:
- bS : Base Servo Angle
- tS : Top Servo Angle
Base RGB:
- r : LED Red Value (0-255)
- g : LED Green Value (0-255)
- b : LED Blue Value (0-255)

Flicker:
- fl : Flicker Duration (ms)

Fade:
- fa : Fade Duration (ms)
- fr : From Red Value (0-255)
- fg : From Green Value (0-255)
- fb : From Blue Value (0-255)
