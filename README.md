# ESP32S3 Chatbot 🤖

## 📋 Overview

The ESP32S3 Chatbot is an intelligent voice assistant built on the ESP32S3 microcontroller using MicroPython. This project combines hardware capabilities with cloud-based AI services to create an interactive voice chatbot experience. It features real-time audio processing, cloud-based speech recognition, AI-powered responses, and natural-sounding speech synthesis.

## ✨ Features

- 🎤 **Audio Processing**
  - I2S microphone integration for high-quality audio input
  - Real-time audio recording and playback
  - SD card storage for audio files

- 🌐 **Cloud Integration**
  - Seamless Wi-Fi connectivity
  - Google Speech-to-Text for accurate voice recognition
  - Gemini AI for intelligent responses
  - Google Text-to-Speech for natural voice output

- 💡 **User Interface**
  - LED indicators for system status
  - Button-based control interface
  - Visual feedback for recording and processing states

## 🛠️ Hardware Requirements

- ESP32S3 development board
- I2S microphone (e.g., INMP441)
- Speaker or audio output device
- SD card module
- Push button
- LEDs (for status indication)
- Jumper wires and breadboard

## ⚙️ Software Requirements

- MicroPython firmware for ESP32S3
- Google Cloud account with enabled APIs:
  - Speech-to-Text API
  - Gemini AI API
  - Text-to-Speech API
- Python 3.x (for development)

## 🚀 Setup Instructions

1. **Hardware Setup**
   ```bash
   # I2S Microphone (INMP441):
   # - VDD to 3.3V
   # - GND to GND
   # - WS (LRCLK) to GPIO 4
   # - SD (DOUT) to GPIO 3
   # - SCK (BCLK) to GPIO 1

   # I2S Speaker (MAX98357A):
   # - VDD to 3.3V
   # - GND to GND
   # - BCLK to GPIO 1
   # - LRCLK to GPIO 5
   # - DIN to GPIO 6

   # SD Card Module:
   # - CLK to GPIO 2
   # - MOSI to GPIO 8
   # - MISO to GPIO 9
   # - CS to GPIO 7

   # Buttons:
   # - Chat Button to GPIO 10
   # - Translate Button to GPIO 11

   # LEDs:
   # - Status LED to GPIO 12
   # - Error LED to GPIO 13
   # - NeoPixel to GPIO 21
   ```

2. **Software Setup**
   - Flash MicroPython firmware to ESP32S3
   - Install required MicroPython libraries
   - Configure Wi-Fi credentials in `secrets.py`
   - Set up Google API credentials

3. **Configuration**
   - Update `secrets.py` with your:
     - Wi-Fi SSID and password
     - Google API key
     - Project-specific settings

## 📝 Usage Guide

1. Power on the ESP32S3 board
2. Wait for Wi-Fi connection (indicated by LED)
3. Press and hold the button to start recording
4. Speak your query clearly
5. Release the button to process
6. Listen to the AI response

## 🔧 Troubleshooting

- **No Audio Input**
  - Check I2S microphone connections
  - Verify microphone power supply
  - Ensure proper GPIO pin configuration

- **Wi-Fi Connection Issues**
  - Verify credentials in `secrets.py`
  - Check network availability
  - Ensure proper antenna connection

- **API Errors**
  - Verify Google API key validity
  - Check API quota limits
  - Ensure proper API enablement

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- MicroPython community for the excellent firmware
- Google Cloud team for their powerful APIs
- ESP32 community for hardware support
- All contributors and users of this project

## 📞 Support

For support, please:
- Open an issue in the GitHub repository
- Check the troubleshooting guide
- Contact the maintainers

---

<div align="center">
  Made with ❤️ using MicroPython and ESP32S3
</div>