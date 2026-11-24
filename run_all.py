import os
import sys
import subprocess
import time
import asyncio
import base64

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("ULTIMATE BYPASS")
    except Exception:
        pass

from aiohttp import web
import aiohttp

def _dec(b: str) -> str:
    try:
        return base64.b64decode(b).decode()
    except Exception:
        return b

BOT_CONFIGS = [
    {
        "name": "Bot V4 (ULTIMATE BYPASS - LUNOX)",
        "env": {
            "DISCORD_TOKEN": os.getenv("TOKEN_V4", _dec("TVRVM05EQTVNVFl3T1RrMU9EWTFNems0TWcuR0F6Rm1GLkRNZDFOZFhHQ3BRRjVDU3RXcXJpUFAxcmZoSUtBYXpFZTdUdHAw")),
            "API_KEY": os.getenv("API_KEY_V4", "AK-FF-ECE4-728C-8BDC-31C6"),
            "OWNER_ID": "1530209496570532041",
            "OWNER_IDS": "1530209496570532041,1196299411916075048,1378068938847424522",
            "PANEL_CHANNEL_ID": "1574100611081838763",
            "GUILD_ID": "0",
            "RECHARGE_CONTACT_ID": "1530209496570532041",
            "CLIENT_ROLE_NAME": "ULTIMATE LIB",
            "DB_FILE": "db_v4.db",
            "ENABLE_WEB_SERVER": "0"
        }
    },
    {
        "name": "Bot V3 (LEGACY BYPASS)",
        "env": {
            "DISCORD_TOKEN": os.getenv("TOKEN_V3", _dec("TVRVM01ERXhOVE0zTWpFNE5UZ3hOekl6T1EuR3BQbkJqLjBQem5UcXFxa3RER2p1M2lnS1N1cDZQeWV0T1F0MXlmdEVqd0JZ")),
            "API_KEY": os.getenv("API_KEY_V3", "AK-FF-300D-7842-11C7-7FDE"),
            "OWNER_ID": "1551003408226459693",
            "OWNER_IDS": "1551003408226459693,1378068938847424522,1559978348103471275",
            "PANEL_CHANNEL_ID": "1570102018519990443",
            "GUILD_ID": "1559978348103471275",
            "RECHARGE_CONTACT_ID": "1551003408226459693",
            "CLIENT_ROLE_NAME": "LIB V2",
            "DB_FILE": "db_v3.db",
            "ENABLE_WEB_SERVER": "0"
        }
    },
    {
        "name": "Bot V2 (ULTIMATE BYPASS)",
        "env": {
            "DISCORD_TOKEN": os.getenv("TOKEN_V2", _dec("TVRVMU5qSTROVGt3TXpjd09EYzFPREEwTmcuR056alRnLkE3LVNrUm5nY3VSdVRvUGctamNHdF8zMGFxcWFxcDBiMTBxQ1Zv")),
            "API_KEY": os.getenv("API_KEY_V2", "AK-FF-ECE4-728C-8BDC-31C6"),
            "OWNER_ID": "1387094143037214724",
            "OWNER_IDS": "1387094143037214724,1378068938847424522",
            "PANEL_CHANNEL_ID": "1569406975333109760",
            "GUILD_ID": "1569406047733424211",
            "RECHARGE_CONTACT_ID": "1387094143037214724",
            "CLIENT_ROLE_NAME": "LIB V2",
            "DB_FILE": "db_v2.db",
            "ENABLE_WEB_SERVER": "0"
        }
    },
    {
        "name": "Bot V1 (BYPASS CLIENT)",
        "env": {
            "DISCORD_TOKEN": os.getenv("TOKEN_V1", _dec("TVRVMk9UUXhOalU1T1RBNU1qVTVOamczTncuRzYzbmY4LlpuTGJKalV3SnlDd0FqOXF5TEFCbWF1dXREZ09QTXRBY0x5X204")),
            "API_KEY": os.getenv("API_KEY_V1", "AK-FF-0078-5B26-7C2B-7FC6"),
            "OWNER_ID": "1378068938847424522",
            "OWNER_IDS": "1378068938847424522",
            "PANEL_CHANNEL_ID": "1569416063932698624",
            "GUILD_ID": "1569415110961668126",
            "RECHARGE_CONTACT_ID": "1378068938847424522",
            "CLIENT_ROLE_NAME": "BYPASS CLIENT",
            "DB_FILE": "db_v1.db",
            "ENABLE_WEB_SERVER": "0"
        }
    }
]

processes = {}

def start_bot(config):
    name = config["name"]
    env = os.environ.copy()
    env.setdefault("GH_TOKEN", os.getenv("GH_TOKEN", ""))
    env.setdefault("GH_REPO", os.getenv("GH_REPO", "Kanha140/lib-bypass-v3"))
    env.setdefault("GH_BRANCH", os.getenv("GH_BRANCH", "db-data"))
    env.update(config["env"])
    script_path = os.path.join(os.path.dirname(__file__), "main.py")
    p = subprocess.Popen(
        [sys.executable, "-u", script_path],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f"[+] Started {name} (PID: {p.pid})", flush=True)
    return p

async def handle_status(request):
    status_report = {}
    for cfg in BOT_CONFIGS:
        name = cfg["name"]
        p = processes.get(name)
        status_report[name] = "ONLINE" if (p and p.poll() is None) else "RESTARTING"
    return web.json_response({
        "status": "online",
        "service": "All 3 Discord Bots Running 24/7",
        "bots": status_report
    })

async def self_ping_loop():
    url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KEEP_ALIVE_URL")
    if not url:
        return
    print(f"[*] Starting 24/7 Self-Ping Keep-Alive for {url}", flush=True)
    while True:
        await asyncio.sleep(600)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    print(f"[Keep-Alive] Self-ping status {resp.status}", flush=True)
        except Exception as e:
            print(f"[Keep-Alive] Warning: {e}", flush=True)

async def periodic_cloud_sync_loop():
    import cloud_sync
    dbs = ["db_v1.db", "db_v2.db", "db_v3.db", "db_v4.db", "bot_database.db"]
    while True:
        await asyncio.sleep(300)
        try:
            for db in dbs:
                p = os.path.join(os.path.dirname(__file__), db)
                if os.path.exists(p):
                    cs = cloud_sync.CloudSync(p)
                    await asyncio.to_thread(cs.push_to_cloud)
        except Exception as e:
            print(f"[PeriodicSync] Error: {e}", flush=True)

async def monitor_bots():
    while True:
        for cfg in BOT_CONFIGS:
            name = cfg["name"]
            p = processes.get(name)
            if p is None or p.poll() is not None:
                print(f"[!] {name} stopped. Restarting...", flush=True)
                processes[name] = start_bot(cfg)
        await asyncio.sleep(10)

async def main():
    # Start all 3 bots
    for cfg in BOT_CONFIGS:
        processes[cfg["name"]] = start_bot(cfg)

    # Start Web Server on PORT for Render
    app = web.Application()
    app.router.add_get("/", handle_status)
    app.router.add_get("/health", handle_status)
    app.router.add_get("/healthz", handle_status)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[*] Multi-Bot Supervisor HTTP Server listening on port {port}", flush=True)

    # Run monitor, self ping and cloud persistence sync
    await asyncio.gather(
        monitor_bots(),
        self_ping_loop(),
        periodic_cloud_sync_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        for p in processes.values():
            p.terminate()
