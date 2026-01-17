# Development Guidelines

## Golden Rule: Keep Python and HTML Versions Synced

**IMPORTANT**: When implementing any feature, ALWAYS implement it in BOTH versions:
1. `hebrew_voice_app.py` - Native Python/Pygame for Raspberry Pi
2. `hebrew_voice_app.html` - Web version for phones/tablets/browsers

### Sync Checklist
- [ ] Feature works identically in both versions
- [ ] UI text/labels match in both versions
- [ ] State machine logic is equivalent
- [ ] Error handling is consistent
- [ ] Test on both platforms before marking complete

---

## Game Modes Architecture

### Mode Selection Screen
Both versions should have a mode selection screen at startup with large, colorful buttons for each mode.

### Mode 1: Free Speech (Current MVP)
- **Hebrew**: User speaks Hebrew, app displays what they said
- **English**: User speaks English, app displays what they said
- Purpose: Practice pronunciation, see transcription

### Mode 2: Spelling Bee (TTS + Spelling)
- App speaks a word using TTS (Text-to-Speech)
- User must spell the word (speak each letter)
- App validates spelling
- **Hebrew version**: Hebrew words, Hebrew letter names
- **English version**: English words, English letters
- Features:
  - Word difficulty levels (easy/medium/hard)
  - Visual feedback (correct letters turn green)
  - Repeat button to hear word again

### Mode 3: Translation Game
- **Hebrew → English**: App shows/speaks Hebrew word, user says English translation
- **English → Hebrew**: App shows/speaks English word, user says Hebrew translation
- Features:
  - Word pairs database
  - Hint system (show first letter)
  - Score tracking

### Mode 4: Word Practice (Echo Mode)
- App speaks a word/phrase
- User repeats it
- App compares pronunciation
- Feedback: "Great!" / "Try again"

---

## TTS Implementation

### HTML Version (Web Speech API)
```javascript
const synth = window.speechSynthesis;

function speak(text, lang = 'he-IL') {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;  // 'he-IL' for Hebrew, 'en-US' for English
    utterance.rate = 0.8;   // Slower for learning
    synth.speak(utterance);
}
```

Good free voices:
- Hebrew: Google Hebrew (on Chrome)
- English: Google US English, Microsoft voices

### Python Version
Use `gTTS` (Google Text-to-Speech) for quality:
```python
from gtts import gTTS
import pygame.mixer

def speak(text, lang='he'):
    tts = gTTS(text=text, lang=lang, slow=True)
    tts.save('/tmp/speech.mp3')
    pygame.mixer.music.load('/tmp/speech.mp3')
    pygame.mixer.music.play()
```

Alternative: `pyttsx3` for offline (lower quality)

---

## Language Configuration

```javascript
// HTML
const LANGUAGES = {
    hebrew: { code: 'he-IL', name: 'עברית', dir: 'rtl' },
    english: { code: 'en-US', name: 'English', dir: 'ltr' }
};
```

```python
# Python
LANGUAGES = {
    'hebrew': {'code': 'he-IL', 'name': 'עברית', 'dir': 'rtl'},
    'english': {'code': 'en-US', 'name': 'English', 'dir': 'ltr'}
}
```

---

## Word Lists

Store in shared JSON format that both versions can use:

```json
{
  "spelling": {
    "hebrew": {
      "easy": ["אבא", "אמא", "כלב", "חתול"],
      "medium": ["שולחן", "מחשב", "טלפון"],
      "hard": ["מקרר", "מכונית", "אוטובוס"]
    },
    "english": {
      "easy": ["cat", "dog", "sun", "mom"],
      "medium": ["house", "water", "happy"],
      "hard": ["elephant", "beautiful", "computer"]
    }
  },
  "translations": [
    {"he": "כלב", "en": "dog"},
    {"he": "חתול", "en": "cat"},
    {"he": "בית", "en": "house"}
  ]
}
```

---

## Deployment

### Phone/Tablet
Use GitHub Pages - automatically provides HTTPS (required for microphone):
```
https://barakem.github.io/hebrew-voice-game/hebrew_voice_app.html
```

### Raspberry Pi
Run the Python version directly:
```bash
python3 hebrew_voice_app.py
```

---

## State Machine (Must Match in Both Versions)

```
READY → (tap) → RECORDING → (tap/timeout) → PROCESSING → SHOWING → (tap) → READY
                    ↓
              (error) → READY
```

States:
- `ready` - Green button, waiting for input
- `recording` - Red button, capturing audio
- `processing` - Yellow button, API call in progress
- `showing` - Green button, displaying result

---

## UI Constants (Keep Synced)

### Colors
| Name | Hex | Use |
|------|-----|-----|
| Bright Green | #32cd32 | Ready state |
| Bright Red | #ff5050 | Recording state |
| Bright Yellow | #ffd700 | Processing state |
| Soft Blue | #6495ed | Accents, borders |
| Background | #f0f8ff | Alice blue background |

### Hebrew UI Text
| Key | Hebrew | English |
|-----|--------|---------|
| TAP_TO_SPEAK | לחץ לדבר! | Tap to speak! |
| RECORDING | מקליט... (לחץ לעצירה) | Recording... (tap to stop) |
| PROCESSING | מעבד... | Processing... |
| LISTENING | מקשיב... | Listening... |
| NOT_UNDERSTOOD | לא הבנתי | Didn't understand |
| SELECT_MODE | בחר משחק | Select game |
| SPELLING | איות | Spelling |
| TRANSLATION | תרגום | Translation |
| FREE_SPEECH | דיבור חופשי | Free speech |

---

## File Structure

```
hebrew-voice-game/
├── CLAUDE.md              # This file - dev guidelines
├── README.md              # User documentation
├── LICENSE                # MIT License
├── hebrew_voice_app.py    # Python version (Raspberry Pi)
├── hebrew_voice_app.html  # HTML version (Phone/Browser)
├── words.json             # Shared word lists (future)
└── assets/                # Shared assets (future)
    ├── sounds/
    └── images/
```

---

## Testing Checklist

Before committing any feature:
- [ ] Test Python version on Raspberry Pi / desktop
- [ ] Test HTML version in Chrome desktop
- [ ] Test HTML version on Android phone (via serve.py)
- [ ] Test HTML version on iOS Safari (via serve.py)
- [ ] Verify Hebrew text renders correctly (RTL)
- [ ] Verify English text renders correctly (LTR)
- [ ] Check TTS works in both languages
