"""QR login for one account: python qr_login.py account1
Scans in phone Telegram: Settings -> Devices -> Link Desktop Device.
Saves sessions/<name>.session, never commit it."""
import asyncio, os, sys, yaml
from telethon import TelegramClient
import qrcode
BASE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1] if len(sys.argv) > 1 else "account1"
with open(os.path.join(BASE, "config.yaml")) as f:
    cfg = yaml.safe_load(f)

async def main():
    os.makedirs(os.path.join(BASE, "sessions"), exist_ok=True)
    client = TelegramClient(os.path.join(BASE, "sessions", name), cfg["api_id"], cfg["api_hash"])
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"ALREADY {me.id}"); await client.disconnect(); return
    qr = await client.qr_login()
    img = qrcode.make(qr.url); img.save(os.path.join(BASE, f"qr_{name}.png"))
    print("QR_SAVED", os.path.join(BASE, f"qr_{name}.png"), flush=True)
    try:
        await qr.wait(timeout=300)
        me = await client.get_me(); print(f"LOGGED_IN {me.id} @{me.username}")
    except Exception as e:
        print(f"QR_FAILED {type(e).__name__}: {e}")
    await client.disconnect()
asyncio.run(main())
