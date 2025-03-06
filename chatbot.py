from machine import I2S, Pin, SDCard
import os
import time
import struct
import binascii
import json
import urequests
import network
from secrets import API_KEY, WIFI_SSID, WIFI_PASSWORD

global transcript
global gemini_response

# Setup record button
record_pin = Pin(10, Pin.IN)

#Setup LED Pin
led_pin = Pin(12, Pin.OUT)

def blink_led(num):
    for i in range(num):
        led_pin.on()
        time.sleep(0.2)
        led_pin.off()
        time.sleep(0.2)

def wait_for_button():
    while record_pin.value() == 0:
        time.sleep_ms(100)
    time.sleep_ms(100)
    
def encode_audio(file_path):
    try:
        with open(file_path, "rb") as f:
            encoded_audio = binascii.b2a_base64(f.read()).decode("utf-8").replace("\n", "")
        return encoded_audio
    except Exception as e:
        print("❌ Error Encoding File:", e)
        return None

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)  # Set ESP32 as a station (client)
    wlan.active(True)  # Activate Wi-Fi

    if not wlan.isconnected():
        print(f"🔌 Connecting to {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait for connection
        for _ in range(10):
            if wlan.isconnected():
                print("✅ Connected! IP Address:", wlan.ifconfig()[0])
                return True
            time.sleep(1)
            
    if wlan.isconnected():
        print("✅ Connected! IP Address:", wlan.ifconfig()[0])
        return True

    print("❌ Wi-Fi Connection Failed!")
    return False

def send_to_gemini(transcript):
    if not transcript:
        print("⚠️ No transcription to send to Gemini.")
        return None
    else:
        print(f"Transcript = {transcript}")
        
    print("🚀 Sending to Gemini AI...")
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    content = "Translate into Hinglish" + transcript + ", Answer in a Single line Only."
    data = json.dumps({
        "contents": [{"parts": [{"text": content}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 20
        }
    })

    try:
        response = urequests.post(url, data=data, headers=headers)
        result = response.json()
        response.close()

        if "candidates" in result:
            answer = result["candidates"][0]["content"]["parts"][0]["text"]
            print("🤖 Gemini AI Response:", answer)
            return answer
        else:
            print("❌ No response from Gemini:", result)
            return None
    except Exception as e:
        print("❌ Gemini API Request Failed:", e)
        return None

def send_to_google_tts(text):
    if not text:
        print("⚠️ No text to synthesize.")
        return None

    print("📢 Sending to Google TTS...")
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({
        "input": {"text": text},
        "voice": {
            "languageCode": "en-IN",
            "name": "en-IN-Wavenet-D"
            },
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": 8000
            }
    })

    try:
        response = urequests.post(url, data=data, headers=headers)
        result = response.json()
        response.close()

        if "audioContent" in result:
            print("✅ TTS Audio Received in 8000Hz!")
            audio_data = binascii.a2b_base64(result["audioContent"])

            # Save TTS Audio to SD Card
            tts_file = "/sd/tts_audio.wav"
            with open(tts_file, "wb") as f:
                f.write(audio_data)
            
            print(f"📁 TTS Audio Saved: {tts_file}")
            return tts_file
        else:
            print("❌ No audio generated:", result)
            return None
    except Exception as e:
        print("❌ Google TTS API Request Failed:", e)
        return None

# I2S Pins for INMP441 Mic
mic_sck_pin = Pin(1)  # BCLK
mic_ws_pin = Pin(4)   # LRCLK
mic_sd_pin = Pin(3)   # DOUT

# I2S Pins for MAX98357A Speaker
spk_bck_pin = Pin(1)  # BCLK
spk_ws_pin = Pin(5)   # LRCLK
spk_sdout_pin = Pin(6) # DIN

# Setup I2S for Microphone (INMP441)
audio_in = I2S(
    0,
    sck=mic_sck_pin,
    ws=mic_ws_pin,
    sd=mic_sd_pin,
    mode=I2S.RX,
    bits=32,  
    format=I2S.MONO,
    rate=8000,
    ibuf=2048
)

# Setup I2S for Speaker (MAX98357A)
audio_out = I2S(
    1,
    sck=spk_bck_pin,
    ws=spk_ws_pin,
    sd=spk_sdout_pin,
    mode=I2S.TX,
    bits=32,  
    format=I2S.MONO,
    rate=8000,
    ibuf=2048
)

# SD Card Pins
clk = Pin(2)
mosi = Pin(8)
miso = Pin(9)
cs = Pin(7)

# Initialize SD Card
try:
    sd = SDCard(slot=2, sck=clk, mosi=mosi, miso=miso, cs=cs)
    os.mount(sd, "/sd")
    print("✅ SD Card Mounted Successfully!")
except Exception as e:
    print("❌ SD Card Error:", e)
    sd = None

# Function to Write WAV Header
def write_wav_header(file, sample_rate, num_channels, bit_depth, data_size):
    file.write(b'RIFF')
    file.write(struct.pack('<I', 36 + data_size))  
    file.write(b'WAVEfmt ')
    file.write(struct.pack('<IHHIIHH', 16, 1, num_channels, sample_rate, sample_rate * num_channels * 2, num_channels * 2, bit_depth))
    file.write(b'data')
    file.write(struct.pack('<I', data_size))  

# Start Recording
print("Press and hold button to record")
blink_led(2)
wait_for_button()
print("Recording...")

samples = bytearray(2048)
converted_samples = bytearray()

while record_pin.value() == 1:
    read_bytes = audio_in.readinto(samples)

    # Amplify sound safely (values from 2 to 6 only)
    I2S.shift(buf=samples, bits=32, shift=3)

    for i in range(0, read_bytes, 4):
        sample_32 = struct.unpack_from("<i", samples, i)[0]
        sample_16 = struct.pack("<h", sample_32 >> 16)
        converted_samples.extend(sample_16)

print("Finished Recording")
blink_led(3)
time.sleep(0.5)

# Save to SD Card
if sd:
    try:
        file_path = "/sd/recorded_audio.wav"
        with open(file_path, "wb") as file:
            write_wav_header(file, 8000, 1, 16, len(converted_samples))
            file.write(converted_samples)

        print(f"Saved as {file_path}")
    except Exception as e:
        print("❌ Error Saving File:", e)

# Playback Recorded Audio from SD Card
print("Press the button to playback")
blink_led(2)
wait_for_button()
print("Playing from SD card...")

if sd:
    try:
        with open("/sd/recorded_audio.wav", "rb") as file:
            file.seek(44)  # Skip WAV header
            while True:
                chunk = file.read(512)
                if not chunk:
                    break
                
                playback_samples = bytearray()
                for i in range(0, len(chunk), 2):
                    sample_16 = struct.unpack_from("<h", chunk, i)[0]
                    sample_32 = sample_16 << 16
                    playback_samples.extend(struct.pack("<i", sample_32))

                audio_out.write(playback_samples)

        print("Finished Playback")
    except Exception as e:
        print("❌ Error Reading File:", e)
blink_led(3)
time.sleep(0.5)

# List all files on SD Card
if sd:
    print("\n📂 Files on SD Card:")
    try:
        for file_name in os.listdir("/sd"):
            print(f" - {file_name}")
    except Exception as e:
        print("❌ Error Listing Files:", e)
        
# Sending the Audio File to Google API
print("Press the button to Sending it to Google")
blink_led(2)
wait_for_button()
print("Sending it to Google")

""" Sends the recorded audio to Google STT and returns the transcribed text. """
if sd:
    if connect_wifi():
        AUDIO_FILE = "/sd/recorded_audio.wav"

        # Encode the audio file
        audio_base64 = encode_audio(AUDIO_FILE)
        if not audio_base64:
            print("❌ Failed to encode audio.")
        else:
            print("✅ Audio Encoded Successfully.")

        # Google STT API Endpoint
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"

        # Request Payload
        headers = {"Content-Type": "application/json"}
        data = json.dumps({
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": 8000,
                "languageCode": "en-IN"
            },
            "audio": {
                "content": audio_base64
            }
        })

        # Send POST Request
        try:
            response = urequests.post(url, data=data, headers=headers)
            result = response.json()
            response.close()
            
            # Extract and print the transcript
            if "results" in result:
                transcript = result["results"][0]["alternatives"][0]["transcript"]
                print("📝 Transcription:", transcript)
            else:
                print("❌ No transcription found:", result)
        except Exception as e:
            print("❌ API Request Failed:", e)
    else:
        print("⚠️ Cannot send request: No internet")
blink_led(3)
time.sleep(0.5)

# Sending the Transcript to Google API
print("Press the button to Send it to Gemini")
blink_led(2)
wait_for_button()
print("Sending it to Gemini")

""" Sends the transcribed text to Gemini API and returns the AI-generated response. """
if sd:
    if connect_wifi():
        gemini_response = send_to_gemini(transcript)
        print("✅ Final Response:", gemini_response)
blink_led(3)
time.sleep(0.5)
        
# Calling Google TTS After Gemini Response
print("Press the button to convert Gemini Response to Speech")
blink_led(2)
wait_for_button()

""" Sends text to Google TTS and plays the response. """
if sd:
    if connect_wifi():
        tts_file = send_to_google_tts(gemini_response)

        if tts_file:
            print("📢 Playing TTS Audio...")
            with open(tts_file, "rb") as file:
                file.seek(44)  # Skip WAV header
                while True:
                    chunk = file.read(64)
                    if not chunk:
                        break
                    
                    playback_samples = bytearray()
                    for i in range(0, len(chunk), 2):
                        sample_16 = struct.unpack_from("<h", chunk, i)[0]
                        sample_32 = sample_16 << 16
                        playback_samples.extend(struct.pack("<i", sample_32))

                    audio_out.write(playback_samples)

            print("✅ Finished Speaking!")

# Unmount SD Card
if sd:
    os.umount("/sd")
    print("✅ SD Card Unmounted Successfully!")



