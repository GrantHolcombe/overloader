"""Put a new random secret on the clipboard without showing it.

    .venv\\Scripts\\python scripts\\new_secret.py

For values that must match in two places, such as the origin secret (the overloader-edge
Worker's ORIGIN_SECRET and the api stack's OriginSecret): paste it into both, then press Enter
and the clipboard is cleared. Windows only (uses clip).
"""

import secrets
import subprocess


def to_clipboard(text: str) -> None:
    subprocess.run(["clip"], input=text.encode("ascii"), check=True)


to_clipboard(secrets.token_urlsafe(48))
input("A new secret is on the clipboard. Paste it everywhere it's needed, then press Enter... ")
to_clipboard(" ")
print("Clipboard cleared.")
