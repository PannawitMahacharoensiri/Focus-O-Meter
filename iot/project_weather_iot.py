from machine import Pin, ADC, I2C, reset
import time, math, network, ujson, dht, ntptime, socket
from umqtt.robust import MQTTClient
from config import WIFI_SSID, WIFI_PASS, MQTT_BROKER, MQTT_USER, MQTT_PASS

# =========================
# Hardware setup
# =========================
led_wifi = Pin(2, Pin.OUT)
led_iot = Pin(12, Pin.OUT)

# Temp sensor
i2c = I2C(1, sda=Pin(4), scl=Pin(5))
t_addr = 77
i2c.writeto(t_addr, bytearray([0x04, 0b01100000]))  # 14-bit resolution
t_step = 0.03125

# Light sensor
ldr = ADC(Pin(36))
ldr_vref = 3.32
ldr_resis = 33000

# Temp and humidity (KY-015 sensor) 
JST_I1 = dht.DHT11(Pin(32)) # JST port I1 = GPIO32

# Sound (KY-038 sensor)
JST_I2 = ADC(Pin(33))       # JST port I2 = GPIO33
JST_I2.atten(ADC.ATTN_11DB) # full range (0–3.3V)

# Light (KY-018 sensor)
JST_I3 = ADC(Pin(34))       # JST port I3 = GPIO34
JST_I3.atten(ADC.ATTN_11DB)

TOPIC = b"b6610545855/project_inclass_weather"

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

def internet_ok():
    try:
        # Check with the public address
        addr = socket.getaddrinfo("8.8.8.8", 53)[0][-1]
        s = socket.socket()
        s.settimeout(2)
        s.connect(addr)
        s.close()
        return True
    except:
        return False

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
    global mqtt
    
    if wlan.isconnected() and internet_ok():
        return True

    print("Wi-Fi or internet lost")
    
    wlan.disconnect()
    time.sleep(1)
    
    mqtt = None

    if not connect_wifi(timeout=10):
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
            password=MQTT_PASS,
            keepalive=30
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
        for i in range(3):
            if connect_mqtt():
                return
            time.sleep(2)

        print("Initial MQTT failed")
        return
    
    try:
        mqtt.publish(b"b6610545855/test/status", b'{"status":"alive"}')
    except Exception as e:
        print("MQTT check failed:", e)
        try:
            mqtt.disconnect()
        except:
            pass

        for i in range(3):
            print("Reconnect attempt:", i+1)
            if connect_mqtt():
                print("Reconnected passed")
                return
            time.sleep(2)

        print("Reconnect failed")


# =========================
# Sensor function
# =========================


def read_temp():
    i2c.writeto(t_addr, bytearray([0x00]))
    data = i2c.readfrom(t_addr, 2)
    raw = (data[0] << 6) | (data[1] >> 2)
    return raw * t_step

def volt_to_resis(r, vref, v):
    if v >= vref:
        raise ValueError("Measured voltage >= reference voltage")
    return r * (v / (vref - v))

def resis_to_lux(r_ohms):
    log_r = math.log10(r_ohms)
    slope = 0.8
    intercept = 5.2
    log_lux = (intercept - log_r) / slope
    return 10 ** log_lux

def resis_to_lux_calibrated(r):
    b = 1.2
    k = 155.8 * (29108 ** b)  
    
    return k * (r ** -b)

def read_light():
    ldr_v = ldr.read_uv() / 1_000_000
    ldr_r = volt_to_resis(ldr_resis, ldr_vref, ldr_v)
    ldr_lux = resis_to_lux(ldr_r)
    return ldr_lux

def read_light_sensor():
    volt = JST_I3.read_uv() / 1_000_000
    sensor_r = volt_to_resis(ldr_resis, ldr_vref, volt)
    sensor_lux = resis_to_lux_calibrated(sensor_r)
    
    return sensor_lux

def get_timestamp():
    now = time.localtime(time.time() + 7 * 3600)
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(*now[:6])

def read_humid_temp():
    JST_I1.measure()
    
    temp_ky15 = JST_I1.temperature()
    hum_ky15  = JST_I1.humidity()
    
    return temp_ky15, hum_ky15
    
def read_sound():
    sound_raw = JST_I2.read()
    # convert_to_db
    return sound_raw

def publish_sensor_data():
    temp_c = read_temp()
    ldr_lux = read_light()
    light_sensor = read_light_sensor()
    temp_ky15, hum_ky15 = read_humid_temp()
    if len(sound_list) > 0:
        avg_sound = sum(sound_list) / len(sound_list)
    else :
        avg_sound = 0
    sound_list.clear()
    
    data = {
        "temp_c": round( ((temp_c + temp_ky15)/2), 2),
        "light_l": round(((ldr_lux + light_sensor)/2), 2),
        "humid_p": round(hum_ky15, 2),
        "sound_ADC": round(avg_sound, 2),
        "timestamp": get_timestamp()
    }

    json_str = ujson.dumps(data)
    print(json_str)

    mqtt.publish(TOPIC, json_str.encode())
    print("Published successfully")

# =========================
# Startup
# =========================
led_wifi.value(1)
led_iot.value(1)

if not connect_wifi():
    print("Retrying Wi-Fi...")
    time.sleep(5)
    
if not connect_mqtt():
    restart_esp("MQTT failed at startup")

# =========================
# Main loop
# =========================
step = 180  # 3 minutes
step_count = 10

target_time = time.time() + step
target_count = time.time() + 10 #10 second
sound_list = []

while True:
    try:
        
        # blink between sends
        led_iot.value(not led_iot.value())
        time.sleep(1)

        now = time.time()

        # if Wi-Fi dropped while idle, recover immediately
        ensure_wifi()
        ensure_mqtt()
        
        if now >= target_count:
            target_count += step_count
            sound = read_sound()
            sound_list.append(round(sound, 2))
        
        if now >= target_time:
            target_time += step
            publish_sensor_data()
            led_iot.value(0)

    except Exception as e:
        print("Main loop error:", e)
        restart_esp("Main loop exception")






