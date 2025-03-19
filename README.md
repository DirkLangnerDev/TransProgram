# Voice Memo Recorder

Voice Memo Recorder is a Windows-based Python utility designed for personal voice memo capture and transcription. Using a single hotkey, it records your voice, transcribes the recording into German text via OpenAI’s Whisper “turbo” model, and then copies the transcription to your clipboard. The application provides both audible signals and a visual status indicator in the system tray.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

Voice Memo Recorder is intended for users who need a simple, efficient way to capture voice notes and convert them into text in German. The application uses Python libraries to:
- Record audio from your microphone.
- Save the recording temporarily.
- Transcribe the audio using the Whisper “turbo” model (leveraging GPU acceleration when available).
- Provide immediate auditory and visual feedback.
- Copy the resulting transcription into your clipboard.

This tool is especially useful if you require quick voice-to-text conversion without dealing with complex interfaces.

## How It Works

1. **Audio Capture**: The tool uses PyAudio to capture microphone input at 16 kHz in mono. Audio data is buffered and later converted for transcription.
2. **Temporary Saving**: Recorded data is saved as a temporary WAV file after converting the raw float32 audio to a 16-bit format.
3. **Transcription**: The temporary WAV file is processed by OpenAI’s Whisper model (turbo version) with the language fixed to German (`"de"`). If a compatible GPU is present, transcription is accelerated.
4. **Feedback**: 
   - **Auditory Signals**: Different beep tones indicate recording start (700 Hz), recording end (500 Hz), and successful transcription (600 Hz).
   - **Visual Indicator**: A system tray icon shows red when idle and green while recording.
5. **Clipboard Integration**: Once transcribed, the text is automatically copied to your clipboard for immediate use.

## Features

- **Hotkey Control**: Toggle recording using `Ctrl+Alt+R`.
- **Audible Notifications**: 
  - Start beep (700 Hz)
  - Stop beep (500 Hz)
  - Confirmation beep (600 Hz)
- **Visual Status**: System tray icon turns green during recording and reverts to red when idle.
- **Automatic Transcription**: Transcribes voice memos in German using the Whisper “turbo” model, with GPU support if available.
- **Clipboard Copying**: The transcribed text is automatically copied to the clipboard.
- **Easy Exit**: Right-click the system tray icon and select “Beenden” to terminate the application.

## Installation

1. **Clone the Repository**  
   Open your terminal and run:
   ```
   git clone https://your-repo-url.git
   cd trans_program
   ```

2. **Install Dependencies**  
   Run the following command to install required packages:
   ```
   pip install -r requirements.txt
   ```
   The installation requires:
   - pyaudio
   - keyboard
   - pyperclip
   - whisper
   - numpy
   - pillow
   - pystray
   - torch (for GPU support)
   - (Note: The `winsound` module is included with Windows)

   > **Note:** Installing PyAudio on Windows may require additional steps; ensure you have the necessary wheels or compiler support.

## Usage

1. **Starting the Application**  
   Launch the recorder by running:
   ```
   pythonw trans.pyw
   ```
   
   **Important:** Make sure to run this using `pythonw` and not `python`.

2. **Recording a Voice Memo**  
   - Press `Ctrl+Alt+R` to start recording (the system tray icon will turn green).
   - Press `Ctrl+Alt+R` again to stop recording.
   - The application transcribes the recorded audio (in German) and copies the text to your clipboard.

3. **Exiting the Application**  
   To quit, right-click on the system tray icon and select “Beenden”.

## Troubleshooting

- **Audio Capture Issues**:  
  Check your microphone settings if the recording quality is poor or if no audio is captured.
  
- **Dependency Errors**:  
  Ensure all listed Python packages are installed correctly. Consult the package documentation if installation problems arise.
  
- **Performance**:  
  Transcription may be slower on systems without GPU support, especially for longer recordings.

## Contributing

Contributions are welcome. If you wish to contribute:
1. Fork the repository.
2. Create a new branch for your changes.
3. Commit your changes with descriptive messages.
4. Open a pull request detailing your improvements.

Please follow the established coding standards and ensure thorough testing of your changes.

## License

This project is licensed under the MIT License.

---

Voice Memo Recorder provides a streamlined approach to capturing and transcribing voice memos in German. Its intuitive hotkey control, real-time feedback, and clipboard integration make it an ideal tool for efficient voice-to-text conversion on Windows.
