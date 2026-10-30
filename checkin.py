"""Telegram daily check-in: 7 accounts -> @zakadeep_bot /checkin at 00:01.
Config: copy config.example.yaml to config.yaml and fill api_id/api_hash.
Sessions: one .session file per account under sessions/, never commit them.
Usage: python checkin.py [account1 account2 ...]  (default account1..account7)
"""
import asyncio, os, random, sys, yaml
from telethon import TelegramClient
BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.yaml")) as f:
    cfg = yaml.safe_load(f)
BOT = cfg.get("bot", "@zakadeep_bot")
MSG = cfg.get("message", "/checkin")

async def run_one(name):
    client = TelegramClient(os.path.join(BASE, "sessions", name), cfg["api_id"], cfg["api_hash"])
    await client.start()
    me = await client.get_me()
    await client.send_message(BOT, MSG)
    await asyncio.sleep(5)
    msgs = await client.get_messages(BOT, limit=3)
    print(f"{name} user={me.id} sent={MSG} replies={[m.text[:80] if m.text else '' for m in msgs]}", flush=True)
    await client.disconnect()

async def main():
    names = sys.argv[1:] or [f"account{i}" for i in range(1, 8)]
    for i, name in enumerate(names):
        if i > 0:
            d = random.randint(30, 120)
            print(f"wait {d}s before {name}", flush=True)
            await asyncio.sleep(d)
        try:
            await run_one(name)
        except Exception as e:
            print(f"{name} FAILED {type(e).__name__}: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
