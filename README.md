1. Script Streaming Utama (streamer.py)
Ini adalah script Python yang akan menangani logika streaming video Anda menggunakan FFmpeg.

2. File Konfigurasi Script Streaming (config.json)
File ini berisi pengaturan khusus untuk operasi streaming itu sendiri, seperti URL RTMP, ekstensi video yang didukung, dan bitrate.

3. Script Bot Telegram (telegram_bot.py)
Ini adalah script Python yang akan berkomunikasi dengan Telegram API, menerima perintah dari Anda, dan mengontrol script streaming utama.

Struktur Folder yang Direkomendasikan
Tempatkan semua file ini di direktori yang sama untuk kemudahan:
your_streaming_project/
├── streamer.py            # Script streaming utama
├── config.json            # Konfigurasi untuk streamer.py
├── keystream.txt          # Kunci streaming YouTube Anda
├── telegram_bot.py        # Script bot Telegram
├── bot_config.json        # Konfigurasi untuk telegram_bot.py
├── ffmpeg_log.txt         # (Akan dibuat otomatis oleh FFmpeg)
└── stream_process.pid     # (Akan dibuat otomatis oleh bot saat streaming aktif)

Langkah-langkah Akhir
Instal Library: Pastikan Anda telah menginstal python-telegram-bot:
Siapkan FFmpeg: Pastikan FFmpeg dan FFprobe terinstal di sistem Anda dan dapat diakses melalui PATH.
Jalankan Bot: Buka terminal di direktori proyek Anda dan jalankan bot:

python telegram_bot.py


