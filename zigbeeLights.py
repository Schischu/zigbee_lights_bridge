import os
import paho.mqtt.client as mqtt

#192.168.178.200
mqttc = mqtt.Client("Zigbee-Mqtt")
mqttc.connect("192.168.178.200", 1883)
mqttc.loop_start()

print "Configuring tty"
os.system("stty -F /dev/ttyAMA0 igncr")
os.system("stty -F /dev/ttyAMA0 115200")

tty = open("/dev/ttyAMA0", "r")

print "Reading tty"
try:
  while True:
    line = tty.readline()
    line = line.strip()

    #print "Line", len(line), line

    if len(line) < 5 or line[0] != "#":
      continue

    line = line[1:]
    index = int(line[0])

    cmd = line[2]
    line = line[4:]
    if cmd == "S":
      value = int(line)
      print '''[%u] Switch %1u''' % (index, value)
      #if index == 1:
      #  if value == 0:
      #    mqttc.publish("ESPURNA-421B6E/channel/3/set" , 0)
      #else:
      #  mqttc.publish("ESPURNA-421B6E/0/set" , value)
      if value == 0:
        cmd = "L"
        line = "0"

    if cmd == "L":
      value = int(line)
      print '''[%u] Brightness %3u''' % (index, value)

      if index == 0:
        mqttc.publish("ESPURNA-421B6E/brightness/set" , value)
      else:
        mqttc.publish("ESPURNA-421B6E/channel/3/set" , value)

      if value > 0:
        mqttc.publish("ESPURNA-421B6E/0/set" , 1)

    if cmd == "C":
      color = line.split(" ")
      r = int(color[0])
      g = int(color[1])
      b = int(color[2])
      print '''[%u] Color %3u %3u %3u''' % (index, r, g, b)
      colorHex = '''#%02X%02X%02X''' % (r, g, b)

      if index != 1:
        mqttc.publish("ESPURNA-421B6E/rgb/set" , colorHex)

except KeyboardInterrupt:
  close(tty)
  mqttc.disconnect()
  mqttc.loop_stop()
