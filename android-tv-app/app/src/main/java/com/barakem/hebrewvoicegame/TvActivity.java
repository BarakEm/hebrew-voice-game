package com.barakem.hebrewvoicegame;

/**
 * TV launcher entry point. Identical behavior to MainActivity
 * but declared separately so Android TV shows it in the leanback launcher.
 */
public class TvActivity extends MainActivity {
    // Inherits all WebView setup from MainActivity.
    // The AndroidManifest gives this activity the LEANBACK_LAUNCHER category
    // so it appears on the Android TV / Google TV home screen.
}
