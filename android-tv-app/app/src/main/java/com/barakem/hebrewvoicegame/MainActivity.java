package com.barakem.hebrewvoicegame;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.tts.TextToSpeech;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.mediarouter.app.MediaRouteChooserDialog;
import androidx.mediarouter.media.MediaControlIntent;
import androidx.mediarouter.media.MediaRouteSelector;
import androidx.mediarouter.media.MediaRouter;

import java.util.Locale;

public class MainActivity extends Activity {

    private static final int MIC_PERMISSION_REQUEST = 1001;
    private WebView webView;
    private TextToSpeech tts;
    private boolean ttsReady = false;
    private MediaRouter mediaRouter;
    private MediaRouteSelector mediaRouteSelector;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Go immersive fullscreen
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );

        // Request microphone permission upfront
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_PERMISSION_REQUEST);
            }
        }

        // Initialize TTS
        tts = new TextToSpeech(this, status -> {
            ttsReady = (status == TextToSpeech.SUCCESS);
            if (ttsReady) {
                tts.setLanguage(new Locale("he", "IL"));
            }
        });

        // Initialize MediaRouter for cast discovery
        mediaRouter = MediaRouter.getInstance(this);
        mediaRouteSelector = new MediaRouteSelector.Builder()
            .addControlCategory(MediaControlIntent.CATEGORY_LIVE_AUDIO)
            .addControlCategory(MediaControlIntent.CATEGORY_REMOTE_PLAYBACK)
            .build();

        webView = findViewById(R.id.webview);
        setupWebView();
        webView.loadUrl(getString(R.string.app_url));
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setDatabaseEnabled(true);

        // Allow mixed content for speech APIs
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        }

        // Expose native Android functions to JavaScript
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");

        // Stay inside the app instead of opening browser
        webView.setWebViewClient(new WebViewClient());

        // Handle microphone permission requests from the web page
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> request.grant(request.getResources()));
            }
        });
    }

    /**
     * Bridge between JavaScript in the WebView and native Android.
     */
    private class AndroidBridge {
        @JavascriptInterface
        public boolean isAndroidApp() {
            return true;
        }

        @JavascriptInterface
        public void speak(String text, String lang) {
            if (!ttsReady || text == null || text.isEmpty()) return;

            tts.stop();

            // Parse language code (e.g. "he-IL" -> Locale("he", "IL"))
            Locale locale;
            if (lang != null && lang.contains("-")) {
                String[] parts = lang.split("-");
                locale = new Locale(parts[0], parts[1]);
            } else if (lang != null) {
                locale = new Locale(lang);
            } else {
                locale = new Locale("he", "IL");
            }
            tts.setLanguage(locale);
            tts.setSpeechRate(0.8f);

            tts.speak(text, TextToSpeech.QUEUE_ADD, null, "utterance_" + System.currentTimeMillis());
        }

        @JavascriptInterface
        public void stopSpeaking() {
            if (ttsReady) {
                tts.stop();
            }
        }

        @JavascriptInterface
        public boolean isTtsReady() {
            return ttsReady;
        }

        @JavascriptInterface
        public void openCastSettings() {
            runOnUiThread(() -> showCastDialog());
        }
    }

    private void showCastDialog() {
        try {
            MediaRouteChooserDialog dialog = new MediaRouteChooserDialog(this);
            dialog.setRouteSelector(mediaRouteSelector);
            dialog.show();
        } catch (Exception e) {
            // Fallback: open Android's built-in Cast / screen mirror settings
            try {
                Intent intent = new Intent(Settings.ACTION_CAST_SETTINGS);
                startActivity(intent);
            } catch (Exception e2) {
                try {
                    Intent intent = new Intent("android.settings.WIFI_DISPLAY_SETTINGS");
                    startActivity(intent);
                } catch (Exception e3) {
                    Intent intent = new Intent(Settings.ACTION_WIRELESS_SETTINGS);
                    startActivity(intent);
                }
            }
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onPause() {
        webView.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        webView.destroy();
        super.onDestroy();
    }
}
