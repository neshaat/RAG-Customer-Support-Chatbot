"""
ngrok tunnel helper — exposes the Flask API publicly for demo sharing.

Requirements:
    pip install pyngrok
    # Sign up at https://ngrok.com and set your auth token:
    ngrok config add-authtoken <YOUR_TOKEN>

Usage (standalone):
    python backend/ngrok_tunnel.py

Or import and call start_tunnel() from app.py.
"""

from pyngrok import ngrok, conf
from loguru import logger
import os


NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")
FLASK_PORT       = int(os.getenv("FLASK_PORT", 5000))


def start_tunnel(port: int = FLASK_PORT) -> str | None:
    """
    Open an ngrok HTTPS tunnel to `port`.
    Returns the public URL, or None if ngrok is not configured.
    """
    if not NGROK_AUTH_TOKEN:
        logger.warning(
            "NGROK_AUTH_TOKEN not set. "
            "Set it in your .env file to enable public tunneling."
        )
        return None

    try:
        conf.get_default().auth_token = NGROK_AUTH_TOKEN
        tunnel = ngrok.connect(port, "http")
        public_url = tunnel.public_url
        logger.success(f"ngrok tunnel active: {public_url}")
        logger.info(f"  Chat API:  {public_url}/chat")
        logger.info(f"  Health:    {public_url}/health")
        return public_url
    except Exception as e:
        logger.error(f"ngrok failed to start: {e}")
        return None


def stop_tunnels():
    """Disconnect all active ngrok tunnels."""
    ngrok.disconnect_all()
    logger.info("ngrok tunnels closed.")


if __name__ == "__main__":
    url = start_tunnel()
    if url:
        print(f"\n🌐  Public URL: {url}\n")
        input("Press Enter to close tunnel...\n")
        stop_tunnels()
