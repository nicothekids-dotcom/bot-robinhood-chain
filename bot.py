"""
Robinhood Chain Token Tracker Bot (Telegram)
=============================================

Fitur:
  /watch <contract_address>   - mulai pantau token (alert harga/volume otomatis)
  /unwatch <contract_address> - berhenti pantau token
  /list                       - daftar token yang sedang dipantau di chat ini
  /check <contract_address>   - cek cepat: harga, likuiditas, volume, & rug-check kontrak
  /new                        - lihat pair baru di Robinhood Chain dgn likuiditas > threshold
  /news                       - rekap berita terbaru terkait Robinhood Chain

PENTING:
  Bot ini HANYA menyajikan data on-chain & data pasar apa adanya.
  Bot ini TIDAK memberi rekomendasi beli/jual dan TIDAK memprediksi harga akan naik/turun.
  Memecoin sangat spekulatif & berisiko tinggi (termasuk risiko rug pull dan
  volatilitas ekstrem). Selalu DYOR (Do Your Own Research).
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

try:
    from web3 import Web3
except ImportError:  # web3 dipakai hanya untuk rug-check on-chain
    Web3 = None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("rh-tracker-bot")

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
RPC_URL = os.environ.get("ROBINHOOD_RPC_URL", "")  # contoh: endpoint Alchemy Robinhood Chain
DEXSCREENER_CHAIN = "robinhood"
DEXSCREENER_BASE = "https://api.dexscreener.com"

PRICE_CHANGE_ALERT_PCT = float(os.environ.get("PRICE_CHANGE_ALERT_PCT", "20"))  # alert jika |Δ 5m| >= ini
NEW_PAIR_MIN_LIQUIDITY_USD = float(os.environ.get("NEW_PAIR_MIN_LIQUIDITY_USD", "10000"))
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "180"))

# Kriteria filter /gems (market cap di rentang tertentu + volume tinggi relatif ke market cap)
GEMS_MIN_MARKET_CAP_USD = float(os.environ.get("GEMS_MIN_MARKET_CAP_USD", "500000"))   # $500rb
GEMS_MAX_MARKET_CAP_USD = float(os.environ.get("GEMS_MAX_MARKET_CAP_USD", "1000000"))  # $1jt
GEMS_MIN_LIQUIDITY_USD = float(os.environ.get("GEMS_MIN_LIQUIDITY_USD", "15000"))
GEMS_MIN_VOLUME_TO_MCAP_RATIO = float(os.environ.get("GEMS_MIN_VOLUME_TO_MCAP_RATIO", "0.3"))  # vol24h >= 30% mcap

DB_PATH = os.environ.get("DB_PATH", "watchlist.db")

DISCLAIMER = (
    "\n\n⚠️ _Data pasar saja, bukan saran finansial. Memecoin berisiko tinggi, "
    "termasuk risiko rug pull & harga anjlok mendadak. DYOR._"
)

# Selector fungsi umum yang relevan untuk rug-check kasar (4-byte function selectors)
MINT_SELECTORS = {
    "40c10f19": "mint(address,uint256)",
    "a0712d68": "mint(uint256)",
}
OWNER_SELECTORS = {
    "8da5cb5b": "owner()",
}
BLACKLIST_SELECTORS = {
    "f9f92be4": "blacklist(address)",
    "537df3b6": "setBlacklist(address,bool)",
}

# ---------------------------------------------------------------------------
# Penyimpanan sederhana (SQLite) untuk daftar token yang dipantau per chat
# ---------------------------------------------------------------------------

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS watchlist (
            chat_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            last_price REAL,
            PRIMARY KEY (chat_id, address)
        )"""
    )
    return conn


def add_watch(chat_id: int, address: str):
    conn = db_conn()
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (chat_id, address, last_price) VALUES (?, ?, NULL)",
        (chat_id, address.lower()),
    )
    conn.commit()
    conn.close()


def remove_watch(chat_id: int, address: str):
    conn = db_conn()
    conn.execute(
        "DELETE FROM watchlist WHERE chat_id=? AND address=?",
        (chat_id, address.lower()),
    )
    conn.commit()
    conn.close()


def list_watch(chat_id: int):
    conn = db_conn()
    rows = conn.execute(
        "SELECT address FROM watchlist WHERE chat_id=?", (chat_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def all_watch_rows():
    conn = db_conn()
    rows = conn.execute("SELECT chat_id, address, last_price FROM watchlist").fetchall()
    conn.close()
    return rows


def update_last_price(chat_id: int, address: str, price: float):
    conn = db_conn()
    conn.execute(
        "UPDATE watchlist SET last_price=? WHERE chat_id=? AND address=?",
        (price, chat_id, address.lower()),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# DexScreener helpers
# ---------------------------------------------------------------------------

def fetch_token_pairs(token_address: str):
    """Ambil semua pair untuk sebuah token address di Robinhood Chain."""
    url = f"{DEXSCREENER_BASE}/token-pairs/v1/{DEXSCREENER_CHAIN}/{token_address}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_new_pairs_search(query: str = "robinhood"):
    """Cari pair terbaru di Robinhood Chain lewat endpoint search DexScreener."""
    url = f"{DEXSCREENER_BASE}/latest/dex/search"
    r = requests.get(url, params={"q": query}, timeout=15)
    r.raise_for_status()
    data = r.json()
    pairs = [p for p in data.get("pairs", []) if p.get("chainId") == DEXSCREENER_CHAIN]
    pairs.sort(key=lambda p: p.get("pairCreatedAt", 0), reverse=True)
    return pairs


def format_pair_summary(pair: dict) -> str:
    base = pair.get("baseToken", {})
    price_usd = pair.get("priceUsd", "?")
    liq = pair.get("liquidity", {}).get("usd", 0)
    vol24 = pair.get("volume", {}).get("h24", 0)
    chg5m = pair.get("priceChange", {}).get("m5", 0)
    chg1h = pair.get("priceChange", {}).get("h1", 0)
    chg24h = pair.get("priceChange", {}).get("h24", 0)
    url = pair.get("url", "")
    return (
        f"*{base.get('symbol', '?')}* ({base.get('name', '')})\n"
        f"Kontrak: `{base.get('address', '')}`\n"
        f"Harga: ${price_usd}\n"
        f"Likuiditas: ${liq:,.0f} | Volume 24h: ${vol24:,.0f}\n"
        f"Δ 5m: {chg5m}% | Δ 1h: {chg1h}% | Δ 24h: {chg24h}%\n"
        f"[Lihat di DexScreener]({url})"
    )


# ---------------------------------------------------------------------------
# Rug-check on-chain sederhana (heuristik, BUKAN audit lengkap)
# ---------------------------------------------------------------------------

def rug_check(token_address: str) -> str:
    if not RPC_URL or Web3 is None:
        return (
            "Rug-check on-chain tidak aktif (RPC/web3 belum dikonfigurasi). "
            "Set ROBINHOOD_RPC_URL di .env untuk mengaktifkan."
        )

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    try:
        code = w3.eth.get_code(Web3.to_checksum_address(token_address)).hex()
    except Exception as e:
        return f"Gagal membaca kontrak: {e}"

    if code in ("0x", ""):
        return "⚠️ Alamat ini bukan smart contract (tidak ada bytecode)."

    findings = []
    hex_code = code.lower()

    def has_selector(selectors: dict) -> list:
        return [name for sel, name in selectors.items() if sel in hex_code]

    mints = has_selector(MINT_SELECTORS)
    owners = has_selector(OWNER_SELECTORS)
    blacklists = has_selector(BLACKLIST_SELECTORS)

    if mints:
        findings.append(f"🔴 Ditemukan fungsi mint: {', '.join(mints)} → supply bisa ditambah kapan saja.")
    else:
        findings.append("🟢 Tidak terdeteksi fungsi mint publik yang umum.")

    if owners:
        findings.append(f"🟡 Kontrak punya fungsi owner(): {', '.join(owners)} → cek apakah ownership sudah di-renounce.")
    else:
        findings.append("🟢 Tidak terdeteksi pola owner() standar (bisa juga custom/renounced).")

    if blacklists:
        findings.append(f"🔴 Ditemukan fungsi blacklist: {', '.join(blacklists)} → pemilik bisa memblokir wallet tertentu.")

    findings.append(
        "\nCatatan: ini heuristik berbasis pola bytecode, bukan audit resmi. "
        "Selalu verifikasi source code kontrak (jika verified) sebelum transaksi besar."
    )
    return "\n".join(findings)


# ---------------------------------------------------------------------------
# Telegram command handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Aku memantau token di *Robinhood Chain* (chain id 4663).\n\n"
        "Perintah:\n"
        "/watch <contract> - pantau token, alert otomatis kalau harga bergerak tajam\n"
        "/unwatch <contract> - stop pantau\n"
        "/list - daftar token yang dipantau\n"
        "/check <contract> - cek harga, likuiditas & rug-check cepat\n"
        "/new - pair baru dgn likuiditas signifikan\n"
        "/gems - token mcap kecil + volume tinggi (BUKAN prediksi harga naik)\n"
        "/news - rekap berita Robinhood Chain terbaru"
        + DISCLAIMER,
        parse_mode="Markdown",
    )


async def watch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Pakai format: /watch 0xAlamatKontrak")
        return
    address = context.args[0]
    add_watch(update.effective_chat.id, address)
    await update.message.reply_text(f"✅ Mulai memantau `{address}`.", parse_mode="Markdown")


async def unwatch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Pakai format: /unwatch 0xAlamatKontrak")
        return
    address = context.args[0]
    remove_watch(update.effective_chat.id, address)
    await update.message.reply_text(f"🛑 Berhenti memantau `{address}`.", parse_mode="Markdown")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    addrs = list_watch(update.effective_chat.id)
    if not addrs:
        await update.message.reply_text("Belum ada token yang dipantau di chat ini.")
        return
    await update.message.reply_text("Token yang dipantau:\n" + "\n".join(f"`{a}`" for a in addrs), parse_mode="Markdown")


async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Pakai format: /check 0xAlamatKontrak")
        return
    address = context.args[0]
    await update.message.reply_text("🔎 Mengambil data...")

    try:
        pairs = fetch_token_pairs(address)
    except Exception as e:
        await update.message.reply_text(f"Gagal ambil data DexScreener: {e}")
        return

    if not pairs:
        await update.message.reply_text("Tidak ditemukan pair untuk kontrak ini di Robinhood Chain.")
        return

    top_pair = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0))
    summary = format_pair_summary(top_pair)
    rug = rug_check(address)

    await update.message.reply_text(
        summary + "\n\n*Rug-check:*\n" + rug + DISCLAIMER,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Mencari pair baru di Robinhood Chain...")
    try:
        pairs = fetch_new_pairs_search()
    except Exception as e:
        await update.message.reply_text(f"Gagal ambil data: {e}")
        return

    filtered = [p for p in pairs if p.get("liquidity", {}).get("usd", 0) >= NEW_PAIR_MIN_LIQUIDITY_USD][:5]
    if not filtered:
        await update.message.reply_text("Belum ada pair baru dengan likuiditas signifikan saat ini.")
        return

    for p in filtered:
        await update.message.reply_text(
            format_pair_summary(p) + DISCLAIMER,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        await asyncio.sleep(0.3)


async def gems_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🔎 Mencari token dengan market cap ${GEMS_MIN_MARKET_CAP_USD:,.0f}–${GEMS_MAX_MARKET_CAP_USD:,.0f} "
        "& volume trading tinggi...\n"
        "⚠️ Ini BUKAN prediksi harga naik, cuma filter pola likuiditas & volume."
    )
    try:
        pairs = fetch_new_pairs_search()
    except Exception as e:
        await update.message.reply_text(f"Gagal ambil data: {e}")
        return

    candidates = []
    for p in pairs:
        liq = p.get("liquidity", {}).get("usd", 0) or 0
        mcap = p.get("marketCap") or p.get("fdv") or 0
        vol24h = p.get("volume", {}).get("h24", 0) or 0
        chg1h = p.get("priceChange", {}).get("h1", 0) or 0
        chg24h = p.get("priceChange", {}).get("h24", 0) or 0

        if not mcap or mcap <= 0:
            continue
        if mcap < GEMS_MIN_MARKET_CAP_USD or mcap > GEMS_MAX_MARKET_CAP_USD:
            continue
        if liq < GEMS_MIN_LIQUIDITY_USD:
            continue
        vol_to_mcap = vol24h / mcap if mcap > 0 else 0
        if vol_to_mcap < GEMS_MIN_VOLUME_TO_MCAP_RATIO:
            continue
        # cari yang momentumnya positif di 1h & 24h (bukan cuma nyangkut, tapi bukan kepastian juga)
        if chg1h <= 0 or chg24h <= 0:
            continue

        candidates.append((p, vol_to_mcap))

    candidates.sort(key=lambda x: x[1], reverse=True)
    candidates = candidates[:5]

    if not candidates:
        await update.message.reply_text(
            "Belum ada token yang cocok kriteria saat ini (mcap kecil + volume tinggi + momentum positif). "
            "Coba lagi beberapa saat lagi."
        )
        return

    for p, ratio in candidates:
        mcap = p.get("marketCap") or p.get("fdv") or 0
        text = (
            format_pair_summary(p)
            + f"\nMarket Cap: ${mcap:,.0f} | Vol24h/MCap: {ratio:.2f}x"
            + DISCLAIMER
        )
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
        await asyncio.sleep(0.3)


NEWS_FEEDS = [
    "https://decrypt.co/feed",
    "https://cryptobriefing.com/feed/",
]


async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📰 Mengambil berita terbaru...")
    import xml.etree.ElementTree as ET

    items_out = []
    for feed_url in NEWS_FEEDS:
        try:
            r = requests.get(feed_url, timeout=10)
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                title = item.findtext("title", default="")
                link = item.findtext("link", default="")
                if "robinhood" in title.lower() or "robinhood" in (item.findtext("description", "") or "").lower():
                    items_out.append(f"• [{title}]({link})")
                if len(items_out) >= 5:
                    break
        except Exception as e:
            logger.warning(f"Gagal ambil feed {feed_url}: {e}")
        if len(items_out) >= 5:
            break

    if not items_out:
        await update.message.reply_text(
            "Tidak ada berita Robinhood Chain terbaru dari feed yang dipantau saat ini. "
            "Coba cek langsung di decrypt.co atau cryptobriefing.com."
        )
        return

    await update.message.reply_text(
        "*Berita terbaru Robinhood Chain:*\n" + "\n".join(items_out),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# ---------------------------------------------------------------------------
# Background job: cek perubahan harga untuk semua token yang dipantau
# ---------------------------------------------------------------------------

async def poll_watchlist(context: ContextTypes.DEFAULT_TYPE):
    rows = all_watch_rows()
    # kelompokkan per address supaya tidak fetch berkali-kali
    by_address = {}
    for chat_id, address, last_price in rows:
        by_address.setdefault(address, []).append((chat_id, last_price))

    for address, watchers in by_address.items():
        try:
            pairs = fetch_token_pairs(address)
        except Exception as e:
            logger.warning(f"Gagal poll {address}: {e}")
            continue
        if not pairs:
            continue

        top_pair = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0))
        chg5m = top_pair.get("priceChange", {}).get("m5", 0) or 0

        if abs(chg5m) >= PRICE_CHANGE_ALERT_PCT:
            summary = format_pair_summary(top_pair)
            for chat_id, _ in watchers:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚨 *Pergerakan harga signifikan!*\n\n{summary}{DISCLAIMER}",
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    logger.warning(f"Gagal kirim alert ke {chat_id}: {e}")

        try:
            price = float(top_pair.get("priceUsd", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0
        for chat_id, _ in watchers:
            update_last_price(chat_id, address, price)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diset. Lihat file .env.example")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("watch", watch_cmd))
    app.add_handler(CommandHandler("unwatch", unwatch_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("new", new_cmd))
    app.add_handler(CommandHandler("gems", gems_cmd))
    app.add_handler(CommandHandler("news", news_cmd))

    app.job_queue.run_repeating(poll_watchlist, interval=POLL_INTERVAL_SECONDS, first=15)

    logger.info("Bot berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
