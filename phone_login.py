"""Phone+code login for one account: python phone_login.py account1 +1234567890
Then type the code Telegram sends to that account into code_<name>.txt,
or adapt to input() for interactive use. Saves sessions/<name>.session."""
import asyncio, os, sys, yaml
BASE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]; phone = sys.argv[2]
with open(os.path.join(BASE, "config.yaml")) as f: cfg = yaml.safe_load(f)
from telethon import TelegramClient
async def main():
    client = TelegramClient(os.path.join(BASE, "sessions", name), cfg["api_id"], cfg["api_hash"])
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me(); print(f"ALREADY {me.id}"); await client.disconnect(); return
    await client.send_code_request(phone); print("CODE_SENT_TO", phone, flush=True)
    for _ in range(60):
        await asyncio.sleep(5)
        p = os.path.join(BASE, f"code_{name}.txt")
        if os.path.exists(p):
            code = open(p).read().strip(); os.remove(p)
            await client.sign_in(phone, code)
            me = await client.get_me(); print(f"LOGGED_IN {me.id} @{me.username}"); break
    await client.disconnect()
asyncio.run(main())
