# ESP32S3-chatbot

## Overview
The ESP32S3 Chatbot project is a MicroPython-based application that leverages Google APIs to create an interactive voice chatbot. It records audio with an I2S microphone, processes the data, and communicates with Google Speech-to-Text, Gemini AI, and Google Text-to-Speech to deliver real-time responses.

## Features
- Record and playback audio using I2S components.
- Store audio files on an SD card.
- Connect to Wi-Fi for cloud integration.
- Convert speech to text using Google Speech-to-Text.
- Generate responses via Gemini AI.
- Synthesize chatbot replies into speech with Google TTS.
- User feedback through LEDs and a button interface.

## Setup Instructions
1. Install MicroPython firmware on your ESP32S3 board.
2. Connect the I2S microphone and speaker as per the hardware configuration.
3. Set up and mount the SD card for audio storage.
4. Update the secrets file with your Wi-Fi credentials and Google API key.
5. Ensure network connectivity and run the script to start the chatbot.

## Usage
- Press and hold the button to start recording.
- The system records audio, processes it, and interacts with the Google APIs.
- After transcription and AI processing, listen to the generated response.
- LEDs provide visual feedback during recording, playback, and processing.

## Contributing
Contributions, issues, and feature requests are welcome! Please follow standard GitHub practices when submitting changes.

## Acknowledgements
Special thanks to the MicroPython community and Google API services for enabling this project.