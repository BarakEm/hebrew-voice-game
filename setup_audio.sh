#!/bin/bash
# Audio setup script for Hebrew Voice App on Raspberry Pi

echo "=== Hebrew Voice App Audio Setup ==="
echo

# Check if user is in audio group
if groups | grep -q audio; then
    echo "[OK] User is in audio group"
else
    echo "[!] Adding user to audio group..."
    sudo usermod -aG audio $(whoami)
    echo "    Please log out and back in for changes to take effect"
fi

echo
echo "=== Available Audio Capture Devices ==="
arecord -l 2>/dev/null || echo "No capture devices found!"

echo
echo "=== Available Audio Playback Devices ==="
aplay -l 2>/dev/null || echo "No playback devices found!"

echo
echo "=== Testing Microphone (3 seconds) ==="
echo "Using USB microphone (hw:1,0) at 44100 Hz..."
echo "Speak now..."
arecord -D hw:1,0 -d 3 -f S16_LE -r 44100 -c 1 /tmp/test_audio.wav 2>/dev/null

if [ -f /tmp/test_audio.wav ]; then
    echo "[OK] Recording successful!"
    echo "Playing back..."
    aplay /tmp/test_audio.wav 2>/dev/null
    rm /tmp/test_audio.wav
else
    echo "[!] Recording failed - check microphone connection"
fi

echo
echo "=== Setup Complete ==="
echo "Run the app with: python3 hebrew_voice_app.py"
