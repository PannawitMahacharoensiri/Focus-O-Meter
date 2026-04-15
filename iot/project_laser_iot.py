from machine import Pin, ADC, I2C, reset, Encoder, Counter
import time, math, network, ujson
from umqtt.robust import MQTTClient
from config import WIFI_SSID, WIFI_PASS, MQTT_BROKER, MQTT_USER, MQTT_PASS

# =========================
# Hardware setup
# =========================
led_wifi = Pin(2, Pin.OUT)
led_iot = Pin(12, Pin.OUT)
sw1, sw2 = Pin(16, Pin.IN, Pin.PULL_UP), Pin(14, Pin.IN, Pin.PULL_UP)
press_time = 0
LONG_PRESS_MS = 500
DEBOUNCE_MS = 50


# Temp sensor
i2c1 = I2C(1, sda=Pin(4), scl=Pin(5))
t_addr = 77
i2c1.writeto(t_addr, bytearray([0x04, 0b01100000]))  # 14-bit resolution
t_step = 0.03125

# Matrix display
i2c0 = I2C(0, scl=Pin(22), sda=Pin(21))
d_addr = 112
i2c0.writeto(d_addr, b'\x21')   # oscillator on
i2c0.writeto(d_addr, b'\x81')   # display on
i2c0.writeto(d_addr, b'\xEF')   # brightness max

# Light sensor
ldr = ADC(Pin(36))
pin0 = Pin(32, Pin.IN)
pin1 = Pin(33, Pin.IN)
encoder = Encoder(0, pin1, pin0)
ldr_vref = 3.32
ldr_resis = 33000

wlan = network.WLAN(network.STA_IF)
mqtt = None

# =========================
# Helper functions
# =========================
def restart_esp(reason="Unknown error", delay=5):
    print("Restarting ESP32:", reason)
    led_wifi.value(1)
    led_iot.value(1)
    time.sleep(delay)
    reset()

def connect_wifi(timeout=15):
    print("Connecting to Wi-Fi...")
    led_wifi.value(1)

    wlan.active(True)

    if wlan.isconnected():
        print("Wi-Fi already connected:", wlan.ifconfig())
        led_wifi.value(0)
        return True

    wlan.connect(WIFI_SSID, WIFI_PASS)

    start = time.time()
    state = 0
    while not wlan.isconnected():
        led_wifi.value(state)
        state = not state
        time.sleep(0.5)

        if time.time() - start > timeout:
            print("Wi-Fi connection timeout")
            return False

    led_wifi.value(0)
    print("Wi-Fi connected:", wlan.ifconfig())
    return True

def ensure_wifi():
    if wlan.isconnected():
        return True

    print("Wi-Fi disconnected")
    if not connect_wifi(timeout=20):
        restart_esp("Wi-Fi reconnection failed")
    return True

def connect_mqtt():
    global mqtt
    print("Connecting to MQTT...")

    try:
        mqtt = MQTTClient(
            client_id=b"esp32-weather",
            server=MQTT_BROKER,
            user=MQTT_USER,
            password=MQTT_PASS
        )
        mqtt.connect()
        led_iot.value(0)
        print("MQTT connected")
        return True
    except Exception as e:
        print("MQTT connect failed:", e)
        return False

def ensure_mqtt():
    global mqtt

    if mqtt is None:
        if not connect_mqtt():
            restart_esp("Initial MQTT connection failed")
        return

    try:
        # lightweight test publish to confirm socket is still usable
        # comment this out if you do not want heartbeat traffic
        # mqtt.publish(b"b6610545316/status", b'{"status":"alive"}')
        pass
    except Exception as e:
        print("MQTT check failed:", e)
        try:
            mqtt.disconnect()
        except:
            pass

        if not connect_mqtt():
            restart_esp("MQTT reconnection failed")

def get_timestamp():
    now = time.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        now[0], now[1], now[2],
        now[3], now[4], now[5]
    )

def detect():
    i2c0.writeto(d_addr, bytes([14, int(not pin0.value())]))
    i2c0.writeto(d_addr, bytes([15, int(not pin1.value())]))

def pixel(x, y):
    for i in range(16):
        i2c0.writeto(d_addr, bytes([i, 0]))
    num = [
    0xF888F8,
    0x0000F8,
    0xB8A8E8,
    0xA8A8F8,
    0xE020F8,
    0xE8A8B8,
    0xF8A8B8,
    0x8080F8,
    0xF8A8F8,
    0xE8A8F8
    ]
    
    data = [
      num[(x%100)//10] & 0xFF ,
      (num[(x%100)//10] >> 8) & 0xFF,
      (num[(x%100)//10] >> 16) & 0xFF]
    data1 = [
      num[x%10] & 0xFF ,
      (num[x%10] >> 8) & 0xFF,
      (num[x%10] >> 16) & 0xFF]
    data2 = [
      num[(y%100)//10] & 0xFF ,
      (num[(y%100)//10] >> 8) & 0xFF,
      (num[(y%100)//10] >> 16) & 0xFF]
    data3 = [
      num[y%10] & 0xFF ,
      (num[y%10] >> 8) & 0xFF,
      (num[y%10] >> 16) & 0xFF]
    if x >= 10: 
        for i,d in enumerate(data):
            i2c0.writeto(d_addr, bytes([4 - i*2, d]))
    for i,d in enumerate(data1):
        i2c0.writeto(d_addr, bytes([12 - i*2, d]))
    if y >= 10:
        for i,d in enumerate(data2):
            i2c0.writeto(d_addr, bytes([5 - i*2, d]))
    for i,d in enumerate(data3):
        i2c0.writeto(d_addr, bytes([13 - i*2, d]))

def handle(pin):
    global mode, press_time
    now = time.ticks_ms()
    duration = time.ticks_diff(time.ticks_ms(), press_time)
    if duration < DEBOUNCE_MS:
        return
    if pin.value() == 0:  # pressed
        press_time = now
    else:  # released
        if duration > LONG_PRESS_MS:
            mode = 1 - mode;
            print("mode: ", mode)
            led_iot.value(mode)
            time.sleep(1)
        else:
            if pin is sw1:
                value = encoder.value() + 1
                encoder.value(value) 
            else:
                value = encoder.value() - 1
                encoder.value(value) 

def recive_state(topic, msg):
    print(msg)
    global in_c, out_c, value, classroom
    try:
        row = ujson.loads(msg)
        print("row:", row)
        if classroom != row["classroom"]:
            classroom = row["classroom"]
            in_c = row["incount"]
            out_c = row["outcount"]
            value = row["total"]
            encoder.value(value)
            pixel(in_c, out_c)
            print("Updated:", in_c, out_c, value)

    except Exception as e:
        print("Error parsing:", e)

def publish_sensor_data(direction):
    data = {
        "direction": direction,
        "timestamp": get_timestamp()
    }

    json_str = ujson.dumps(data)
    print(json_str)

    mqtt.publish(b"b6610545316/project_laser/msg", json_str.encode())
    print("Published successfully")

# =========================
# Startup
# =========================
led_wifi.value(1)
led_iot.value(1)

if not connect_wifi():
    restart_esp("Wi-Fi failed at startup")

if not connect_mqtt():
    restart_esp("MQTT failed at startup")


value = 0
mode = 0
in_c = 0
out_c = 0
classroom = ""
pixel(0, 0)

sw1.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=handle)
sw2.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=handle)

mqtt.set_callback(recive_state)
mqtt.subscribe(b"b6610545316/project_laser/state")
time.sleep(1)
mqtt.check_msg()
# =========================
# Main loop
# =========================

while True:
    try:
        # if Wi-Fi dropped while idle, recover immediately
        ensure_wifi()
        ensure_mqtt()
        detect()
        mqtt.check_msg()
        if mode:
            led_iot.value(not led_iot.value())
            encoder.value(value)
            new_value = value
        else:
            new_value = encoder.value() 
        if new_value != value and not pin0.value() and not pin1.value():
            if value < new_value:
                direction = "IN"
                in_c+=1
            else:
                out_c+=1
                direction = "OUT"
            print(in_c,out_c,new_value)
            pixel(in_c, out_c)
            if not mode:
                pass
                publish_sensor_data(direction)
            value = new_value
            
        time.sleep(0.1)
    except Exception as e:
        print("Main loop error:", e)
        restart_esp("Main loop exception")
