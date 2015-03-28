YOZAKURA
========

京都大学メカトロニクス研究室メンバー
SHINOBI遠隔班
夜桜

#Settings
##Contec  
**CONTEC access point (yozakura side)     admin:pass**  
IP Address: 192.168.54.225  
IEEE802.11n (2.4 GHz)  10 channels  
コンパチブルインフラストラクチャ  
ESSID SHINOBI_TELE_YOZAKURA_10ch  
WPA2-PSK(AES)  
1:8  

**CONTEC station (opstn side)     blank**  
IP Address: 192.168.54.220  
IEEE802.11n (2.4GHz)  
コンパチブルインフラストラクチャ  
ESSID SHINOBI_TELE_YOZAKURA_10ch  
WPA2-PSK(AES)  
1:8  

##PC  
**Operator Station PC**  
IP Address: 192.168.54.200  

**Robot PC (Rasberry Pi)**  
IP Address: 192.168.54.210  

##Camera  
**AI-Ball for Arm**  
IP Address: 192.168.54.160  

**AI-Ball for Front body**  
IP Address: 192.168.54.161  

**AI-Ball for Back body**  
IP Address: 192.168.54.162  

**AI-Ball for Overview**  
IP Address: 192.168.54.163  

#Wiring
##Raspberry Pi

<img src="http://www.element14.com/community/servlet/JiveServlet/previewBody/68203-102-6-294412/GPIO.png" alt="RPi B+ Pinout Diagram" width="600x">

| Connection | Pin # |   | Pin # | Connection |
| ---------: | ----: | :-: | :---- | :--------- |
| 3.3V bus | 1 | | 2 |  |
| SDA bus to I2C devices | 3 | | 4 |  |
| SDC bus to I2C devices | 5 | | 6 | |
| Motor RST bus | 7 | | 8 | Left motor FF1 |
|  Ground bus | 9 | | 10 | Left motor FF2 |
| Right motor FF1 | 11 | | 12 | Left motor current sensor AL |
| Right motor FF2 | 13 | | 14 |  |
| Right motor current sensor AL | 15 | | 16 | Battery current sensor AL|
|  | 17 | | 18 |  |
| Right flipper FF1 | 19 | | 20 | |
| Right flipper FF2 | 21 | | 22 | Left flipper FF1 |
| Right flipper current sensor AL | 23 | | 24 | Left flipper FF2 |
| | 25 | | 26 | Left flipper current sensor AL |

##mbed
<img src="http://nora66.com/mbed/pinout.png" alt="mbedLPC1768 Pinout Diagram" width="400x" align="right">
* p19: Left flipper position ADC
* p20: Right flipper position ADC
* p23: Right flipper PWM
* p24: Left flipper PWM
* p25: Right motor PWM
* p26: Left motor PWM
* p27: Left motor DIR
* p28: Right motor DIR
* p29: Left flipper DIR
* p30: Right flipper DIR