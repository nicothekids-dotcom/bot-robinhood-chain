# Tutorial: Cara Menjalankan Bot Robinhood Chain (Buat Pemula Banget)

Panduan ini ditulis buat kamu yang **belum pernah coding sama sekali**. Ikuti
urut dari atas, jangan diloncat-loncat. Total waktu: sekitar 15-20 menit.

---

## Bagian 1: Bikin "Akun" untuk Bot Kamu di Telegram

Bot Telegram itu butuh semacam "kunci rahasia" (namanya **token**) supaya bisa
aktif. Kita ambil kunci ini dari bot resmi Telegram bernama **BotFather**.

1. Buka aplikasi Telegram kamu (HP atau laptop, bebas).
2. Di kolom pencarian, ketik: `BotFather`
3. Cari yang ada centang biru (akun resmi Telegram), lalu tap.
4. Tap tombol **START** (atau ketik `/start`).
5. Ketik: `/newbot`
6. BotFather akan tanya **nama bot** — ini nama yang muncul di chat, bebas mau
   apa. Contoh: `Bot Pantau Robinhood Chain`
7. BotFather akan tanya **username bot** — ini HARUS unik dan HARUS diakhiri
   kata `bot`. Contoh: `rhpantau_bot` atau `pantaukoinku_bot`.
   Kalau muncul pesan "sorry, this username is already taken", coba nama lain.
8. Kalau berhasil, BotFather akan kasih pesan berisi tulisan panjang yang
   diawali angka, contoh:
   ```
   123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
   ```
   **Ini adalah token kamu.** Copy dan simpan di Notes/catatan HP kamu.
   ⚠️ **Jangan share token ini ke siapa pun** — siapa pun yang punya token ini
   bisa mengendalikan bot kamu, sama kayak password.

Selesai bagian 1! Kamu sudah punya bot, cuma belum "hidup" (belum bisa jawab
apa-apa) karena belum kita jalankan programnya.

---

## Bagian 2: Siapkan Tempat Bot-nya "Hidup" 24 Jam

Program bot-nya perlu komputer yang nyala terus supaya bot bisa balas chat
kapan saja, bukan cuma pas laptop kamu nyala. Kita pakai layanan gratis
bernama **Railway** yang akan menjalankan program itu untuk kita.

### Langkah 2.1 — Bikin akun GitHub (tempat naruh file program)

1. Buka [github.com](https://github.com) di browser.
2. Klik **Sign up**, daftar pakai email kamu (gratis).
3. Verifikasi email kalau diminta.

### Langkah 2.2 — Upload file bot ke GitHub

1. Setelah login, klik tombol **+** di pojok kanan atas → **New repository**.
2. Isi **Repository name**, contoh: `bot-robinhood-chain`
3. Biarkan pilihan **Public** (default).
4. Klik **Create repository**.
5. Di halaman baru, cari tulisan **"uploading an existing file"** (link biru,
   biasanya ada di tengah halaman) → klik.
6. Sekarang buka folder bot yang aku kasih tadi di komputer kamu. **Seret
   (drag) semua file** di dalam folder itu (bot.py, requirements.txt,
   Dockerfile, dst — KECUALI file `.env.example`, tapi kalau ikut ke-upload
   juga tidak masalah) ke kotak upload di GitHub.
7. Scroll ke bawah, klik tombol hijau **Commit changes**.

Selesai — file bot kamu sekarang ada di internet (di GitHub), siap dipakai
Railway.

### Langkah 2.3 — Bikin akun Railway & sambungkan ke GitHub

1. Buka [railway.app](https://railway.app)
2. Klik **Login** → pilih **Login with GitHub** → izinkan aksesnya.
3. Setelah masuk, klik **New Project**.
4. Pilih **Deploy from GitHub repo**.
5. Cari dan klik repo yang tadi kamu buat (`bot-robinhood-chain`).
6. Railway otomatis mulai "membangun" bot kamu (proses ini beberapa menit,
   biarkan saja, jangan ditutup dulu).

### Langkah 2.4 — Masukkan token bot ke Railway

Ini bagian PENTING supaya bot kamu bisa nyala.

1. Di halaman project Railway, klik kotak/card bot kamu.
2. Cari tab **Variables** (biasanya di bagian atas atau samping).
3. Klik **New Variable**.
4. Di kolom **Name**, ketik persis: `TELEGRAM_BOT_TOKEN`
5. Di kolom **Value**, tempel (paste) token yang kamu simpan dari Bagian 1.
6. Klik **Add** / **Save**.
7. Railway akan otomatis restart bot kamu dengan token itu. Tunggu sekitar
   1-2 menit sampai statusnya jadi **Active** / lingkaran hijau.

🎉 **Bot kamu sekarang hidup 24 jam!**

---

## Bagian 3: Coba Bot Kamu di Telegram

1. Buka Telegram, cari username bot kamu (yang diakhiri `_bot` tadi).
2. Tap **START**.
3. Bot akan balas dengan daftar perintah yang bisa dipakai.
4. Coba ketik:
   ```
   /new
   ```
   Bot akan kasih daftar token/memecoin baru di Robinhood Chain.
5. Coba juga:
   ```
   /check 0xAlamatKontrakToken
   ```
   (ganti `0xAlamatKontrakToken` dengan alamat token yang mau kamu cek —
   bisa kamu dapat dari [dexscreener.com/robinhood](https://dexscreener.com/robinhood),
   klik salah satu koin, lalu copy alamat kontraknya)

---

## Bagian 4 (Opsional): Aktifkan Fitur "Rug-Check"

Fitur ini mengecek apakah kontrak token punya fungsi mencurigakan (misalnya
bisa cetak koin baru sesuka pemiliknya). Kalau kamu skip bagian ini, bot tetap
jalan normal, cuma fitur `/check` bagian rug-check-nya akan bilang "belum
aktif".

1. Buka [alchemy.com](https://www.alchemy.com), daftar akun gratis.
2. Setelah login, klik **Create new app**.
3. Di pilihan **Chain**, cari dan pilih **Robinhood Chain**.
4. Setelah dibuat, klik app itu, cari tombol **API Key** atau **View Key**,
   copy yang bagian **HTTPS URL** (biasanya diawali `https://robinhood-mainnet...`).
5. Balik ke Railway → tab **Variables** → **New Variable**:
   - Name: `ROBINHOOD_RPC_URL`
   - Value: (tempel URL dari Alchemy)
6. Save, tunggu bot restart.

---

## Kalau Ada Masalah

- **Bot tidak balas sama sekali** → cek di Railway tab **Deployments**, klik
  yang terbaru, lihat **Logs**. Kalau ada tulisan merah/error, biasanya
  tokennya salah ketik — cek lagi Bagian 2.4.
- **"This username is already taken" pas bikin bot** → coba nama username
  lain, harus unik sedunia.
- **Railway minta kartu kredit** → Railway punya jatah gratis bulanan; kalau
  diminta upgrade, itu cuma karena kamu sudah pakai lebih dari jatah gratis
  (jarang terjadi untuk bot sekecil ini).

---

## Yang Perlu Diingat

Bot ini cuma nampilin data — harga, likuiditas, dan cek kontrak. **Bot ini
tidak pernah bilang "beli sekarang" atau "pasti naik"**, karena memang tidak
ada yang bisa memastikan itu. Memecoin itu judi berisiko tinggi — banyak yang
harganya jatuh ke nol dalam hitungan jam. Jangan pakai uang yang kamu tidak
sanggup kehilangan sepenuhnya.
