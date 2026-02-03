# TV Casting Guide for Hebrew Voice Game

## Overview

This guide covers multiple methods to cast the Hebrew Voice Game web app to a TV, including native browser features, Google Cast API, and hardware-based solutions.

---

## Method 1: Browser Native Casting (Easiest, No Code Changes)

### Google Chrome - Cast Tab (Recommended)

**Works with:** Any Chromecast-enabled TV, Google TV, Chromecast dongle

**How it works:**
1. Open the web app in Chrome on your phone/laptop
2. Tap the three-dot menu (⋮) → "Cast"
3. Select your TV from the list
4. Choose "Cast tab" or "Cast screen"

**Pros:**
- No code changes required
- Works immediately with existing app
- Free, built into Chrome
- Supports audio from microphone through phone

**Cons:**
- Slight latency (~0.5-1 second)
- Uses phone as intermediary
- Quality depends on WiFi strength

**Setup:**
- TV must be on same WiFi network as phone
- Chromecast must be set up on TV

---

## Method 2: Google Cast API Integration (Professional)

### Implementation with Sender API

Add Google Cast support directly to the web app for a seamless experience.

**Hardware needed:** Chromecast-enabled TV or Chromecast dongle ($30-50)

### Step 1: Add Cast SDK to HTML

```html
<!-- Add to <head> section -->
<script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>
```

### Step 2: Add Cast Button to UI

```html
<!-- Add cast button near language toggle -->
<google-cast-launcher id="castbutton"></google-cast-launcher>

<style>
#castbutton {
    --connected-color: #32cd32;
    --disconnected-color: #6495ed;
    width: 60px;
    height: 60px;
    cursor: pointer;
}
</style>
```

### Step 3: Initialize Cast Framework (JavaScript)

```javascript
// Cast API initialization
window['__onGCastApiAvailable'] = function(isAvailable) {
    if (isAvailable) {
        cast.framework.CastContext.getInstance().setOptions({
            receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
            autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
        });
        
        // Listen for cast state changes
        const castContext = cast.framework.CastContext.getInstance();
        castContext.addEventListener(
            cast.framework.CastContextEventType.CAST_STATE_CHANGED,
            onCastStateChanged
        );
    }
};

function onCastStateChanged(event) {
    console.log('Cast state:', event.castState);
    if (event.castState === 'CONNECTED') {
        console.log('Connected to TV!');
        // Optional: Adjust UI for TV display
        adjustForTVMode();
    }
}

function adjustForTVMode() {
    // Make text larger for TV viewing
    document.body.style.fontSize = '150%';
    // Optional: Hide cast button when connected
    document.getElementById('castbutton').style.opacity = '0.5';
}
```

### Step 4: Cast Custom Web App (Advanced)

For full control, create a custom receiver app:

```javascript
// In your sender app (phone/tablet)
const applicationId = 'YOUR_APP_ID'; // Register at Google Cast SDK

function loadCastReceiverApp() {
    const castSession = cast.framework.CastContext.getInstance().getCurrentSession();
    castSession.loadMedia(new chrome.cast.media.LoadRequest({
        contentId: 'https://barakem.github.io/hebrew-voice-game/hebrew_voice_app.html',
        contentType: 'application/x-webcast',
        streamType: chrome.cast.media.StreamType.LIVE
    }));
}
```

**Pros:**
- Professional integration
- Low latency
- Control TV display from phone
- Can show custom receiver UI on TV
- Free to use (just need Chromecast hardware)

**Cons:**
- Requires code changes
- Need to register app with Google (free but requires account)
- Only works with Chromecast devices

**Documentation:**
- https://developers.google.com/cast/docs/web_sender
- https://developers.google.com/cast/docs/developers

---

## Method 3: Apple AirPlay (iOS/macOS to Apple TV)

### Browser Screen Mirroring

**Works with:** Apple TV, AirPlay 2-compatible TVs (Samsung, LG, Sony, Vizio)

**How it works:**
1. Swipe down from top-right on iPhone/iPad (Control Center)
2. Tap "Screen Mirroring"
3. Select your Apple TV
4. Open web app in Safari

**Pros:**
- No code changes needed
- Full screen mirroring
- Good quality
- Audio works

**Cons:**
- Requires Apple TV or AirPlay 2 TV (~$150+)
- Only works from iOS/macOS
- Mirrors entire screen (includes status bar)

### AirPlay API Integration (Advanced)

For Safari on iOS 13+, you can add AirPlay controls:

```html
<video id="video-element" controls>
    <source src="your-content.mp4" type="video/mp4">
</video>

<script>
// Detect AirPlay availability
if (window.WebKitPlaybackTargetAvailabilityEvent) {
    const video = document.getElementById('video-element');
    
    video.addEventListener('webkitplaybacktargetavailabilitychanged', (event) => {
        if (event.availability === 'available') {
            // Show AirPlay button
            console.log('AirPlay available');
        }
    });
    
    // Trigger AirPlay picker
    video.webkitShowPlaybackTargetPicker();
}
</script>
```

**Note:** AirPlay API is limited to media playback, not full app casting.

---

## Method 4: Miracast / DLNA (Android)

### Screen Mirroring (Android)

**Works with:** Smart TVs with Miracast, DLNA, or Screen Mirroring support

**How it works:**
1. Open Settings → Connected devices → Cast (or Screen Mirroring)
2. Select your TV
3. Open web app in Chrome

**Pros:**
- No code changes needed
- Works with many TV brands
- Built into Android

**Cons:**
- Name varies by manufacturer (Cast, Smart View, Screen Share)
- Quality varies
- Some latency

**Compatible TVs:**
- Samsung (Smart View)
- LG (Screen Share)
- Sony (Screen mirroring)
- Most Android TVs

---

## Method 5: HDMI Cable (Zero Latency)

### Direct Connection

**Hardware:** USB-C to HDMI adapter ($15-30) or Lightning to HDMI ($40-50)

**How it works:**
1. Connect phone/tablet to TV via HDMI cable
2. Open web app
3. TV displays phone screen

**Pros:**
- Zero latency
- Perfect quality
- No WiFi needed
- No code changes

**Cons:**
- Requires cable
- Device must stay connected
- Battery drains faster

**Recommended adapters:**
- **Android:** USB-C to HDMI (ensure phone supports video out)
- **iOS:** Apple Lightning Digital AV Adapter (official)
- **Laptop:** Built-in HDMI port

---

## Method 6: Raspberry Pi as TV Kiosk (Purpose-Built)

### Direct Python App on TV-Connected Pi

Since you already have `hebrew_voice_app.py` for Raspberry Pi:

**Setup:**
1. Connect Raspberry Pi to TV via HDMI
2. Run the Python app in fullscreen
3. Use wireless keyboard/mouse or touchscreen

```bash
# Auto-start on boot
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
# Add line:
@python3 /home/pi/hebrew-voice-app.py
```

**Pros:**
- No casting needed
- No latency
- Dedicated hardware
- Raspberry Pi is cheap ($35-75)

**Cons:**
- Requires Raspberry Pi setup
- Physical device connected to TV

---

## Recommended Solutions by Use Case

### For Families with Smart TV (Already Own)
**→ Method 1: Chrome Cast Tab (Easiest)**
- Zero code changes
- Works with existing Chromecast/Google TV
- Just open app and cast

### For Best Quality & Control
**→ Method 2: Google Cast API Integration**
- Professional solution
- Requires coding but reusable
- Worth it for polished app

### For iOS Users with Apple TV
**→ Method 3: AirPlay Screen Mirroring**
- Built into iOS
- No code changes

### For Dedicated Setup (e.g., Classroom)
**→ Method 6: Raspberry Pi + TV**
- Use the Python version directly
- Most reliable
- Can be permanently set up

### For Zero Latency (e.g., Performance)
**→ Method 5: HDMI Cable**
- Direct connection
- Perfect quality

---

## Implementation Priority

For the Hebrew Voice Game, I recommend:

### Phase 1: Document Native Casting (Immediate)
- Add instructions to README.md
- No code changes
- Users can cast today

### Phase 2: Google Cast Integration (Future Enhancement)
- Add Cast button to `hebrew_voice_app.html`
- Register app with Google Cast SDK
- Test with Chromecast

### Phase 3: TV-Optimized UI (Optional)
- Detect when connected to TV
- Increase font sizes
- Optimize layout for 16:9 displays

---

## Sample Code for Phase 2

Here's a minimal implementation to add to `hebrew_voice_app.html`:

```html
<!-- In <head> -->
<script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>

<!-- In header section, next to language toggle -->
<div class="cast-container">
    <google-cast-launcher id="castbutton"></google-cast-launcher>
</div>

<style>
.cast-container {
    position: absolute;
    top: 2vmin;
    left: 2vmin; /* or right: 2vmin for RTL */
}

google-cast-launcher {
    --connected-color: #32cd32;
    --disconnected-color: #6495ed;
    width: clamp(40px, 8vmin, 60px);
    height: clamp(40px, 8vmin, 60px);
}
</style>

<script>
// Initialize Cast API
window['__onGCastApiAvailable'] = function(isAvailable) {
    if (isAvailable) {
        cast.framework.CastContext.getInstance().setOptions({
            receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
            autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
        });
        
        // Listen for cast state
        cast.framework.CastContext.getInstance().addEventListener(
            cast.framework.CastContextEventType.CAST_STATE_CHANGED,
            function(event) {
                if (event.castState === 'CONNECTED') {
                    // Optional: Scale up UI for TV
                    document.documentElement.style.fontSize = '150%';
                } else {
                    document.documentElement.style.fontSize = '100%';
                }
            }
        );
    }
};
</script>
```

---

## Testing Checklist

Before deployment:
- [ ] Test cast button appears in Chrome
- [ ] Test connection to Chromecast device
- [ ] Verify audio routing (mic stays on phone)
- [ ] Test language toggle works while casting
- [ ] Verify Hebrew RTL text displays correctly on TV
- [ ] Test all game modes while casting
- [ ] Confirm button sizes are readable from TV distance
- [ ] Test reconnection after WiFi interruption

---

## Resources

### Official Documentation
- **Google Cast:** https://developers.google.com/cast
- **Web Sender API:** https://developers.google.com/cast/docs/web_sender
- **AirPlay:** https://developer.apple.com/airplay/

### Tools & Testing
- **Cast Debugger:** chrome://inspect/#devices
- **Cast Developer Console:** https://cast.google.com/publish

### Hardware Compatibility
- **Chromecast:** https://www.google.com/chromecast/built-in/
- **AirPlay 2 TVs:** https://www.apple.com/airplay/

---

## Security Considerations

When implementing casting:
- Microphone stays on sender device (phone/tablet)
- Network must be secure (encrypted WiFi)
- Consider adding PIN protection for classroom use
- HTTPS required for WebRTC and casting APIs

---

## Future Ideas

- **Multi-device:** Parent controls on phone, kid views on TV
- **Scoreboard mode:** Display scores on TV while playing on tablet
- **Party mode:** Multiple kids take turns, TV shows leaderboard
- **Recording:** Save sessions and replay on TV
