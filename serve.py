#!/usr/bin/env python3
"""
Simple HTTPS server for Hebrew Voice Game.
Serves the HTML file over HTTPS (required for microphone access from other devices).

Usage:
    python3 serve.py [port]

Default port: 8443
Access from browser: https://<rpi-ip>:8443
"""

import http.server
import ssl
import socket
import os
import subprocess
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
CERT_FILE = "server.pem"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def generate_ssl_cert():
    """Generate a self-signed SSL certificate if it doesn't exist."""
    cert_path = os.path.join(SCRIPT_DIR, CERT_FILE)
    if os.path.exists(cert_path):
        print(f"Using existing certificate: {cert_path}")
        return cert_path

    print("Generating self-signed SSL certificate...")
    cmd = [
        "openssl", "req", "-new", "-x509",
        "-keyout", cert_path,
        "-out", cert_path,
        "-days", "365",
        "-nodes",
        "-subj", "/CN=HebrewVoiceGame/O=Local/C=US"
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Certificate generated: {cert_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate certificate: {e}")
        print("Please install openssl: sudo apt install openssl")
        sys.exit(1)
    except FileNotFoundError:
        print("openssl not found. Please install: sudo apt install openssl")
        sys.exit(1)

    return cert_path

def main():
    os.chdir(SCRIPT_DIR)
    cert_path = generate_ssl_cert()

    local_ip = get_local_ip()

    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("0.0.0.0", PORT), handler)

    # Wrap with SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print("\n" + "=" * 50)
    print("Hebrew Voice Game Server")
    print("=" * 50)
    print(f"\nServer running on port {PORT}")
    print(f"\nAccess the game at:")
    print(f"  Local:   https://localhost:{PORT}/hebrew_voice_app.html")
    print(f"  Network: https://{local_ip}:{PORT}/hebrew_voice_app.html")
    print(f"\nNote: Your browser will warn about the self-signed certificate.")
    print("      Click 'Advanced' -> 'Proceed' to continue.")
    print("\nPress Ctrl+C to stop the server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()

if __name__ == "__main__":
    main()
