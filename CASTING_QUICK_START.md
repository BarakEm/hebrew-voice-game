# Quick Reference: Cast to TV 📺

## Fastest Methods (No Coding Required)

### 1. Chrome Cast Tab (✅ Recommended)
**Works with:** Chromecast, Google TV, Android TV
1. Open app in Chrome → Tap **⋮** (menu)
2. Tap **"Cast"**
3. Select your TV
4. Choose **"Cast tab"**

**Requirements:**
- TV and phone on same WiFi
- Chrome browser

---

### 2. iPhone/iPad AirPlay
**Works with:** Apple TV, AirPlay 2 TVs (Samsung, LG, Sony)
1. Swipe down (Control Center)
2. Tap **"Screen Mirroring"**
3. Select your Apple TV
4. Open app in Safari

---

### 3. Android Screen Cast
**Works with:** Most Smart TVs
1. Settings → **Connected devices** → **Cast**
2. Select your TV
3. Open app in Chrome

*Name varies: "Cast", "Smart View", "Screen Share"*

---

### 4. HDMI Cable (Zero Latency!)
**Hardware:** USB-C/Lightning to HDMI adapter ($15-50)
1. Plug cable into phone/tablet
2. Connect to TV HDMI port
3. Open app

**Perfect for:**
- Presentations
- Demo/teaching
- Guaranteed quality

---

## For Developers: Add Cast Button

```html
<!-- Add to <head> -->
<script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>

<!-- Add cast button -->
<google-cast-launcher></google-cast-launcher>

<script>
window['__onGCastApiAvailable'] = function(isAvailable) {
    if (isAvailable) {
        cast.framework.CastContext.getInstance().setOptions({
            receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID
        });
    }
};
</script>
```

See [TV_CASTING_GUIDE.md](TV_CASTING_GUIDE.md) for full implementation.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cast button not showing | Use Chrome, ensure Chromecast is on network |
| Can't find TV | Check both on same WiFi network |
| Poor quality | Move closer to WiFi router |
| Audio not working | Audio comes from phone (by design) |
| Lag/latency | Use HDMI cable for zero latency |

---

## Test It Now!

Open [casting_demo.html](casting_demo.html) to test cast functionality.

---

## Hardware Compatibility

✅ **Works with:**
- Chromecast (all versions)
- Google TV / Android TV
- Smart TVs with built-in Chromecast
- Apple TV (via AirPlay)
- Samsung/LG/Sony TVs with screen mirroring

📱 **Tested Browsers:**
- Chrome (Android, iOS, Desktop) - Best support
- Safari (iOS) - AirPlay only
- Edge (Desktop) - Supports Chromecast

🔒 **Security:**
- Microphone stays on phone
- Secure WiFi required
- HTTPS required for casting APIs

---

**Full Guide:** [TV_CASTING_GUIDE.md](TV_CASTING_GUIDE.md)  
**Demo:** [casting_demo.html](casting_demo.html)
