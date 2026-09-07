# Robinhood Chain Tracker Bot

Bot Telegram untuk **memantau** token di Robinhood Chain (chain id `4663`) —
bukan bot yang mempromosikan atau menjanjikan harga akan naik. Semua data
diambil apa adanya dari DexScreener (data pasar) dan langsung dari chain lewat
RPC (untuk rug-check kasar).

## Fitur
- `/watch <contract>` — pantau token, dapat alert otomatis kalau harga bergerak tajam (default: ±20% dalam 5 menit)
- `/unwatch <contract>` — berhenti pantau
- `/list` — daftar token yang dipantau di chat itu
- `/check <contract>` — harga, likuiditas, volume, dan rug-check kontrak (cek fungsi mint/owner/blacklist)
- `/new` — pair baru di Robinhood Chain dengan likuiditas di atas threshold
- `/news` — rekap headline terbaru soal Robinhood Chain

## Batasan penting (baca dulu)
- Bot ini **tidak** memberi rekomendasi beli/jual dan **tidak** memprediksi harga.
- Rug-check bersifat **heuristik** (mendeteksi pola bytecode umum seperti fungsi
  mint/blacklist), **bukan** audit keamanan resmi. Jangan jadikan satu-satunya
  dasar keputusan.
- Memecoin sangat spekulatif — mayoritas berakhir turun tajam atau ke nol.
  Jangan investasikan uang yang tidak sanggup kamu rugikan.

## Langkah wajib (cuma ini yang harus kamu lakukan sendiri)

1. Buka [@BotFather](https://t.me/BotFather) di Telegram → `/newbot` → ikuti instruksinya → **copy token** yang diberikan.
   (Ini nggak bisa diwakilkan siapa pun — token itu kredensial akun kamu.)
2. *(Opsional, buat aktifkan rug-check)* Daftar gratis di [Alchemy](https://www.alchemy.com/),
   buat app baru → pilih network **Robinhood Chain** → copy RPC URL-nya.

Setelah punya token itu, tinggal pilih SALAH SATU cara deploy di bawah — nggak perlu ngerti coding.

## Cara termudah: Railway (gratis, 24/7, tanpa VPS)

1. Push folder ini ke repo GitHub baru (atau upload lewat Railway CLI).
2. Buka [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → pilih repo ini.
   Railway otomatis pakai `Dockerfile` yang sudah disiapkan.
3. Di tab **Variables**, tambahkan:
   - `TELEGRAM_BOT_TOKEN` = token dari BotFather
   - `ROBINHOOD_RPC_URL` = RPC dari Alchemy (opsional)
4. Deploy. Selesai — bot langsung jalan 24/7, restart otomatis kalau error.

## Cara alternatif: VPS sendiri pakai Docker

```bash
cp .env.example .env
nano .env   # isi TELEGRAM_BOT_TOKEN (dan ROBINHOOD_RPC_URL kalau mau)
docker compose up -d --build
```
Cek log: `docker compose logs -f`. Bot otomatis restart kalau server reboot (`restart: unless-stopped`).

## Cara manual (tanpa Docker)

```bash
cp .env.example .env
nano .env
pip install -r requirements.txt
export $(cat .env | xargs)
python bot.py
```
Untuk 24/7 tanpa Docker, jalankan lewat `systemd`, `pm2`, atau `tmux`/`screen` di VPS.

## Struktur file
```
bot.py              # logic bot
requirements.txt    # dependency Python
.env.example         # contoh konfigurasi (copy jadi .env, isi token)
Dockerfile           # buat containerize
docker-compose.yml   # buat jalan gampang di VPS sendiri
railway.json         # config auto-deploy Railway
watchlist.db         # dibuat otomatis (SQLite) saat bot pertama kali jalan
```
