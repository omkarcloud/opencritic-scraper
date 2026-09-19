"""Configuration for the Opencritic Scraper. Everything can be set with an
environment variable; the defaults work out of the box.

    PORT              port the API listens on (default 8000)
    OPENCRITIC_PROXY  proxy URL for every request, e.g. http://user:pass@host:port
                      (default: none — direct). OpenCritic's JSON API did not
                      rate-limit at 120 requests in 7 seconds from one IP, so
                      you very likely don't need this. Set it only if you start
                      seeing 403 / 429 errors at high volume.
    OPENCRITIC_API_KEY  pin the site's public web-app key by hand (default:
                      none — the scraper reads it from opencritic.com's own
                      JavaScript bundle and refreshes it when it changes).

Everything else below is a plain constant with a working default — edit it
here if you need to.
"""
import os

PORT = int(os.environ.get("PORT", "8000"))

# Retry policy for transport errors (every request).
MAX_RETRIES = 3
RETRY_BACKOFF = 2          # seconds, multiplied by the attempt number

OPENCRITIC_PROXY = os.environ.get("OPENCRITIC_PROXY") or None
OPENCRITIC_API_KEY = os.environ.get("OPENCRITIC_API_KEY") or None


def opencritic_proxy():
    """Proxy URL for the scraper's HTTP session, None = direct."""
    return os.environ.get("OPENCRITIC_PROXY") or None
