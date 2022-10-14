#!python3

import os
import sys
import json
import paho.mqtt.client as mqtt
import asyncio
import websockets

def configureTTY(tty, baudrate):
  os.system("stty -F " + tty + " igncr")
  os.system("stty -F " + tty + " " + str(baudrate))

def mqttOpen(name, ip, port):
  mqttc = mqtt.Client(name)
  mqttc.connect(ip, port)
  mqttc.loop_start()

  return mqttc

def mqttClose(mqttc):
  mqttc.disconnect()
  mqttc.loop_stop()

def mqttPublish(mqttc, topic, value):
  mqttc.publish(topic , value)

def websocketOpen(name, ip, port):
  uri = "ws://" + ip + ":" + str(port)
  return uri

async def _websocketSend(uri, message):
  async with websockets.connect(uri, ping_timeout=1, close_timeout=4) as websocket:
    await websocket.send(message)

def websocketSend(uri, message):
  #print("websocket: ", message)
  asyncio.get_event_loop().run_until_complete(_websocketSend(uri, message))

class BackendType:
  MQTT      = 0
  WEBSOCKET = 1
  UNDEFINED = 2

class Backend:
  backendType = BackendType.UNDEFINED
  backendhandle = None

  def __init__(self, backendType):
    self.backendType = backendType

backend = []

def main(argv):

  print("Starting")

  configuration = json.load(open('configuration.json'))
  if "zigbee" not in configuration:
    return

  zigbeeConfiguration = configuration["zigbee"]

  if "tty" not in zigbeeConfiguration:
    zigbeeConfiguration["tty"] = "Miflora-Prometheus"

  if "baudrate" not in zigbeeConfiguration:
    zigbeeConfiguration["baudrate"] = 115200

  nodes = []
  if "nodes" in zigbeeConfiguration:
    nodes = zigbeeConfiguration["nodes"]

  print("Configuration:")
  print("TTY:      ", zigbeeConfiguration["tty"])
  print("Baudrate: ", zigbeeConfiguration["baudrate"])

  print("Configuring tty")
  configureTTY(zigbeeConfiguration["tty"], zigbeeConfiguration["baudrate"])

  iNode = 0
  for node in nodes:
    if "name" not in node:
      node["name"] = "Node #" + iNode

    if "mqtt" in node:
      backend.append(Backend(BackendType.MQTT))

      mqttConfiguration = node["mqtt"]

      if "ip" not in mqttConfiguration:
        mqttConfiguration["ip"] = "127.0.0.1"

      if "port" not in mqttConfiguration:
        mqttConfiguration["port"] = 1883

      if "switch-on" not in mqttConfiguration:
        mqttConfiguration["switch-on"] = ""

      if "switch-off" not in mqttConfiguration:
        mqttConfiguration["switch-off"] = ""

      if "brightness" not in mqttConfiguration:
        mqttConfiguration["brightness"] = ""

      if "rgb" not in mqttConfiguration:
        mqttConfiguration["rgb"] = ""

      backend[iNode].backendHandle = mqttOpen(node["name"], mqttConfiguration["ip"], mqttConfiguration["port"])

    elif "websocket" in node:
      backend.append(Backend(BackendType.WEBSOCKET))

      websocketConfiguration = node["websocket"]

      if "ip" not in websocketConfiguration:
        websocketConfiguration["ip"] = "127.0.0.1"

      if "port" not in websocketConfiguration:
        websocketConfiguration["port"] = 8090

      if "switch-on" not in websocketConfiguration:
        websocketConfiguration["switch-on"] = ""

      if "switch-off" not in websocketConfiguration:
        websocketConfiguration["switch-off"] = ""

      if "brightness" not in websocketConfiguration:
        websocketConfiguration["brightness"] = ""

      if "rgb" not in websocketConfiguration:
        websocketConfiguration["rgb"] = ""

      backend[iNode].backendHandle = websocketOpen(node["name"], websocketConfiguration["ip"], websocketConfiguration["port"])

    iNode = iNode + 1

  print("Opening tty")
  tty = open("/dev/ttyAMA0", "r")

  print("Reading tty")
  try:
    while True:
      line = tty.readline()
      line = line.strip()

      #print("Line", len(line), line)

      if len(line) < 5 or line[0] != "#":
        continue

      line = line[1:]
      index = int(line[0])

      cmd = line[2]
      line = line[4:]
      if cmd == "S":
        value = int(line)
        print('''[%u] Switch %1u''' % (index, value))

        if backend[index].backendType == BackendType.MQTT:
          topic = ""

          if value == 1 and "switch-on" in nodes[index]["mqtt"]:
            topic = nodes[index]["mqtt"]["switch-on"]

          if value == 0 and "switch-off" in nodes[index]["mqtt"]:
            topic = nodes[index]["mqtt"]["switch-off"]

          if topic != "":
            mqttPublish(backend[index].backendHandle, topic, value)
          else:
            if value == 0:
              cmd = "L"
              line = "0"

        elif backend[index].backendType == BackendType.WEBSOCKET:
          message = ""

          if value == 1 and "switch-on" in nodes[index]["websocket"]:
            message = nodes[index]["websocket"]["switch-on"]

          if value == 0 and "switch-off" in nodes[index]["websocket"]:
            message = nodes[index]["websocket"]["switch-off"]

          if message != "":
            websocketSend(backend[index].backendHandle, message)
          else:
            if value == 0:
              cmd = "L"
              line = "0"

      if cmd == "L":
        value = int(line)
        percent = int(value * 100 / 255)
        print('''[%u] Brightness %3u (%3u%%)''' % (index, value, percent))

        if backend[index].backendType == BackendType.MQTT:
          if "brightness" in nodes[index]["mqtt"]:
            topic = nodes[index]["mqtt"]["brightness"]
            if topic != "":
              mqttPublish(backend[index].backendHandle, topic, value)

        elif backend[index].backendType == BackendType.WEBSOCKET:
          if "brightness" in nodes[index]["websocket"]:
            message = nodes[index]["websocket"]["brightness"]
            if message != "":
              message = message.replace("<value>", str(value))
              message = message.replace("<percent>", str(percent))
              websocketSend(backend[index].backendHandle, message)

        if value > 0:
          if backend[index].backendType == BackendType.MQTT:
            if "switch-on" in nodes[index]["mqtt"]:
              topic = nodes[index]["mqtt"]["switch-on"]
              if topic != "":
                mqttPublish(backend[index].backendHandle, topic, 1)

          elif backend[index].backendType == BackendType.WEBSOCKET:
            if "switch-on" in nodes[index]["websocket"]:
              message = nodes[index]["websocket"]["switch-on"]
              if message != "":
                websocketSend(backend[index].backendHandle, message)

      if cmd == "C":
        color = line.split(" ")
        r = int(color[0])
        g = int(color[1])
        b = int(color[2])
        print('''[%u] Color %3u %3u %3u''' % (index, r, g, b))
        colorHex = '''#%02X%02X%02X''' % (r, g, b)

        if backend[index].backendType == BackendType.MQTT:
          if "rgb" in nodes[index]["mqtt"]:
            topic = nodes[index]["mqtt"]["rgb"]
            if topic != "":
              mqttPublish(backend[index].backendHandle, topic, colorHex)

        elif backend[index].backendType == BackendType.WEBSOCKET:
          if "rgb" in nodes[index]["websocket"]:
            message = nodes[index]["websocket"]["rgb"]
            if message != "":
              message = message.replace("<value>", colorHex)
              message = message.replace("<red>", str(r))
              message = message.replace("<green>", str(g))
              message = message.replace("<blue>", str(b))
              websocketSend(backend[index].backendHandle, message)

  except KeyboardInterrupt:
    close(tty)

  iNode = 0
  for n in backend:
    if n.backendType == BackendType.MQTT:
      mqttClose(n.backendHandle)
    #elif n.backendType == BackendType.WEBSOCKET:
    #  websocketClose(n.backendHandle)

if __name__ == "__main__":
  main(sys.argv)