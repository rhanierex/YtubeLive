import logging
import os
import subprocess
import time
import json
import sys
import platform

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- KONFIGURASI BOT ---
CONFIG_FILE = "bot_config.json"
CONFIG = {} # Akan diisi dari bot_config.json

DEFAULT_BOT_CONFIG = {
    "TELEGRAM_BOT_TOKEN": "GANTI_DENGAN_TOKEN_BOT_ANDA",
    "ALLOWED_CHAT_ID": 0,
    "STREAM_SCRIPT_PATH": "streamer.py",
    "PID_FILE": "stream_process.pid",
    "LOG_FILE": "ffmpeg_log.txt"
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Fungsi untuk memuat konfigurasi ---
def load_bot_config():
    """Memuat konfigurasi bot dari bot_config.json atau membuat file default jika tidak ada."""
    global CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            CONFIG = json.load(f)
        for key, default_value in DEFAULT_BOT_CONFIG.items():
            if key not in CONFIG:
                CONFIG[key] = default_value
        logger.info(f"Konfigurasi bot dimuat dari '{CONFIG_FILE}'.")

        if CONFIG["TELEGRAM_BOT_TOKEN"] == DEFAULT_BOT_CONFIG["TELEGRAM_BOT_TOKEN"] or not CONFIG["TELEGRAM_BOT_TOKEN"]:
            logger.error("Token bot Telegram belum diatur di bot_config.json. Bot tidak akan berfungsi.")
            sys.exit(1)
        if CONFIG["ALLOWED_CHAT_ID"] == DEFAULT_BOT_CONFIG["ALLOWED_CHAT_ID"] or not CONFIG["ALLOWED_CHAT_ID"]:
            logger.error("Chat ID yang diizinkan belum diatur di bot_config.json. Bot tidak akan berfungsi.")
            sys.exit(1)

    except FileNotFoundError:
        logger.warning(f"File '{CONFIG_FILE}' tidak ditemukan. Membuat file konfigurasi bot default...")
        CONFIG = DEFAULT_BOT_CONFIG
        save_bot_config()
        logger.error(f"Harap edit '{CONFIG_FILE}' dengan token bot dan Chat ID Anda, lalu jalankan ulang bot.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Kesalahan format JSON di '{CONFIG_FILE}'. Menggunakan konfigurasi bot default.")
        CONFIG = DEFAULT_BOT_CONFIG
        logger.error(f"Harap perbaiki atau hapus '{CONFIG_FILE}' jika Anda ingin menggunakan konfigurasi baru.")
        sys.exit(1)

def save_bot_config():
    """Menyimpan konfigurasi bot saat ini ke bot_config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(CONFIG, f, indent=4)
        logger.info(f"Konfigurasi bot disimpan ke '{CONFIG_FILE}'.")
    except IOError as e:
        logger.error(f"Gagal menyimpan konfigurasi bot ke '{CONFIG_FILE}': {e}")

# --- Fungsi Helper ---
def is_stream_running():
    """Mengecek apakah proses streaming sedang berjalan."""
    pid_file_path = CONFIG['PID_FILE']
    if os.path.exists(pid_file_path):
        with open(pid_file_path, 'r') as f:
            pid_str = f.read().strip()
        try:
            pid = int(pid_str)
            if platform.system() == "Windows":
                # Di Windows, ini adalah pengecekan sederhana hanya berdasarkan keberadaan PID file.
                # Untuk lebih robust, gunakan psutil atau tasklist.
                # Contoh psutil: import psutil; return psutil.pid_exists(pid), pid
                # Untuk saat ini, asumsikan jika file PID ada, proses sedang berjalan.
                return True, pid
            else: # Linux/macOS
                os.kill(pid, 0)
                return True, pid
        except (ProcessLookupError, ValueError):
            logger.warning(f"PID {pid_str} tidak valid atau proses tidak ditemukan. Menghapus '{pid_file_path}'.")
            os.remove(pid_file_path)
            return False, None
        except Exception as e:
            logger.error(f"Error saat mengecek PID: {e}")
            return False, None
    return False, None

def start_stream_process():
    """Memulai proses streaming."""
    running, _ = is_stream_running()
    if running:
        return False

    try:
        process = subprocess.Popen([sys.executable, CONFIG['STREAM_SCRIPT_PATH']],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0)

        with open(CONFIG['PID_FILE'], 'w') as f:
            f.write(str(process.pid))
        logger.info(f"Proses streaming dimulai dengan PID: {process.pid}")
        return True
    except FileNotFoundError:
        logger.error(f"Script streaming '{CONFIG['STREAM_SCRIPT_PATH']}' tidak ditemukan.")
        return False
    except Exception as e:
        logger.error(f"Gagal memulai proses streaming: {e}")
        return False

def stop_stream_process(pid):
    """Menghentikan proses streaming."""
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True, capture_output=True)
        else:
            os.kill(pid, 15)

        time.sleep(2)
        if os.path.exists(CONFIG['PID_FILE']):
            os.remove(CONFIG['PID_FILE'])
        logger.info(f"Proses streaming (PID: {pid}) dihentikan.")
        return True
    except Exception as e:
        logger.error(f"Gagal menghentikan proses streaming (PID: {pid}): {e}")
        return False

# --- Handler Perintah Telegram ---

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi untuk memeriksa apakah chat ID diizinkan."""
    if update.effective_chat.id != CONFIG['ALLOWED_CHAT_ID']:
        await update.message.reply_text("Maaf, Anda tidak diizinkan menggunakan bot ini.")
        logger.warning(f"Akses tidak sah dari Chat ID: {update.effective_chat.id}")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan saat perintah /start diterima."""
    if not await check_auth(update, context): return
    await update.message.reply_text(
        "Halo! Saya adalah Bot Kontrol Streaming Anda.\n"
        "Gunakan perintah berikut:\n"
        "/start_stream - Memulai streaming\n"
        "/stop_stream - Menghentikan streaming\n"
        "/status - Cek status streaming\n"
        "/log - Dapatkan log FFmpeg terbaru"
    )

async def start_stream_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai streaming video."""
    if not await check_auth(update, context): return

    running, _ = is_stream_running()
    if running:
        await update.message.reply_text("Streaming sudah berjalan.")
    else:
        await update.message.reply_text("Memulai streaming, mohon tunggu...")
        if start_stream_process():
            await update.message.reply_text("Streaming berhasil dimulai! Cek log FFmpeg untuk detail.")
        else:
            await update.message.reply_text("Gagal memulai streaming. Periksa log bot.")

async def stop_stream_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menghentikan streaming video."""
    if not await check_auth(update, context): return

    running, pid = is_stream_running()
    if not running:
        await update.message.reply_text("Streaming tidak sedang berjalan.")
    else:
        await update.message.reply_text(f"Menghentikan streaming (PID: {pid}), mohon tunggu...")
        if stop_stream_process(pid):
            await update.message.reply_text("Streaming berhasil dihentikan.")
        else:
            await update.message.reply_text("Gagal menghentikan streaming. Periksa log bot.")

async def stream_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengecek status streaming."""
    if not await check_auth(update, context): return

    running, pid = is_stream_running()
    if running:
        await update.message.reply_text(f"Streaming sedang berjalan dengan PID: `{pid}`", parse_mode='MarkdownV2')
    else:
        await update.message.reply_text("Streaming tidak sedang berjalan.")

async def send_ffmpeg_log_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim file log FFmpeg terbaru."""
    if not await check_auth(update, context): return

    log_file_path = CONFIG['LOG_FILE']
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'rb') as f:
                await update.message.reply_document(f, caption="Log FFmpeg terbaru:")
        except Exception as e:
            await update.message.reply_text(f"Gagal membaca file log: {e}")
    else:
        await update.message.reply_text("File log FFmpeg tidak ditemukan.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan pesan bantuan."""
    if not await check_auth(update, context): return
    await start_command(update, context)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menanggapi perintah yang tidak dikenal."""
    if not await await check_auth(update, context): return # Perbaikan: double await di sini
    await update.message.reply_text("Maaf, perintah tersebut tidak dikenal.")


def main() -> None:
    """Menjalankan bot."""
    load_bot_config()

    application = Application.builder().token(CONFIG['TELEGRAM_BOT_TOKEN']).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("start_stream", start_stream_handler))
    application.add_handler(CommandHandler("stop_stream", stop_stream_handler))
    application.add_handler(CommandHandler("status", stream_status_handler))
    application.add_handler(CommandHandler("log", send_ffmpeg_log_handler))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot dimulai. Tekan Ctrl+C untuk menghentikan.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()