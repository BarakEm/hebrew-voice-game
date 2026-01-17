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
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
import speech_recognition as sr
from bidi.algorithm import get_display

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

# Audio settings
RECORD_SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


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

# UI Text for each language
UI_TEXT = {
    'hebrew': {
        'SELECT_MODE': 'בחר משחק',
        'FREE_SPEECH': 'דיבור חופשי',
        'SPELLING': 'איות (בקרוב)',
        'TRANSLATION': 'תרגום (בקרוב)',
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
    },
    'english': {
        'SELECT_MODE': 'Select Game',
        'FREE_SPEECH': 'Free Speech',
        'SPELLING': 'Spelling (Soon)',
        'TRANSLATION': 'Translation (Soon)',
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

        # Recording state
        self.is_recording_active = False
        self.stop_recording_flag = False

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

    # ===========================================
    # TEXT-TO-SPEECH
    # ===========================================
    def speak_text(self, text: str = None):
        """Speak the given text or last recognized text."""
        if not HAS_GTTS:
            log.warning("gTTS not available")
            return

        text = text or self.last_recognized_text
        if not text:
            return

        def speak():
            try:
                lang_code = 'he' if self.current_lang == 'hebrew' else 'en'
                tts = gTTS(text=text, lang=lang_code, slow=True)
                tts.save(self.temp_tts)
                pygame.mixer.music.load(self.temp_tts)
                pygame.mixer.music.play()
                log.info(f"Speaking: {text}")
            except Exception as e:
                log.error(f"TTS error: {e}")

        threading.Thread(target=speak, daemon=True).start()

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

            self.state = AppState.SHOWING

        threading.Thread(target=process, daemon=True).start()

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
            (GameMode.SPELLING, GRAY, 'SPELLING', False),
            (GameMode.TRANSLATION, GRAY, 'TRANSLATION', False),
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
            display_text = self.get_text('SAY_SOMETHING')
            text_color = BRIGHT_BLUE

        # Fit text to display
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

        # Main button
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
                    if mode == GameMode.FREE_SPEECH:
                        self.current_mode = mode
                        self.state = AppState.READY
                        log.info(f"Selected mode: {mode.value}")
                    # Other modes coming soon
                    return

        else:
            # Back button
            if self.back_button_rect.collidepoint(pos):
                if self.is_recording_active:
                    self._stop_recording()
                self.state = AppState.MODE_SELECT
                self.current_mode = None
                self.recognized_text = ""
                self.last_recognized_text = ""
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
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_touch(event.pos)
                elif event.type == pygame.FINGERDOWN:
                    x = int(event.x * SCREEN_WIDTH)
                    y = int(event.y * SCREEN_HEIGHT)
                    self._handle_touch((x, y))

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
    log.info("Controls: ESC=exit, SPACE=action, S=screenshot, H=Hebrew, E=English")
    log.info(f"TTS available: {HAS_GTTS}")

    app = HebrewVoiceApp()
    app.run()


if __name__ == "__main__":
    main()
