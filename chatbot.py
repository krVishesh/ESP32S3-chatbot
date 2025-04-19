import os
import time
import struct
import binascii
import json
import network
import urequests
import neopixel
from machine import I2S, Pin, SDCard

# Replace these with your own credentials
from secrets import API_KEY, WIFI_SSID, WIFI_PASSWORD

# Helper function to check if a file exists in MicroPython
def file_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False

# I2S Pins for INMP441 Mic (RX)
mic_sck_pin = Pin(1)  # BCLK
mic_ws_pin = Pin(4)   # LRCLK
mic_sd_pin = Pin(3)   # DOUT

# I2S Pins for MAX98357A Speaker (TX)
spk_bck_pin = Pin(1)  # BCLK
spk_ws_pin = Pin(5)   # LRCLK
spk_sdout_pin = Pin(6) # DIN

# SD Card Pins
clk = Pin(2)
mosi = Pin(8)
miso = Pin(9)
cs = Pin(7)

# Two Button Pins
chat_button = Pin(10, Pin.IN)       # Triggers Chat function
translate_button = Pin(11, Pin.IN)  # Triggers Translation function

# LED Pin
led_pin = Pin(12, Pin.OUT)
second_led_pin = Pin(13, Pin.OUT)
NEOPIXEL_PIN = 21
np = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), 1)

# Initialize I2S for Microphone (RX) and Speaker (TX)
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

# SD Card Initialization
try:
    sd = SDCard(slot=2, sck=clk, mosi=mosi, miso=miso, cs=cs)
    os.mount(sd, "/sd")
    print("✅ SD Card Mounted Successfully!")
except Exception as e:
    print("❌ SD Card Error:", e)
    error_led_on()
    time.sleep(1)
    error_led_off()
    sd = None

def error_led_on():
    """Turn on the error LED."""
    second_led_pin.on()

def error_led_off():
    """Turn off the error LED."""
    second_led_pin.off()

def error_led_flash(duration=1):
    """Flash the error LED for the specified duration in seconds."""
    error_led_on()
    time.sleep(duration)
    error_led_off()

def light_up_board(color):
    np[0] = color
    np.write()

def blink_led(times):
    """Blink LED a specified number of times."""
    for _ in range(times):
        led_pin.on()
        time.sleep(0.2)
        led_pin.off()
        time.sleep(0.2)

def connect_wifi():
    """Connect to Wi-Fi using credentials from secrets.py."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"🔌 Connecting to {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(10):
            if wlan.isconnected():
                print("✅ Connected! IP Address:", wlan.ifconfig()[0])
                return True
            time.sleep(1)
    if wlan.isconnected():
        print("✅ Connected! IP Address:", wlan.ifconfig()[0])
        return True
    print("❌ Wi-Fi Connection Failed!")
    error_led_flash()
    return False

def write_wav_header(file, sample_rate, num_channels, bit_depth, data_size):
    """Writes a standard 44-byte WAV header for the recorded file."""
    file.write(b'RIFF')
    file.write(struct.pack('<I', 36 + data_size))
    file.write(b'WAVEfmt ')
    file.write(struct.pack('<IHHIIHH',
                           16,  # Subchunk1Size
                           1,   # AudioFormat = PCM
                           num_channels,
                           sample_rate,
                           sample_rate * num_channels * 2,
                           num_channels * 2,
                           bit_depth))
    file.write(b'data')
    file.write(struct.pack('<I', data_size))

def record_while_button_held(pin):
    """
    Records audio while the specified button pin is held down.
    Returns the raw 16-bit samples of the recorded data.
    """
    print("Press and hold the button to record. Release to stop.")

    # Wait until the button is pressed
    while pin.value() == 0:
        time.sleep_ms(100)
    print("Recording started...")

    samples = bytearray(2048)
    converted_samples = bytearray()

    # Keep recording while the button is held down
    try:
        while pin.value() == 1:
            read_bytes = audio_in.readinto(samples)
            # Amplify sound (shift bits)
            I2S.shift(buf=samples, bits=32, shift=3)
            for i in range(0, read_bytes, 4):
                sample_32 = struct.unpack_from("<i", samples, i)[0]
                sample_16 = struct.pack("<h", sample_32 >> 16)
                converted_samples.extend(sample_16)

        print("Finished Recording")
        blink_led(3)
        return converted_samples
    except Exception as e:
        print("❌ Recording Error:", e)
        error_led_flash()
        return bytearray()

def save_audio_to_sd(converted_samples, file_path="/sd/recorded_audio.wav"):
    """Save the raw 16-bit samples into a WAV file on the SD card."""
    if not sd:
        print("❌ No SD card available.")
        error_led_flash()
        return None
    try:
        with open(file_path, "wb") as file:
            write_wav_header(file, 8000, 1, 16, len(converted_samples))
            file.write(converted_samples)
        print(f"Saved audio as {file_path}")
        blink_led(3)
        return file_path
    except Exception as e:
        print("❌ Error Saving File:", e)
        error_led_flash()
    return None

def play_audio_from_sd(file_path="/sd/recorded_audio.wav"):
    """Play a WAV file from the SD card on the speaker using I2S."""
    if not sd:
        error_led_flash()
        return
    if not file_exists(file_path):
        print("❌ Audio file does not exist.")
        error_led_flash()
        return

    try:
        print(f"Playing {file_path}...")
        with open(file_path, "rb") as file:
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
        blink_led(3)
    except Exception as e:
        print("❌ Error Reading File:", e)
        error_led_flash()

def list_files_on_sd():
    """List all files present on the SD card."""
    if sd:
        print("\n📂 Files on SD Card:")
        try:
            for file_name in os.listdir("/sd"):
                print(f" - {file_name}")
        except Exception as e:
            print("❌ Error Listing Files:", e)
            error_led_flash()
        blink_led(3)

def encode_audio(file_path):
    """Encodes the given audio file in base64 for sending to Google STT."""
    try:
        with open(file_path, "rb") as f:
            encoded_audio = binascii.b2a_base64(f.read()).decode("utf-8").replace("\n", "")
        return encoded_audio
    except Exception as e:
        print("❌ Error Encoding File:", e)
        error_led_flash()
        return None

def send_audio_to_google_stt(file_path="/sd/recorded_audio.wav"):
    """
    Send the recorded audio file to Google STT and return the transcription.
    """
    if not sd or not file_exists(file_path):
        print("❌ Audio file not found.")
        error_led_flash()
        return None

    if not connect_wifi():
        print("⚠️ Cannot send request: No internet")
        error_led_flash()
        return None

    encoded_audio = encode_audio(file_path)
    if not encoded_audio:
        print("❌ Failed to encode audio.")
        error_led_flash()
        return None

    print("✅ Audio Encoded Successfully. Sending to Google STT...")
    stt_url = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"
    stt_headers = {"Content-Type": "application/json"}
    stt_data = json.dumps({
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 8000,
            "languageCode": "en-IN"
        },
        "audio": {
            "content": encoded_audio
        }
    })
    try:
        response = urequests.post(stt_url, data=stt_data, headers=stt_headers)
        result = response.json()
        response.close()
        if "results" in result:
            transcript = result["results"][0]["alternatives"][0]["transcript"]
            print("📝 Transcription:", transcript)
            blink_led(3)
            return transcript
        else:
            light_up_board((50, 50, 50))  # White
            time.sleep(0.5)
            light_up_board((0, 0, 0))  # Off
            time.sleep(0.5)
            print("❌ No transcription found:", result)
            error_led_flash()
    except Exception as e:
        print("❌ API Request Failed:", e)
        error_led_flash()
    return None

def send_text_to_gemini(prompt):
    """Sends text (prompt) to Gemini API and returns the AI-generated response."""
    if not prompt:
        print("⚠️ No prompt to send to Gemini.")
        error_led_flash()
        return None

    if not connect_wifi():
        print("⚠️ Cannot send request: No internet")
        error_led_flash()
        return None

    print("🚀 Sending to Gemini with Prompt:", prompt)
    gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 50
        }
    })
    try:
        response = urequests.post(gemini_url, data=data, headers=headers)
        result = response.json()
        response.close()
        if "candidates" in result:
            answer = result["candidates"][0]["content"]["parts"][0]["text"]
            print("🤖 Gemini AI Response:", answer)
            blink_led(3)
            return answer
        else:
            light_up_board((50, 50, 50))  # White
            time.sleep(0.5)
            light_up_board((0, 0, 0))  # Off
            time.sleep(0.5)
            print("❌ No response from Gemini:", result)
            error_led_flash()
    except Exception as e:
        print("❌ Gemini API Request Failed:", e)
        error_led_flash()
    return None

def text_to_speech(text):
    """Sends text to Google TTS, saves the audio to SD, and returns the filename."""
    if not text:
        print("⚠️ No text to synthesize.")
        error_led_flash()
        return None

    if not connect_wifi():
        print("⚠️ Cannot send request: No internet")
        error_led_flash()
        return None

    print("📢 Sending to Google TTS...")
    tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"
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
        response = urequests.post(tts_url, data=data, headers=headers)
        result = response.json()
        response.close()
        if "audioContent" in result:
            print("✅ TTS Audio Received in 8000Hz!")
            audio_data = binascii.a2b_base64(result["audioContent"])
            tts_file = "/sd/tts_audio.wav"
            try:
                with open(tts_file, "wb") as f:
                    f.write(audio_data)
                print(f"📁 TTS Audio Saved: {tts_file}")
                blink_led(3)
                return tts_file
            except Exception as e:
                print("❌ Error Saving TTS File:", e)
                error_led_flash()
        else:
            light_up_board((50, 50, 50))  # White
            time.sleep(0.5)
            light_up_board((0, 0, 0))  # Off
            time.sleep(0.5)
            print("❌ No audio generated:", result)
            error_led_flash()
    except Exception as e:
        print("❌ Google TTS API Request Failed:", e)
        error_led_flash()
    return None

def play_tts_audio(file_path="/sd/tts_audio.wav"):
    """Play the TTS WAV file from the SD card."""
    if not sd or not file_exists(file_path):
        error_led_flash()
        return
    print(f"📢 Playing TTS Audio: {file_path}")
    try:
        with open(file_path, "rb") as file:
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
        blink_led(3)
    except Exception as e:
        print("❌ Error Playing TTS Audio:", e)
        error_led_flash()

def chat_flow():
    """
    Chat Flow:
    1) Record audio while the chat_button is pressed.
    2) Playback, STT, send to Gemini with a 'chat' style prompt.
    3) TTS and playback.
    """
    recorded_samples = record_while_button_held(chat_button)
    recorded_file = save_audio_to_sd(recorded_samples, "/sd/recorded_audio.wav")

    if recorded_file:
        play_audio_from_sd(recorded_file)
        list_files_on_sd()

        user_transcript = send_audio_to_google_stt(recorded_file)
        if user_transcript:
            prompt = "Let's chat about this: " + user_transcript + "; Answers should be 1-2 lines only."
            gemini_response = send_text_to_gemini(prompt)
            if gemini_response:
                tts_filepath = text_to_speech(gemini_response)
                if tts_filepath:
                    play_tts_audio(tts_filepath)
                    
    print("Waiting for button Press")

def translate_flow():
    """
    Translation Flow:
    1) Record audio while the translate_button is pressed.
    2) Playback, STT, send to Gemini with a 'translate into Hindi' prompt.
    3) TTS and playback.
    """
    recorded_samples = record_while_button_held(translate_button)
    recorded_file = save_audio_to_sd(recorded_samples, "/sd/recorded_audio.wav")

    if recorded_file:
        play_audio_from_sd(recorded_file)
        list_files_on_sd()

        user_transcript = send_audio_to_google_stt(recorded_file)
        if user_transcript:
            prompt = "Translate into Hindi " + user_transcript + ", answer in a single line only, use only English alphabet letters."
            gemini_response = send_text_to_gemini(prompt)
            if gemini_response:
                tts_filepath = text_to_speech(gemini_response)
                if tts_filepath:
                    play_tts_audio(tts_filepath)
                    
    print("Waiting for button Press")

def main():
    """
    Main loop that waits for either the Chat button or the Translate button to be pressed.
    After each flow completes, it restarts automatically.
    """
    # Make sure error LED is off at startup
    error_led_off()
    print("Waiting for button Press")
    while True:
        # If chat button is pressed
        if chat_button.value() == 1:
            chat_flow()

        # If translate button is pressed
        if translate_button.value() == 1:
            translate_flow()

        time.sleep(0.2)

if __name__ == "__main__":
    main()

