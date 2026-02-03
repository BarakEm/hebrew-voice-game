# Cast Button Troubleshooting Guide

## ✅ Cast Button is Now Fixed

The cast button now properly detects and reports Chromecast device availability. When you open the app, check the browser console (F12) to see detailed status information.

## How to Use the Cast Button

1. **Start the HTTPS Server**
   ```bash
   python3 serve.py
   ```

2. **Open in Chrome Browser**
   - Navigate to: `https://localhost:8443/hebrew_voice_app.html`
   - Or: `https://<your-ip>:8443/hebrew_voice_app.html`
   - Accept the self-signed certificate warning

3. **Check Console Messages**
   - Press F12 to open Developer Tools
   - Look for these messages:
     - ✅ "Google Cast API availability: true" - API loaded
     - ✅ "Google Cast initialized. Initial state: ..." - Shows device status
     
## What the Console Messages Mean

### ✅ Success Messages
- **"Google Cast initialized. Initial state: NOT_CONNECTED"**
  - Cast API working, devices available, ready to connect
  - Click the cast button to see available devices

- **"✅ Connected to TV!"**
  - Successfully connected to a Chromecast
  - Content now showing on TV

### ⚠️ Warning Messages
- **"❌ No Chromecast devices found on network"**
  - No Chromecast devices detected
  - See troubleshooting steps below

- **"⚠️ Google Cast API not available"**
  - Not using Chrome browser
  - Solution: Use Chrome, Edge, or Chromium-based browser

### 🔄 Status Messages
- **"🔄 Connecting to TV..."**
  - Connection in progress
  - Wait a few seconds

- **"📺 Disconnected from TV"**
  - Was connected, now disconnected
  - Normal when you stop casting

## Troubleshooting No Devices Found

If you see "❌ No Chromecast devices found on network":

### 1. Check Chromecast Device
- [ ] Device is powered on
- [ ] Device shows "Ready to cast" screen
- [ ] Device is connected to WiFi (not sleeping)

### 2. Check Network
- [ ] Computer and Chromecast on SAME WiFi network
- [ ] Not using guest WiFi or VPN
- [ ] Router allows device discovery (mDNS/Bonjour enabled)
- [ ] No firewall blocking Chromecast ports

### 3. Check Google Home App
- [ ] Open Google Home app on phone
- [ ] Can you see your Chromecast?
- [ ] Try casting from YouTube to verify Chromecast works

### 4. Check Browser
- [ ] Using Chrome, Edge, or Chromium browser
- [ ] Not using Firefox, Safari, or other browsers
- [ ] Chrome is up to date

### 5. Restart Everything
1. Unplug Chromecast for 30 seconds
2. Plug back in and wait for "Ready to cast"
3. Restart Chrome browser
4. Restart the serve.py script
5. Try again

## Testing Tools

### Quick Test: casting_demo.html
```bash
# Start server
python3 serve.py

# Open in browser
https://localhost:8443/casting_demo.html
```
This is a simplified test page that focuses only on casting functionality.

### Debug Test: test_cast.html
```bash
# Start server  
python3 serve.py

# Open in browser
https://localhost:8443/test_cast.html
```
This page shows detailed diagnostic information and logs every Cast API event.

## Common Issues

### Cast Button is Grey/Invisible
- **Cause**: No Cast API loaded or no devices available
- **Check Console**: Look for initialization messages
- **Solution**: Ensure using Chrome and Chromecast is on

### Cast Button Shows but No Devices Listed
- **Cause**: NO_DEVICES_AVAILABLE state
- **Console Shows**: "❌ No Chromecast devices found"
- **Solution**: Follow troubleshooting steps above

### Can't Click Cast Button
- **Cause**: Button may be disabled
- **Solution**: Check console for error messages

### Connected but Nothing Shows on TV
- **Cause**: Normal behavior - Cast mirrors tab content
- **What to Expect**: 
  - Phone/computer controls the app
  - TV displays what's on screen
  - Some latency (~0.5-1 second) is normal

## Alternative Casting Methods

If the Cast button still doesn't work, you can use browser-native casting:

### Chrome Cast Tab
1. Open app in Chrome
2. Click ⋮ (three dots menu)
3. Select "Cast..."
4. Choose your Chromecast
5. Select "Cast tab"

This works even without the Cast button!

## Network Requirements

Cast requires:
- ✅ HTTPS (already configured in serve.py)
- ✅ mDNS/Bonjour for device discovery
- ✅ Ports 8008-8009 (Chromecast)
- ✅ Port 5353 (mDNS)

Most home networks support this by default.

## Still Having Issues?

1. Check the console messages carefully
2. Try the test_cast.html diagnostic page
3. Verify Chromecast works with YouTube or other apps
4. Check if both devices show in your router's connected devices list
5. Try a different Chrome/Chromium browser

## Technical Details

For developers, see:
- `CAST_FIX_DETAILS.md` - Technical explanation of the fix
- `TV_CASTING_GUIDE.md` - Complete casting implementation guide
- `CASTING_QUICK_START.md` - Quick reference for all casting methods

---

**Note**: The cast button only appears in Chrome and only when Cast API loads successfully. The console messages will tell you exactly what's happening.
