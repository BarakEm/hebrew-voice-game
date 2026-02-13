#!/usr/bin/env python3
"""
Hebrew Voice Learning App
Toddler-friendly voice recognition app for Raspberry Pi
Supports Hebrew and English with multiple game modes
"""

import pygame
import pyaudio
import wave
import threading
import os
import tempfile
import re
import logging
import io
import json
import random
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
import speech_recognition as sr
from bidi.algorithm import get_display
import requests

# Optional TTS support
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    print("Note: gTTS not installed. Install with: pip install gtts")

# Set up logging
LOG_FILE = os.path.expanduser("~/hebrew-voice-game/app.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Initialize pygame
pygame.init()
pygame.mixer.init()
display_info = pygame.display.Info()
SCREEN_WIDTH = display_info.current_w
SCREEN_HEIGHT = display_info.current_h
log.info(f"Detected screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")


# ===========================================
# CONFIGURATION
# ===========================================
MAX_RECORDING_TIME = 10  # seconds

# Colors - toddler-friendly
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BRIGHT_GREEN = (50, 205, 50)
BRIGHT_RED = (255, 80, 80)
BRIGHT_BLUE = (100, 149, 237)
BRIGHT_YELLOW = (255, 215, 0)
SOFT_BACKGROUND = (240, 248, 255)
TEAL = (78, 205, 196)
CORAL = (255, 107, 107)
GRAY = (200, 200, 200)
PURPLE = (155, 89, 182)  # Continuous mode color

# Audio settings
RECORD_SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16

# Default words structure if loading fails
DEFAULT_WORDS_DATA = {
    "spelling": {
        "hebrew": {"easy": [], "medium": [], "hard": []}, 
        "english": {"easy": [], "medium": [], "hard": []}
    },
    "translations": []
}


# ===========================================
# ENUMS AND DATA CLASSES
# ===========================================
class AppState(Enum):
    MODE_SELECT = "mode_select"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    SHOWING = "showing"


class GameMode(Enum):
    FREE_SPEECH = "free_speech"
    SPELLING = "spelling"
    TRANSLATION = "translation"


@dataclass
class Language:
    code: str
    name: str
    native_name: str
    dir: str  # 'rtl' or 'ltr'


LANGUAGES = {
    'hebrew': Language('he-IL', 'Hebrew', 'עברית', 'rtl'),
    'english': Language('en-US', 'English', 'English', 'ltr'),
}

# Hebrew letter names for spelling mode
HEBREW_LETTER_NAMES = {
    'א': 'אָלֶף', 'ב': 'בֵּית', 'ג': 'גִּימֶל', 'ד': 'דָּלֶת', 'ה': 'הֵא',
    'ו': 'וָו', 'ז': 'זַיִן', 'ח': 'חֵית', 'ט': 'טֵית', 'י': 'יוֹד',
    'כ': 'כָּף', 'ך': 'כָּף סוֹפִית', 'ל': 'לָמֶד', 'מ': 'מֵם', 'ם': 'מֵם סוֹפִית',
    'נ': 'נוּן', 'ן': 'נוּן סוֹפִית', 'ס': 'סָמֶך', 'ע': 'עַיִן', 'פ': 'פֵּא',
    'ף': 'פֵּא סוֹפִית', 'צ': 'צָדִי', 'ץ': 'צָדִי סוֹפִית', 'ק': 'קוֹף',
    'ר': 'רֵישׁ', 'ש': 'שִׁין', 'ת': 'תָּו'
}

# UI Text for each language
UI_TEXT = {
    'hebrew': {
        'SELECT_MODE': 'בחר משחק',
        'FREE_SPEECH': 'דיבור חופשי',
        'SPELLING': 'איות',
        'TRANSLATION': 'תרגום',
        'TRANSLATING': 'מתרגם...',
        'TRANSLATE_TO': 'אמור משהו בעברית לתרגום',
        'TRANSLATION_ERROR': 'שגיאת תרגום',
        'BACK': '← חזרה',
        'TAP_TO_SPEAK': 'לחץ לדבר!',
        'RECORDING': 'מקליט... (לחץ לעצירה)',
        'PROCESSING': 'מעבד...',
        'LISTENING': 'מקשיב...',
        'THINKING': 'חושב...',
        'SAY_SOMETHING': 'אמור משהו בעברית!',
        'NOT_UNDERSTOOD': 'לא הבנתי',
        'NETWORK_ERROR': 'שגיאת רשת',
        'ERROR': 'שגיאה',
        'CONTINUOUS': 'רצף',
        'CONTINUOUS_ON': 'רצף פעיל',
    },
    'english': {
        'SELECT_MODE': 'Select Game',
        'FREE_SPEECH': 'Free Speech',
        'SPELLING': 'Spelling',
        'TRANSLATION': 'Translation',
        'TRANSLATING': 'Translating...',
        'TRANSLATE_TO': 'Say something to translate',
        'TRANSLATION_ERROR': 'Translation error',
        'BACK': '← Back',
        'TAP_TO_SPEAK': 'Tap to Speak!',
        'RECORDING': 'Recording... (tap to stop)',
        'PROCESSING': 'Processing...',
        'LISTENING': 'Listening...',
        'THINKING': 'Thinking...',
        'SAY_SOMETHING': 'Say something in English!',
        'NOT_UNDERSTOOD': "Didn't understand",
        'NETWORK_ERROR': 'Network error',
        'ERROR': 'Error',
        'CONTINUOUS': 'Loop',
        'CONTINUOUS_ON': 'Loop Active',
    }
}


# ===========================================
# HELPER FUNCTIONS
# ===========================================
def strip_niqqud(text: str) -> str:
    """Remove Hebrew niqqud (vowel marks)."""
    return re.sub(r'[\u0591-\u05C7]', '', text)


def prepare_hebrew_text(text: str) -> str:
    """Prepare Hebrew text for display."""
    text = strip_niqqud(text)
    return get_display(text)


# ===========================================
# MAIN APP CLASS
# ===========================================
class HebrewVoiceApp:
    def __init__(self):
        # Display setup
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        pygame.display.set_caption("Hebrew Voice Game")
        pygame.mouse.set_visible(False)

        # Font setup
        self.font_path = self._find_hebrew_font()
        log.info(f"Using font: {self.font_path}")
        base_size = int(SCREEN_HEIGHT * 0.12)
        self.large_font = pygame.font.Font(self.font_path, base_size)
        self.medium_font = pygame.font.Font(self.font_path, int(base_size * 0.5))
        self.small_font = pygame.font.Font(self.font_path, int(base_size * 0.35))
        self.button_font = pygame.font.Font(self.font_path, int(base_size * 0.4))

        # State
        self.state = AppState.MODE_SELECT
        self.current_lang = 'hebrew'
        self.current_mode: Optional[GameMode] = None
        self.recognized_text = ""
        self.last_recognized_text = ""
        self.translation_original = ""  # Store original text in translation mode

        # Recording state
        self.is_recording_active = False
        self.stop_recording_flag = False

        # Continuous mode
        self.continuous_mode = False
        self.tts_playing = False
        self.pending_restart_listening = False

        # Audio
        self.audio = pyaudio.PyAudio()
        self.temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        self.temp_tts = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
        self.recognizer = sr.Recognizer()

        # UI elements
        self._setup_ui_rects()

        # Animation
        self.animation_frame = 0
        self.clock = pygame.time.Clock()

        # Load words data
        self.words_data = self._load_words_data()
        
        # Spelling Bee game state
        self.spelling_game = {
            'difficulty': None,
            'current_word': None,
            'target_word': None,
            'user_spelling': [],
            'word_list': [],
            'score': 0
        }

    def _find_hebrew_font(self) -> str:
        """Find a font that supports Hebrew."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansHebrew-Bold.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return None

    def _load_words_data(self) -> dict:
        """Load words from words.json file."""
        try:
            words_path = os.path.join(os.path.dirname(__file__), 'words.json')
            with open(words_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log.info("Words data loaded successfully")
                return data
        except Exception as e:
            log.error(f"Failed to load words.json: {e}")
            return DEFAULT_WORDS_DATA.copy()

    def _setup_ui_rects(self):
        """Set up UI element rectangles."""
        margin = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.04)
        button_height = int(SCREEN_HEIGHT * 0.22)

        # Mode selection buttons
        mode_gap = int(SCREEN_HEIGHT * 0.03)
        mode_button_height = int((SCREEN_HEIGHT - margin * 4 - mode_gap * 2 - SCREEN_HEIGHT * 0.12) / 3)

        self.mode_buttons = {
            GameMode.FREE_SPEECH: pygame.Rect(
                margin, int(SCREEN_HEIGHT * 0.15),
                SCREEN_WIDTH - margin * 2, mode_button_height
            ),
            GameMode.SPELLING: pygame.Rect(
                margin, int(SCREEN_HEIGHT * 0.15) + mode_button_height + mode_gap,
                SCREEN_WIDTH - margin * 2, mode_button_height
            ),
            GameMode.TRANSLATION: pygame.Rect(
                margin, int(SCREEN_HEIGHT * 0.15) + (mode_button_height + mode_gap) * 2,
                SCREEN_WIDTH - margin * 2, mode_button_height
            ),
        }

        # Game screen elements
        self.back_button_rect = pygame.Rect(margin, margin, int(SCREEN_WIDTH * 0.25), int(SCREEN_HEIGHT * 0.08))

        # Continuous mode button (circular, between back button and language toggle)
        continuous_size = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.08)
        self.continuous_btn_rect = pygame.Rect(
            self.back_button_rect.right + margin,
            margin + (int(SCREEN_HEIGHT * 0.08) - continuous_size) // 2,
            continuous_size, continuous_size
        )

        # Language toggle
        toggle_width = int(SCREEN_WIDTH * 0.4)
        toggle_height = int(SCREEN_HEIGHT * 0.08)
        self.lang_toggle_rect = pygame.Rect(
            SCREEN_WIDTH - margin - toggle_width, margin,
            toggle_width, toggle_height
        )
        self.hebrew_btn_rect = pygame.Rect(
            self.lang_toggle_rect.x + 4, self.lang_toggle_rect.y + 4,
            (toggle_width - 8) // 2, toggle_height - 8
        )
        self.english_btn_rect = pygame.Rect(
            self.lang_toggle_rect.x + 4 + (toggle_width - 8) // 2,
            self.lang_toggle_rect.y + 4,
            (toggle_width - 8) // 2, toggle_height - 8
        )

        # Display area
        top_bar_height = int(SCREEN_HEIGHT * 0.12)
        self.display_rect = pygame.Rect(
            margin, top_bar_height + margin,
            SCREEN_WIDTH - margin * 2,
            SCREEN_HEIGHT - top_bar_height - button_height - margin * 3
        )

        # Speaker button
        speaker_size = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.1)
        self.speaker_btn_rect = pygame.Rect(
            self.display_rect.right - speaker_size - 10,
            self.display_rect.top + 10,
            speaker_size, speaker_size
        )

        # Main button
        self.main_button_rect = pygame.Rect(
            margin, SCREEN_HEIGHT - button_height - margin,
            SCREEN_WIDTH - margin * 2, button_height
        )
        
        # Difficulty selector buttons for spelling mode
        difficulty_btn_width = int(SCREEN_WIDTH * 0.28)
        difficulty_btn_height = int(SCREEN_HEIGHT * 0.12)
        difficulty_gap = int(SCREEN_WIDTH * 0.04)
        difficulty_start_x = (SCREEN_WIDTH - (difficulty_btn_width * 3 + difficulty_gap * 2)) // 2
        difficulty_y = self.display_rect.centery - difficulty_btn_height // 2
        
        self.difficulty_buttons = {
            'easy': pygame.Rect(difficulty_start_x, difficulty_y, difficulty_btn_width, difficulty_btn_height),
            'medium': pygame.Rect(difficulty_start_x + difficulty_btn_width + difficulty_gap, difficulty_y, 
                                 difficulty_btn_width, difficulty_btn_height),
            'hard': pygame.Rect(difficulty_start_x + (difficulty_btn_width + difficulty_gap) * 2, difficulty_y,
                               difficulty_btn_width, difficulty_btn_height)
        }
        
        # Game control buttons (Repeat, Next) for spelling mode
        game_btn_width = int(SCREEN_WIDTH * 0.35)
        game_btn_height = int(SCREEN_HEIGHT * 0.08)
        game_btn_gap = int(SCREEN_WIDTH * 0.05)
        game_btn_start_x = (SCREEN_WIDTH - (game_btn_width * 2 + game_btn_gap)) // 2
        game_btn_y = self.display_rect.bottom - game_btn_height - 10
        
        self.repeat_btn_rect = pygame.Rect(game_btn_start_x, game_btn_y, game_btn_width, game_btn_height)
        self.next_btn_rect = pygame.Rect(game_btn_start_x + game_btn_width + game_btn_gap, game_btn_y,
                                         game_btn_width, game_btn_height)

    def get_text(self, key: str) -> str:
        """Get UI text for current language."""
        return UI_TEXT[self.current_lang].get(key, key)

    def set_language(self, lang: str):
        """Change the current language."""
        if lang in LANGUAGES:
            self.current_lang = lang
            log.info(f"Language changed to: {lang}")
            if self.state not in [AppState.MODE_SELECT]:
                self.state = AppState.READY
                self.recognized_text = ""

    def _toggle_continuous_mode(self):
        """Toggle continuous (eyes-free) mode."""
        self.continuous_mode = not self.continuous_mode
        log.info(f"Continuous mode: {self.continuous_mode}")

        if self.continuous_mode and self.state in [AppState.READY, AppState.SHOWING]:
            # Start listening immediately when enabling continuous mode
            self._record_audio()
        elif not self.continuous_mode and self.is_recording_active:
            # Stop if we're currently recording
            self._stop_recording()

    # ===========================================
    # TEXT-TO-SPEECH
    # ===========================================
    def speak_text(self, text: str = None, restart_after: bool = False):
        """Speak the given text or last recognized text."""
        if not HAS_GTTS:
            log.warning("gTTS not available")
            if restart_after and self.continuous_mode:
                self.pending_restart_listening = True
            return

        text = text or self.last_recognized_text
        if not text:
            if restart_after and self.continuous_mode:
                self.pending_restart_listening = True
            return

        def speak():
            try:
                self.tts_playing = True
                lang_code = 'he' if self.current_lang == 'hebrew' else 'en'
                tts = gTTS(text=text, lang=lang_code, slow=True)
                tts.save(self.temp_tts)
                pygame.mixer.music.load(self.temp_tts)
                pygame.mixer.music.play()
                log.info(f"Speaking: {text}")

                # Wait for TTS to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(50)

                self.tts_playing = False

                # Schedule restart if continuous mode
                if restart_after and self.continuous_mode:
                    pygame.time.wait(500)  # Short pause before restart
                    self.pending_restart_listening = True
                    log.info("Continuous mode: scheduling restart after TTS")

            except Exception as e:
                log.error(f"TTS error: {e}")
                self.tts_playing = False
                if restart_after and self.continuous_mode:
                    self.pending_restart_listening = True

        threading.Thread(target=speak, daemon=True).start()

    def speak_and_spell(self, text: str = None, restart_after: bool = False):
        """Speak each word and then spell it letter by letter."""
        if not HAS_GTTS:
            log.warning("gTTS not available for spelling")
            if restart_after and self.continuous_mode:
                self.pending_restart_listening = True
            return

        text = text or self.last_recognized_text
        if not text:
            if restart_after and self.continuous_mode:
                self.pending_restart_listening = True
            return

        def spell():
            try:
                self.tts_playing = True
                lang_code = 'he' if self.current_lang == 'hebrew' else 'en'
                is_hebrew = self.current_lang == 'hebrew'
                words = text.split()

                for word in words:
                    # Wait for any previous audio to finish
                    while pygame.mixer.music.get_busy():
                        pygame.time.wait(50)

                    # Say the whole word
                    try:
                        tts = gTTS(text=word, lang=lang_code, slow=True)
                        tts.save(self.temp_tts)
                        pygame.mixer.music.load(self.temp_tts)
                        pygame.mixer.music.play()
                        log.info(f"Speaking word: {word}")
                        while pygame.mixer.music.get_busy():
                            pygame.time.wait(50)
                    except Exception as e:
                        log.error(f"TTS error for word '{word}': {e}")

                    # Small pause after word
                    pygame.time.wait(300)

                    # Spell each letter
                    for letter in word:
                        if is_hebrew and letter in HEBREW_LETTER_NAMES:
                            letter_name = HEBREW_LETTER_NAMES[letter]
                        else:
                            letter_name = letter.upper()

                        try:
                            tts = gTTS(text=letter_name, lang=lang_code, slow=True)
                            tts.save(self.temp_tts)
                            pygame.mixer.music.load(self.temp_tts)
                            pygame.mixer.music.play()
                            log.info(f"Spelling letter: {letter} -> {letter_name}")
                            while pygame.mixer.music.get_busy():
                                pygame.time.wait(50)
                            # Small pause between letters
                            pygame.time.wait(200)
                        except Exception as e:
                            log.error(f"TTS error for letter '{letter}': {e}")

                    # Pause between words
                    pygame.time.wait(500)

                log.info("Finished spelling")
                self.tts_playing = False

                # Schedule restart if continuous mode
                if restart_after and self.continuous_mode:
                    pygame.time.wait(500)  # Short pause before restart
                    self.pending_restart_listening = True
                    log.info("Continuous mode: scheduling restart after spelling")

            except Exception as e:
                log.error(f"Spell error: {e}")
                self.tts_playing = False
                if restart_after and self.continuous_mode:
                    self.pending_restart_listening = True

        threading.Thread(target=spell, daemon=True).start()

    # ===========================================
    # TRANSLATION
    # ===========================================
    def translate_text(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """Translate text using MyMemory free API."""
        try:
            url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair={from_lang}|{to_lang}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('responseStatus') == 200 and data.get('responseData'):
                translation = data['responseData'].get('translatedText')
                log.info(f"Translated '{text}' -> '{translation}'")
                return translation
            else:
                log.error(f"Translation API error: {data}")
                return None
        except Exception as e:
            log.error(f"Translation error: {e}")
            return None

    def speak_in_language(self, text: str, lang_code: str, restart_after: bool = False):
        """Speak text in a specific language (not necessarily current language)."""
        if not HAS_GTTS:
            log.warning("gTTS not available")
            if restart_after and self.continuous_mode:
                self.pending_restart_listening = True
            return

        if not text:
            if restart_after and self.continuous_mode:
                self.pending_restart_listening = True
            return

        def speak():
            try:
                self.tts_playing = True
                tts = gTTS(text=text, lang=lang_code, slow=True)
                tts.save(self.temp_tts)
                pygame.mixer.music.load(self.temp_tts)
                pygame.mixer.music.play()
                log.info(f"Speaking in {lang_code}: {text}")

                # Wait for TTS to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(50)

                self.tts_playing = False

                # Schedule restart if continuous mode
                if restart_after and self.continuous_mode:
                    pygame.time.wait(500)
                    self.pending_restart_listening = True
                    log.info("Continuous mode: scheduling restart after TTS")

            except Exception as e:
                log.error(f"TTS error: {e}")
                self.tts_playing = False
                if restart_after and self.continuous_mode:
                    self.pending_restart_listening = True

        threading.Thread(target=speak, daemon=True).start()

    # ===========================================
    # SPELLING BEE GAME
    # ===========================================
    def select_difficulty(self, difficulty: str):
        """Select difficulty and start spelling game."""
        if not self.words_data:
            log.error("Words data not loaded")
            return
        
        lang_key = self.current_lang
        # Validate that the language exists in words_data
        if (lang_key not in self.words_data.get('spelling', {}) or 
            difficulty not in self.words_data['spelling'][lang_key]):
            log.error(f"No words available for {lang_key}/{difficulty}")
            return
        
        word_list = self.words_data['spelling'][lang_key][difficulty]
        
        if not word_list:
            log.error(f"Empty word list for {difficulty}")
            return
        
        self.spelling_game['difficulty'] = difficulty
        self.spelling_game['word_list'] = word_list
        log.info(f"Selected difficulty: {difficulty}, {len(word_list)} words available")
        
        # Start first word
        self.next_word()
    
    def next_word(self):
        """Pick a random word and speak it."""
        if not self.spelling_game['word_list']:
            log.error("No words in word list")
            return
        
        # Pick random word
        word = random.choice(self.spelling_game['word_list'])
        self.spelling_game['target_word'] = word
        self.spelling_game['current_word'] = word
        self.spelling_game['user_spelling'] = []
        
        log.info(f"Next word: {word}")
        
        # Speak the word
        self.recognized_text = "👂 " + (self.get_text('LISTENING') if self.current_lang == 'hebrew' else 'Listen...')
        self.state = AppState.SHOWING
        
        def after_speak():
            # After speaking, show instruction
            if self.current_lang == 'hebrew':
                self.recognized_text = 'עכשיו אתה! אות אחר אות'
            else:
                self.recognized_text = 'Your turn! Spell it letter by letter'
            self.state = AppState.READY
        
        # Speak in a thread and then update
        def speak_word():
            try:
                if HAS_GTTS:
                    lang_code = 'he' if self.current_lang == 'hebrew' else 'en'
                    tts = gTTS(text=word, lang=lang_code, slow=True)
                    tts.save(self.temp_tts)
                    pygame.mixer.music.load(self.temp_tts)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.wait(50)
                after_speak()
            except Exception as e:
                log.error(f"TTS error in next_word: {e}")
                after_speak()
        
        threading.Thread(target=speak_word, daemon=True).start()
    
    def repeat_word(self):
        """Repeat the current word."""
        if not self.spelling_game['target_word']:
            return
        
        word = self.spelling_game['target_word']
        self.recognized_text = "👂 " + (self.get_text('LISTENING') if self.current_lang == 'hebrew' else 'Listen...')
        
        def after_speak():
            if self.current_lang == 'hebrew':
                self.recognized_text = 'עכשיו אתה! אות אחר אות'
            else:
                self.recognized_text = 'Your turn! Spell it letter by letter'
        
        def speak_word():
            try:
                if HAS_GTTS:
                    lang_code = 'he' if self.current_lang == 'hebrew' else 'en'
                    tts = gTTS(text=word, lang=lang_code, slow=True)
                    tts.save(self.temp_tts)
                    pygame.mixer.music.load(self.temp_tts)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.wait(50)
                after_speak()
            except Exception as e:
                log.error(f"TTS error in repeat_word: {e}")
                after_speak()
        
        threading.Thread(target=speak_word, daemon=True).start()
    
    def check_spelling(self, spoken_text: str):
        """Check if spoken letter matches target word."""
        if not self.spelling_game['target_word']:
            return
        
        normalized = spoken_text.strip().lower()
        target_word = self.spelling_game['target_word']
        target_letters = list(target_word.lower())
        matched_index = -1
        
        # Track filled positions
        filled_positions = set()
        for entry in self.spelling_game['user_spelling']:
            if 'position' in entry:
                filled_positions.add(entry['position'])
        
        # For Hebrew, check against letter names
        if self.current_lang == 'hebrew':
            for letter, name in HEBREW_LETTER_NAMES.items():
                # Strip niqqud from name for comparison
                name_stripped = strip_niqqud(name).lower()
                # Check for exact match (with or without niqqud) or if the letter itself is spoken
                if normalized == name_stripped or normalized == name.lower() or normalized == letter:
                    # Find first unfilled position for this letter
                    for i in range(len(target_letters)):
                        if i not in filled_positions and target_letters[i] == letter.lower():
                            matched_index = i
                            self.spelling_game['user_spelling'].append({
                                'char': letter, 
                                'correct': True,
                                'position': i
                            })
                            break
                    break
        else:
            # For English, check if it's a single letter
            if len(normalized) == 1 and normalized.isalpha():
                # Find first unfilled position for this letter
                for i in range(len(target_letters)):
                    if i not in filled_positions and target_letters[i] == normalized:
                        matched_index = i
                        self.spelling_game['user_spelling'].append({
                            'char': normalized,
                            'correct': True,
                            'position': i
                        })
                        break
        
        if matched_index >= 0:
            # Correct letter!
            # Check if word is complete
            if len(self.spelling_game['user_spelling']) == len(target_letters):
                # Word completed!
                self.recognized_text = '🎉 ' + ('מצוין! מילה נכונה!' if self.current_lang == 'hebrew' else 'Excellent! Correct!')
                self.last_recognized_text = 'מצוין' if self.current_lang == 'hebrew' else 'Excellent'
                self.state = AppState.SHOWING
                
                # Speak success and auto-next
                def success_flow():
                    try:
                        if HAS_GTTS:
                            lang_code = 'he' if self.current_lang == 'hebrew' else 'en'
                            text = 'מצוין' if self.current_lang == 'hebrew' else 'Excellent'
                            tts = gTTS(text=text, lang=lang_code, slow=True)
                            tts.save(self.temp_tts)
                            pygame.mixer.music.load(self.temp_tts)
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.wait(50)
                        pygame.time.wait(2000)
                        self.next_word()
                    except Exception as e:
                        log.error(f"Success flow error: {e}")
                        pygame.time.wait(2000)
                        self.next_word()
                
                threading.Thread(target=success_flow, daemon=True).start()
            else:
                # Continue spelling
                self.recognized_text = ('נכון! ✓ המשך...' if self.current_lang == 'hebrew' 
                                       else 'Correct! ✓ Continue...')
                self.state = AppState.READY
        else:
            # Incorrect
            self.recognized_text = '❌ ' + ('נסה שוב' if self.current_lang == 'hebrew' else 'Try again')
            self.state = AppState.READY

    # ===========================================
    # RECORDING
    # ===========================================
    def _record_audio(self):
        """Record audio with manual stop or auto-stop."""
        self.state = AppState.RECORDING
        self.is_recording_active = True
        self.stop_recording_flag = False
        log.info("Recording started...")

        def record():
            try:
                stream = self.audio.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RECORD_SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=CHUNK
                )

                frames = []
                max_chunks = int(RECORD_SAMPLE_RATE / CHUNK * MAX_RECORDING_TIME)

                for _ in range(max_chunks):
                    if self.stop_recording_flag or self.state != AppState.RECORDING:
                        log.info("Recording stopped")
                        break
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)

                stream.stop_stream()
                stream.close()
                self.is_recording_active = False
                self.stop_recording_flag = False

                if len(frames) > 0:
                    wf = wave.open(self.temp_wav, 'wb')
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(self.audio.get_sample_size(FORMAT))
                    wf.setframerate(RECORD_SAMPLE_RATE)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    log.info(f"Recording finished ({len(frames)} chunks)")
                    self._process_audio()
                else:
                    self.recognized_text = self.get_text('NOT_UNDERSTOOD')
                    self.state = AppState.SHOWING

            except Exception as e:
                log.error(f"Recording error: {e}")
                self.is_recording_active = False
                self.state = AppState.READY

        threading.Thread(target=record, daemon=True).start()

    def _stop_recording(self):
        """Stop current recording."""
        if self.is_recording_active:
            log.info("Stopping recording...")
            self.stop_recording_flag = True

    def _process_audio(self):
        """Process recorded audio with Google Speech Recognition."""
        self.state = AppState.PROCESSING

        def process():
            try:
                with sr.AudioFile(self.temp_wav) as source:
                    audio_data = self.recognizer.record(source)

                lang_code = LANGUAGES[self.current_lang].code
                log.info(f"Sending to Google Speech API ({lang_code})...")
                text = self.recognizer.recognize_google(audio_data, language=lang_code)
                self.recognized_text = text if text else "..."
                self.last_recognized_text = self.recognized_text
                log.info(f"Recognized: {self.recognized_text}")

            except sr.UnknownValueError:
                self.recognized_text = self.get_text('NOT_UNDERSTOOD')
                self.last_recognized_text = ""
                log.warning("Could not understand audio")
            except sr.RequestError as e:
                self.recognized_text = self.get_text('NETWORK_ERROR')
                self.last_recognized_text = ""
                log.error(f"Network error: {e}")
            except Exception as e:
                self.recognized_text = self.get_text('ERROR')
                self.last_recognized_text = ""
                log.exception(f"Processing error: {e}")

            # Handle translation mode
            if self.current_mode == GameMode.TRANSLATION and self.last_recognized_text:
                self._handle_translation(self.last_recognized_text)
                return

            # Handle spelling mode
            if self.current_mode == GameMode.SPELLING and self.last_recognized_text:
                self.check_spelling(self.last_recognized_text)
                return

            self.state = AppState.SHOWING

            # In continuous mode for free speech, speak the result then restart
            if self.current_mode == GameMode.FREE_SPEECH and self.continuous_mode and self.last_recognized_text:
                pygame.time.wait(300)
                self.speak_text(restart_after=True)
            elif self.continuous_mode and not self.last_recognized_text:
                # Error case in continuous mode - restart listening after delay
                pygame.time.wait(1000)
                self.pending_restart_listening = True

        threading.Thread(target=process, daemon=True).start()

    def _handle_translation(self, spoken_text: str):
        """Handle translation of recognized speech."""
        # Show translating state
        self.recognized_text = self.get_text('TRANSLATING')

        # Determine source and target languages
        from_lang = 'he' if self.current_lang == 'hebrew' else 'en'
        to_lang = 'en' if self.current_lang == 'hebrew' else 'he'

        # Translate
        translation = self.translate_text(spoken_text, from_lang, to_lang)

        if translation:
            # Show original + translation
            self.recognized_text = translation
            self.last_recognized_text = translation
            self.translation_original = spoken_text  # Store original for display
            self.state = AppState.SHOWING

            # Speak the translation in target language
            pygame.time.wait(300)
            self.speak_in_language(translation, to_lang, restart_after=self.continuous_mode)
        else:
            self.recognized_text = self.get_text('TRANSLATION_ERROR')
            self.last_recognized_text = ""
            self.state = AppState.SHOWING

            if self.continuous_mode:
                pygame.time.wait(1000)
                self.pending_restart_listening = True

    # ===========================================
    # DRAWING
    # ===========================================
    def _render_text(self, text: str, font: pygame.font.Font, color: tuple) -> pygame.Surface:
        """Render text with RTL support for Hebrew."""
        if self.current_lang == 'hebrew':
            text = prepare_hebrew_text(text)
        return font.render(text, True, color)

    def _draw_mode_select(self):
        """Draw mode selection screen."""
        # Title
        title = self.get_text('SELECT_MODE')
        title_surface = self._render_text(title, self.medium_font, BRIGHT_BLUE)
        title_rect = title_surface.get_rect(centerx=SCREEN_WIDTH // 2, top=int(SCREEN_HEIGHT * 0.05))
        self.screen.blit(title_surface, title_rect)

        # Mode buttons
        mode_configs = [
            (GameMode.FREE_SPEECH, BRIGHT_GREEN, 'FREE_SPEECH', True),
            (GameMode.SPELLING, CORAL, 'SPELLING', True),
            (GameMode.TRANSLATION, TEAL, 'TRANSLATION', True),
        ]

        for mode, color, text_key, enabled in mode_configs:
            rect = self.mode_buttons[mode]

            # Shadow
            shadow_rect = rect.copy()
            shadow_rect.move_ip(6, 6)
            pygame.draw.rect(self.screen, (100, 100, 100), shadow_rect, border_radius=30)

            # Button
            pygame.draw.rect(self.screen, color, rect, border_radius=30)
            pygame.draw.rect(self.screen, WHITE, rect, width=4, border_radius=30)

            # Text
            btn_text = self.get_text(text_key)
            text_surface = self._render_text(btn_text, self.button_font, WHITE)
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)

    def _draw_game_screen(self):
        """Draw the game screen."""
        # Back button
        pygame.draw.rect(self.screen, BRIGHT_BLUE, self.back_button_rect, border_radius=15)
        back_text = self._render_text(self.get_text('BACK'), self.small_font, WHITE)
        back_rect = back_text.get_rect(center=self.back_button_rect.center)
        self.screen.blit(back_text, back_rect)

        # Language toggle background
        pygame.draw.rect(self.screen, WHITE, self.lang_toggle_rect, border_radius=25)

        # Hebrew button
        he_color = BRIGHT_BLUE if self.current_lang == 'hebrew' else (220, 220, 220)
        he_text_color = WHITE if self.current_lang == 'hebrew' else (100, 100, 100)
        pygame.draw.rect(self.screen, he_color, self.hebrew_btn_rect, border_radius=20)
        he_text = self._render_text('עברית', self.small_font, he_text_color)
        he_rect = he_text.get_rect(center=self.hebrew_btn_rect.center)
        self.screen.blit(he_text, he_rect)

        # English button
        en_color = BRIGHT_BLUE if self.current_lang == 'english' else (220, 220, 220)
        en_text_color = WHITE if self.current_lang == 'english' else (100, 100, 100)
        pygame.draw.rect(self.screen, en_color, self.english_btn_rect, border_radius=20)
        en_text = self.small_font.render('English', True, en_text_color)
        en_rect = en_text.get_rect(center=self.english_btn_rect.center)
        self.screen.blit(en_text, en_rect)

        # Continuous mode button
        if self.continuous_mode:
            # Active state - filled purple with pulse animation
            pulse_scale = 1.0 + 0.05 * abs(30 - (self.animation_frame % 60)) / 30
            pulse_rect = self.continuous_btn_rect.inflate(
                int(self.continuous_btn_rect.width * (pulse_scale - 1)),
                int(self.continuous_btn_rect.height * (pulse_scale - 1))
            )
            pygame.draw.circle(self.screen, PURPLE, pulse_rect.center, pulse_rect.width // 2)
            cont_text = self.small_font.render('∞', True, WHITE)
        else:
            # Inactive state - outline only
            pygame.draw.circle(self.screen, PURPLE, self.continuous_btn_rect.center,
                             self.continuous_btn_rect.width // 2, width=3)
            cont_text = self.small_font.render('∞', True, PURPLE)
        cont_rect = cont_text.get_rect(center=self.continuous_btn_rect.center)
        self.screen.blit(cont_text, cont_rect)

        # Display area
        pygame.draw.rect(self.screen, WHITE, self.display_rect, border_radius=30)
        pygame.draw.rect(self.screen, BRIGHT_BLUE, self.display_rect, width=5, border_radius=30)

        # Display text
        if self.state == AppState.SHOWING and self.recognized_text:
            display_text = self.recognized_text
            text_color = BLACK
        elif self.state == AppState.RECORDING:
            display_text = self.get_text('LISTENING')
            text_color = BRIGHT_RED
        elif self.state == AppState.PROCESSING:
            display_text = self.get_text('THINKING')
            text_color = BRIGHT_YELLOW
        else:
            # Show appropriate prompt based on mode
            if self.current_mode == GameMode.TRANSLATION:
                display_text = self.get_text('TRANSLATE_TO')
            else:
                display_text = self.get_text('SAY_SOMETHING')
            text_color = BRIGHT_BLUE

        # In translation mode showing results, display original above translation
        if (self.current_mode == GameMode.TRANSLATION and
            self.state == AppState.SHOWING and
            self.translation_original and self.recognized_text):
            # Draw original text (smaller, gray)
            orig_font = pygame.font.Font(self.font_path, int(SCREEN_HEIGHT * 0.05))
            orig_surface = self._render_text(self.translation_original, orig_font, GRAY)
            orig_rect = orig_surface.get_rect(centerx=self.display_rect.centerx,
                                               top=self.display_rect.top + 20)
            self.screen.blit(orig_surface, orig_rect)

            # Draw translation (main text, centered below)
            font_size = int(SCREEN_HEIGHT * 0.12)
            while font_size > int(SCREEN_HEIGHT * 0.05):
                font = pygame.font.Font(self.font_path, font_size)
                text_surface = self._render_text(display_text, font, text_color)
                if text_surface.get_width() < self.display_rect.width - 60:
                    break
                font_size -= 10
            text_rect = text_surface.get_rect(centerx=self.display_rect.centerx,
                                               centery=self.display_rect.centery + 20)
            self.screen.blit(text_surface, text_rect)
        else:
            # Normal display - fit text to display
            font_size = int(SCREEN_HEIGHT * 0.15)
            while font_size > int(SCREEN_HEIGHT * 0.05):
                font = pygame.font.Font(self.font_path, font_size)
                text_surface = self._render_text(display_text, font, text_color)
                if text_surface.get_width() < self.display_rect.width - 60:
                    break
                font_size -= 10

            text_rect = text_surface.get_rect(center=self.display_rect.center)
            self.screen.blit(text_surface, text_rect)

        # Speaker button (only when showing recognized text)
        if self.state == AppState.SHOWING and self.last_recognized_text and HAS_GTTS:
            pygame.draw.circle(
                self.screen, BRIGHT_BLUE,
                self.speaker_btn_rect.center,
                self.speaker_btn_rect.width // 2
            )
            speaker_text = self.small_font.render('🔊', True, WHITE)
            speaker_rect = speaker_text.get_rect(center=self.speaker_btn_rect.center)
            self.screen.blit(speaker_text, speaker_rect)

        # Spelling mode: Show difficulty selector or game controls
        if self.current_mode == GameMode.SPELLING:
            if self.spelling_game['difficulty'] is None:
                # Show difficulty selector
                difficulty_configs = [
                    ('easy', BRIGHT_GREEN, '🟢 ' + ('קל' if self.current_lang == 'hebrew' else 'Easy')),
                    ('medium', BRIGHT_YELLOW, '🟡 ' + ('בינוני' if self.current_lang == 'hebrew' else 'Medium')),
                    ('hard', BRIGHT_RED, '🔴 ' + ('קשה' if self.current_lang == 'hebrew' else 'Hard'))
                ]
                
                for difficulty, color, label in difficulty_configs:
                    rect = self.difficulty_buttons[difficulty]
                    # Shadow
                    shadow = rect.copy()
                    shadow.move_ip(4, 4)
                    pygame.draw.rect(self.screen, (100, 100, 100), shadow, border_radius=20)
                    # Button
                    pygame.draw.rect(self.screen, color, rect, border_radius=20)
                    pygame.draw.rect(self.screen, WHITE, rect, width=3, border_radius=20)
                    # Text
                    text_surface = self._render_text(label, self.small_font, WHITE)
                    text_rect = text_surface.get_rect(center=rect.center)
                    self.screen.blit(text_surface, text_rect)
                
                # Show prompt in display area
                prompt = 'בחר רמת קושי' if self.current_lang == 'hebrew' else 'Select Difficulty'
                font = pygame.font.Font(self.font_path, int(SCREEN_HEIGHT * 0.08))
                prompt_surface = self._render_text(prompt, font, BRIGHT_BLUE)
                prompt_rect = prompt_surface.get_rect(center=(self.display_rect.centerx, 
                                                              self.display_rect.top + int(SCREEN_HEIGHT * 0.1)))
                self.screen.blit(prompt_surface, prompt_rect)
            else:
                # Show spelling letter boxes
                if self.spelling_game['target_word']:
                    letters = list(self.spelling_game['target_word'])
                    user_spelling = self.spelling_game['user_spelling']
                    
                    # Calculate letter box layout
                    box_size = min(int(SCREEN_WIDTH * 0.12), int(SCREEN_HEIGHT * 0.08))
                    gap = int(box_size * 0.2)
                    total_width = len(letters) * box_size + (len(letters) - 1) * gap
                    start_x = self.display_rect.centerx - total_width // 2
                    box_y = self.display_rect.centery + int(SCREEN_HEIGHT * 0.05)
                    
                    for i, letter in enumerate(letters):
                        x = start_x + i * (box_size + gap)
                        box_rect = pygame.Rect(x, box_y, box_size, box_size)
                        
                        # Determine box color
                        if i < len(user_spelling):
                            # Letter has been spoken
                            if user_spelling[i]['correct']:
                                box_color = BRIGHT_GREEN
                            else:
                                box_color = BRIGHT_RED
                            display_char = user_spelling[i]['char']
                        else:
                            # Not yet filled
                            box_color = GRAY
                            display_char = '_'
                        
                        # Draw box
                        pygame.draw.rect(self.screen, box_color, box_rect, border_radius=10)
                        pygame.draw.rect(self.screen, WHITE, box_rect, width=3, border_radius=10)
                        
                        # Draw letter
                        letter_font = pygame.font.Font(self.font_path, int(box_size * 0.6))
                        letter_surface = self._render_text(display_char, letter_font, WHITE)
                        letter_rect = letter_surface.get_rect(center=box_rect.center)
                        self.screen.blit(letter_surface, letter_rect)
                
                # Show game control buttons (Repeat, Next)
                # Repeat button
                pygame.draw.rect(self.screen, BRIGHT_BLUE, self.repeat_btn_rect, border_radius=15)
                pygame.draw.rect(self.screen, WHITE, self.repeat_btn_rect, width=3, border_radius=15)
                repeat_text = '🔁 ' + ('חזור' if self.current_lang == 'hebrew' else 'Repeat')
                repeat_surface = self._render_text(repeat_text, self.small_font, WHITE)
                repeat_rect = repeat_surface.get_rect(center=self.repeat_btn_rect.center)
                self.screen.blit(repeat_surface, repeat_rect)
                
                # Next button
                pygame.draw.rect(self.screen, TEAL, self.next_btn_rect, border_radius=15)
                pygame.draw.rect(self.screen, WHITE, self.next_btn_rect, width=3, border_radius=15)
                next_text = '⏭️ ' + ('הבא' if self.current_lang == 'hebrew' else 'Next')
                next_surface = self._render_text(next_text, self.small_font, WHITE)
                next_rect = next_surface.get_rect(center=self.next_btn_rect.center)
                self.screen.blit(next_surface, next_rect)

        # Main button (hide in spelling mode when showing difficulty selector)
        show_main_button = not (self.current_mode == GameMode.SPELLING and 
                                self.spelling_game['difficulty'] is None)
        
        if show_main_button:
            if self.state == AppState.RECORDING:
                color = BRIGHT_RED
                text = self.get_text('RECORDING')
                pulse = True
            elif self.state == AppState.PROCESSING:
                color = BRIGHT_YELLOW
                text = self.get_text('PROCESSING')
                pulse = True
            else:
                color = BRIGHT_GREEN
                text = self.get_text('TAP_TO_SPEAK')
                pulse = False

            button_rect = self.main_button_rect.copy()
            if pulse:
                self.animation_frame = (self.animation_frame + 1) % 60
                scale = 1.0 + 0.03 * abs(30 - self.animation_frame) / 30
                w_diff = int(button_rect.width * (scale - 1) / 2)
                h_diff = int(button_rect.height * (scale - 1) / 2)
                button_rect.inflate_ip(w_diff, h_diff)

            # Shadow
            shadow_rect = button_rect.copy()
            shadow_rect.move_ip(8, 8)
            pygame.draw.rect(self.screen, (100, 100, 100), shadow_rect, border_radius=40)

            # Button
            pygame.draw.rect(self.screen, color, button_rect, border_radius=40)
            pygame.draw.rect(self.screen, WHITE, button_rect, width=6, border_radius=40)

            # Button text
            btn_text_surface = self._render_text(text, self.medium_font, WHITE)
            btn_text_rect = btn_text_surface.get_rect(center=button_rect.center)
            self.screen.blit(btn_text_surface, btn_text_rect)

    # ===========================================
    # EVENT HANDLING
    # ===========================================
    def _handle_touch(self, pos: tuple):
        """Handle touch/click events."""
        if self.state == AppState.MODE_SELECT:
            for mode, rect in self.mode_buttons.items():
                if rect.collidepoint(pos):
                    if mode in [GameMode.FREE_SPEECH, GameMode.SPELLING, GameMode.TRANSLATION]:
                        self.current_mode = mode
                        self.state = AppState.READY
                        log.info(f"Selected mode: {mode.value}")
                    return

        else:
            # Back button
            if self.back_button_rect.collidepoint(pos):
                if self.is_recording_active:
                    self._stop_recording()
                # Disable continuous mode when going back
                self.continuous_mode = False
                self.pending_restart_listening = False
                self.state = AppState.MODE_SELECT
                self.current_mode = None
                self.recognized_text = ""
                self.last_recognized_text = ""
                self.translation_original = ""
                # Reset spelling game state
                self.spelling_game = {
                    'difficulty': None,
                    'current_word': None,
                    'target_word': None,
                    'user_spelling': [],
                    'word_list': [],
                    'score': 0
                }
                return

            # Continuous mode toggle
            if self.continuous_btn_rect.collidepoint(pos):
                self._toggle_continuous_mode()
                return

            # Language toggle
            if self.hebrew_btn_rect.collidepoint(pos):
                self.set_language('hebrew')
                return
            if self.english_btn_rect.collidepoint(pos):
                self.set_language('english')
                return

            # Speaker button
            if (self.state == AppState.SHOWING and
                self.last_recognized_text and
                self.speaker_btn_rect.collidepoint(pos)):
                self.speak_text()
                return

            # Spelling mode: Difficulty selector
            if self.current_mode == GameMode.SPELLING and self.spelling_game['difficulty'] is None:
                for difficulty, rect in self.difficulty_buttons.items():
                    if rect.collidepoint(pos):
                        self.select_difficulty(difficulty)
                        return
            
            # Spelling mode: Game control buttons
            if self.current_mode == GameMode.SPELLING and self.spelling_game['difficulty'] is not None:
                if self.repeat_btn_rect.collidepoint(pos):
                    self.repeat_word()
                    return
                if self.next_btn_rect.collidepoint(pos):
                    self.next_word()
                    return

            # Main button
            if self.main_button_rect.collidepoint(pos):
                if self.state == AppState.RECORDING:
                    self._stop_recording()
                elif self.state in [AppState.READY, AppState.SHOWING]:
                    self._record_audio()

    def run(self):
        """Main app loop."""
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        if self.state == AppState.MODE_SELECT:
                            self._handle_touch(self.mode_buttons[GameMode.FREE_SPEECH].center)
                        else:
                            self._handle_touch(self.main_button_rect.center)
                    elif event.key == pygame.K_s:
                        screenshot_path = os.path.expanduser("~/screenshot.png")
                        pygame.image.save(self.screen, screenshot_path)
                        log.info(f"Screenshot saved: {screenshot_path}")
                    elif event.key == pygame.K_h:
                        self.set_language('hebrew')
                    elif event.key == pygame.K_e:
                        self.set_language('english')
                    elif event.key == pygame.K_c:
                        if self.state not in [AppState.MODE_SELECT]:
                            self._toggle_continuous_mode()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_touch(event.pos)
                elif event.type == pygame.FINGERDOWN:
                    x = int(event.x * SCREEN_WIDTH)
                    y = int(event.y * SCREEN_HEIGHT)
                    self._handle_touch((x, y))

            # Check for pending restart in continuous mode
            if (self.pending_restart_listening and
                self.continuous_mode and
                not self.is_recording_active and
                not self.tts_playing and
                self.state in [AppState.READY, AppState.SHOWING]):
                self.pending_restart_listening = False
                log.info("Continuous mode: restarting listening")
                self._record_audio()

            # Draw
            self.screen.fill(SOFT_BACKGROUND)

            if self.state == AppState.MODE_SELECT:
                self._draw_mode_select()
            else:
                self._draw_game_screen()

            pygame.display.flip()
            self.clock.tick(60)

        # Cleanup
        self.audio.terminate()
        pygame.quit()
        try:
            os.unlink(self.temp_wav)
            os.unlink(self.temp_tts)
        except:
            pass


def main():
    log.info("=" * 50)
    log.info("Hebrew Voice Game")
    log.info("=" * 50)
    log.info("Controls: ESC=exit, SPACE=action, S=screenshot, H=Hebrew, E=English, C=continuous mode")
    log.info(f"TTS available: {HAS_GTTS}")

    app = HebrewVoiceApp()
    app.run()


if __name__ == "__main__":
    main()
