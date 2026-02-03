# Hebrew Voice Game / משחק קול בעברית

A toddler-friendly voice recognition app for learning Hebrew speech. Designed for Raspberry Pi with touchscreen.

## Features

### Current (MVP)
- **Voice Recognition**: Uses Google Speech Recognition API for fast, accurate Hebrew transcription
- **Toddler-Friendly UI**: Large colorful buttons, simple interface, fullscreen mode
- **Manual Recording Control**: Tap to start recording, tap again to stop early
- **Auto-Stop**: Automatically stops recording after 10 seconds
- **Visual Feedback**: Color-coded states (green=ready, red=recording, yellow=processing)
- **Hebrew RTL Support**: Proper right-to-left text rendering with niqqud stripping

### Versions
- `hebrew_voice_app.py` - Native Python/Pygame app for Raspberry Pi
- `hebrew_voice_app.html` / `hebrew_voice_app_fixed.html` - Web version using Web Speech API

## Requirements

### Python Version
```
pygame
pyaudio
scipy
numpy
SpeechRecognition
python-bidi
```

### System Dependencies (Raspberry Pi)
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

## Usage

### Option 1: Phone/Tablet (via GitHub Pages)

Open in Chrome on your phone:
```
https://barakem.github.io/hebrew-voice-game/hebrew_voice_app.html
```

- Works on any phone/tablet with Chrome
- No installation needed
- Allow microphone access when prompted

### Option 2: Raspberry Pi (Python App)
```bash
pip install gtts  # for text-to-speech
python3 hebrew_voice_app.py
```

**Keyboard Controls:**
- SPACE: Start/stop recording
- ESC: Exit app
- H: Switch to Hebrew
- E: Switch to English
- S: Save screenshot

### Option 3: Desktop Browser
Open `hebrew_voice_app.html` directly in Chrome.

### Option 4: Cast to TV
Cast the web app to your TV for a big-screen experience! See **[TV_CASTING_GUIDE.md](TV_CASTING_GUIDE.md)** for:
- Native browser casting (Chrome Cast, AirPlay)
- Google Cast API integration
- HDMI cable connection
- Raspberry Pi TV setup

**Quick Start:** Open the web app in Chrome and tap ⋮ → Cast → Select your TV

## Game Modes

### Mode 1: Free Speech (Current)
- Speak in Hebrew or English, see transcription
- Language toggle switch

### Mode 2: Spelling Bee
- App speaks a word using TTS
- User spells it out loud (letter by letter)
- Available in Hebrew and English

### Mode 3: Translation
- Hebrew → English: Hear/see Hebrew word, say English translation
- English → Hebrew: Hear/see English word, say Hebrew translation

### Mode 4: Echo Practice
- App speaks a word/phrase
- User repeats it
- Comparison feedback

## Roadmap

### Phase 1: Multi-Mode Foundation
- [ ] Mode selection screen with big colorful buttons
- [ ] Language toggle (Hebrew/English) for Free Speech mode
- [ ] TTS integration (Web Speech API for HTML, gTTS for Python)

### Phase 2: Spelling Bee Mode
- [ ] Word lists (easy/medium/hard)
- [ ] TTS speaks the word
- [ ] Letter-by-letter validation
- [ ] Visual feedback for correct letters

### Phase 3: Translation Mode
- [ ] Word pairs database (Hebrew-English)
- [ ] Bidirectional translation game
- [ ] Hint system
- [ ] Score tracking

### Phase 4: Polish & Extras
- [ ] Success/error sounds
- [ ] Streak counter
- [ ] Progress persistence
- [ ] Settings menu

## Architecture

```
hebrew_voice_app.py
├── HebrewVoiceApp class
│   ├── _record_audio()      # Audio capture with PyAudio
│   ├── _process_audio()     # Google Speech API integration
│   ├── _handle_touch()      # Input handling (tap to start/stop)
│   ├── _draw_button()       # Animated touch button
│   └── _draw_text_display() # RTL Hebrew text rendering
├── Hebrew text utilities
│   ├── strip_niqqud()       # Remove vowel marks
│   └── prepare_hebrew_text() # Bidi algorithm for RTL
└── Constants
    ├── Colors (toddler-friendly palette)
    ├── Audio settings (44.1kHz, mono)
    └── UI text (Hebrew strings)
```

## Configuration

Key settings in `hebrew_voice_app.py`:
- `MAX_RECORDING_TIME = 10` - Auto-stop after N seconds
- `RECORD_SAMPLE_RATE = 44100` - Audio sample rate
- `BUTTON_HEIGHT = 25%` - Button size relative to screen

## Documentation

### TV Casting
- **[CASTING_COMPARISON.md](CASTING_COMPARISON.md)** - 📊 Compare all casting methods (recommended starting point)
- **[TV_CASTING_GUIDE.md](TV_CASTING_GUIDE.md)** - 📖 Complete guide to casting to TV (6 methods with code examples)
- **[CASTING_QUICK_START.md](CASTING_QUICK_START.md)** - ⚡ Quick reference card for casting
- **[casting_demo.html](casting_demo.html)** - 🎯 Live demo of Google Cast integration

### Development
- **[CLAUDE.md](CLAUDE.md)** - Development guidelines for contributors

## License

MIT License - see [LICENSE](LICENSE)
