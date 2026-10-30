"""tg-checkin Web 账号池：纯 API + 单页前端
- 浏览器扫码登录（Telethon QR，过期可刷新）
- 手动 / 定时签到：每天 00:01，号间随机 30-120 秒
- 日志：SQLite，每号每次签到一条
- 配置只存在本机 config.yaml，绝不提交到 GitHub
"""
import asyncio, os, random, sqlite3, time, uuid
from datetime import datetime
from pathlib import Path
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, events

BASE = Path(__file__).parent
CONFIG = BASE / "config.yaml"
DB = BASE / "data" / "logs.db"
SESSIONS = BASE / "sessions"
BOT = "@zakadeep_bot"
MESSAGE = "/checkin"
ACCOUNTS = [f"account{i}" for i in range(1, 8)]  # 7 个号，名字固定，登录后才有 session

app = FastAPI(title="tg-checkin Web 账号池")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
scheduler = AsyncIOScheduler()
qr_sessions = {}  # name -> {client, qr_login, token, expires, status}

def load_cfg():
    if not CONFIG.exists():
        return {}
    return yaml.safe_load(open(CONFIG)) or {}

def save_cfg(cfg):
    CONFIG.write_text(yaml.safe_dump(cfg, allow_unicode=True))
    os.chmod(CONFIG, 0o600)

def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, ts TEXT, account TEXT, ok INTEGER, reply TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT)")
    c.commit()
    return c

def log(account, ok, reply):
    c = db(); c.execute("INSERT INTO logs(ts,account,ok,reply) VALUES(?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), account, 1 if ok else 0, reply or ""))
    c.commit(); c.close()

def account_status(name):
    return "已登录" if (SESSIONS / f"{name}.session").exists() else "未登录"

async def do_checkin(name, cfg):
    """单号签到：发 /checkin，等 8 秒，取机器人最新回复"""
    if not (SESSIONS / f"{name}.session").exists():
        log(name, False, "未登录，跳过"); return {"account": name, "ok": False, "reply": "未登录"}
    client = TelegramClient(str(SESSIONS / name), cfg["api_id"], cfg["api_hash"])
    await client.connect()
    try:
        if not await client.is_user_authorized():
            log(name, False, "会话失效，需重新登录"); return {"account": name, "ok": False, "reply": "会话失效"}
        await client.send_message(BOT, MESSAGE)
        await asyncio.sleep(8)
        msgs = [m async for m in client.iter_messages(BOT, limit=3)]
        reply = msgs[0].text if msgs else "无回复"
        # 只取机器人那条，不是自己发的
        for m in msgs:
            if m.text and m.text != MESSAGE:
                reply = m.text; break
        log(name, True, reply)
        return {"account": name, "ok": True, "reply": reply}
    finally:
        await client.disconnect()

async def run_all_checkin():
    cfg = load_cfg()
    if not cfg.get("api_id") or not cfg.get("api_hash"):
        return {"ok": False, "error": "请先在设置里填 api_id / api_hash"}
    results = []
    first = True
    for name in ACCOUNTS:
        if not first:
            await asyncio.sleep(random.randint(30, 120))
        first = False
        results.append(await do_checkin(name, cfg))
    return {"ok": True, "results": results}

@app.on_event("startup")
async def startup():
    db().close()
    # 默认定时：每天 00:01
    scheduler.add_job(lambda: asyncio.create_task(run_all_checkin()), "cron", hour=0, minute=1, id="daily")
    scheduler.start()

@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")

@app.get("/api/accounts")
def accounts():
    return [{"name": n, "status": account_status(n)} for n in ACCOUNTS]

class CfgIn(BaseModel):
    api_id: int
    api_hash: str

@app.post("/api/settings")
def settings(inp: CfgIn):
    save_cfg({"api_id": inp.api_id, "api_hash": inp.api_hash})
    return {"ok": True}

@app.get("/api/settings")
def get_settings():
    cfg = load_cfg()
    return {"configured": bool(cfg.get("api_id")), "api_id": cfg.get("api_id")}

@app.post("/api/qr/{name}")
async def qr_start(name: str):
    cfg = load_cfg()
    if not cfg.get("api_id"):
        raise HTTPException(400, "请先填 api_id / api_hash")
    client = TelegramClient(str(SESSIONS / name), cfg["api_id"], cfg["api_hash"])
    await client.connect()
    qr_login = await client.qr_login()
    # 生成二维码图
    import qrcode
    img = BASE / "static" / f"qr_{name}.png"
    qrcode.make(qr_login.url).save(img)
    qr_sessions[name] = {"client": client, "qr_login": qr_login}
    return {"ok": True, "qr_url": f"/static/qr_{name}.png", "note": "请用手机 Telegram 设置→设备→关联桌面设备马上扫，过期请重新点生成"}

@app.get("/api/qr/{name}/status")
async def qr_status(name: str):
    s = qr_sessions.get(name)
    if not s:
        return {"status": "未开始"}
    try:
        # 非阻塞轮询一次：若已扫码，qr_login 会完成
        await asyncio.wait_for(s["qr_login"].wait(), timeout=2)
        await s["client"].disconnect()
        qr_sessions.pop(name, None)
        return {"status": "已登录", "account": name}
    except asyncio.TimeoutError:
        return {"status": "等待扫码"}
    except Exception as e:
        return {"status": f"失败: {e}"}

@app.post("/api/checkin")
async def checkin_all():
    return await run_all_checkin()

@app.post("/api/checkin/{name}")
async def checkin_one(name: str):
    cfg = load_cfg()
    return await do_checkin(name, cfg)

@app.get("/api/logs")
def logs(limit: int = 50):
    c = db()
    rows = c.execute("SELECT ts,account,ok,reply FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return [{"ts": r[0], "account": r[1], "ok": bool(r[2]), "reply": r[3]} for r in rows]

@app.get("/api/schedule")
def schedule():
    job = scheduler.get_job("daily")
    return {"daily": "每天 00:01" if job else "未设置", "next": str(job.next_run_time) if job else ""}

@app.get("/api/health")
def health():
    return {"ok": True, "bot": BOT, "message": MESSAGE, "accounts": len(ACCOUNTS)}
