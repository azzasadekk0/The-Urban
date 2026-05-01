"""
ngrok_tunnel.py — launches a public ngrok tunnel for the Next.js frontend.
Called by start.ps1:  python ngrok_tunnel.py <port> <auth_token>
"""
import sys
import os

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"] = "false"

import time
import subprocess
from pyngrok import ngrok, conf

port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
token = sys.argv[2] if len(sys.argv) > 2 else ""

if token:
    conf.get_default().auth_token = token

# Step 1: Force-kill ALL ngrok processes at OS level
try:
    subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], capture_output=True)
except Exception:
    pass

# Step 2: Kill via pyngrok API too
try:
    ngrok.kill()
except Exception:
    pass

# Step 3: Wait for ngrok's remote endpoint to fully release
print("\nWaiting for previous tunnel to release...", flush=True)
time.sleep(5)

print(f"Connecting ngrok tunnel to port {port}...", flush=True)
tunnel = ngrok.connect(port, "http")
public_url = tunnel.public_url

print()
print("=" * 60)
print("  LIVE PUBLIC URL (share with anyone):")
print(f"  {public_url}")
print("=" * 60)
print()
sys.stdout.flush()

# Keep the process alive so the tunnel stays open
try:
    ngrok.get_ngrok_process().proc.wait()
except KeyboardInterrupt:
    print("\nClosing ngrok tunnel...")
    ngrok.kill()
