import requests
import time
import os
import random
from datetime import datetime, timezone, timedelta

# --- PEGA AS CONFIGURAÇÕES DOS SEGREDOS DO GITHUB ---
BOT_TOKEN = os.environ["DISCORD_TOKEN"]
SOURCE_CHANNEL_ID = os.environ["CHANNEL_PRIVADO"]
TARGET_CHANNEL_ID = os.environ["CHANNEL_PUBLICO"]
# ---------------------

headers = {"Authorization": f"Bot {BOT_TOKEN}"}

def run_bot():
    print("--- INICIANDO BOT VIXEN (GITHUB) ---")
    
    found_platforms = set()
    messages_to_delete = []

    # 1. LER CANAL PRIVADO
    print("1. Lendo canal privado...")
    try:
        r_hist = requests.get(f"https://discord.com/api/v9/channels/{SOURCE_CHANNEL_ID}/messages?limit=15", headers=headers)
        messages = r_hist.json()
        if not isinstance(messages, list): messages = []
    except:
        messages = []

    # 2. DETECÇÃO ONLYFANS (/live)
    print("--- Checando OnlyFans ---")
    try:
        headers_of = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://onlyfans.com/",
            "Accept-Language": "en-US,en;q=0.9"
        }
        r_of = requests.get("https://onlyfans.com/vixenfree/live", headers=headers_of, timeout=10)
        
        if r_of.status_code == 200:
            page_text = r_of.text.lower()
            of_triggers = ['"islive":true', 'status-online', 'b-live-icon', 'live now', 'class="b-video-wrapper"']
            is_of_live = False
            for trigger in of_triggers:
                if trigger in page_text:
                    is_of_live = True
                    break
            
            if is_of_live:
                found_platforms.add("OnlyFans")
                print("OnlyFans Detectado via Site!")
    except Exception as e:
        print(f"Erro OF: {e}")

    # 3. FILTRAR MENSAGENS DISCORD
    for msg in messages:
        msg_id = msg.get("id")
        content = msg.get("content", "").lower()
        for embed in msg.get("embeds", []):
            content += " " + str(embed.get("title", "")) + " " + str(embed.get("description", ""))
            if "provider" in embed: content += " " + str(embed["provider"].get("name", ""))
        
        is_relevant = False
        if "twitch" in content: 
            found_platforms.add("Twitch")
            is_relevant = True
        if "kick" in content: 
            found_platforms.add("Kick")
            is_relevant = True
        if "fansly" in content: 
            found_platforms.add("Fansly")
            found_platforms.add("OnlyFans") # Regra de Ouro: Fansly puxa OF
            is_relevant = True
        
        if is_relevant or msg.get("author", {}).get("bot"):
            messages_to_delete.append(msg_id)

    if not found_platforms and not messages_to_delete:
        print("Nada encontrado.")
        return

    # 4. VERIFICAR DUPLICATA
    sorted_platforms = sorted(list(found_platforms))
    title_str = ", ".join(sorted_platforms).upper()
    should_send = True
    
    try:
        r_last = requests.get(f"https://discord.com/api/v9/channels/{TARGET_CHANNEL_ID}/messages?limit=1", headers=headers)
        last_msgs = r_last.json()
        
        if last_msgs and isinstance(last_msgs, list):
            last_msg = last_msgs[0]
            last_content = last_msg.get("content", "").lower()
            
            if last_msg.get("author", {}).get("username") == "Vix Bot" and "live on:" in last_content:
                 all_included = True
                 for plat in found_platforms:
                     if plat.lower() not in last_content:
                         all_included = False
                         break
                 
                 is_recent = False
                 if last_msg.get("timestamp"):
                    msg_time = datetime.fromisoformat(last_msg["timestamp"].replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - msg_time) < timedelta(minutes=10):
                        is_recent = True

                 if all_included and is_recent:
                     should_send = False
                     print("Já avisado recentemente.")
                 elif all_included and not is_recent:
                     print("Renovando aviso (Restart).")
                     should_send = True
                 else:
                     print("Novidade detectada.")
                     should_send = True
    except:
        pass

    # 5. ENVIAR
    if should_send:
        msg_body = []
        if "Twitch" in found_platforms: msg_body.append("💜 **Twitch:** <https://twitch.tv/vixenchannel>")
        if "Kick" in found_platforms: msg_body.append("💚 **Kick:** <https://kick.com/vixeninner>")
        if "Fansly" in found_platforms: msg_body.append("🧡 **Fansly:** <https://fansly.com/vixeninner>")
        if "OnlyFans" in found_platforms: msg_body.append("💙 **OnlyFans:** <https://onlyfans.com/vixenfree>")
        
        final_content = f"🚨 **VIXEN IS LIVE ON: {title_str}** 🚨\n\n" + "\n".join(msg_body) + "\n\n@everyone"
        
        requests.post(f"https://discord.com/api/v9/channels/{TARGET_CHANNEL_ID}/messages", json={"content": final_content}, headers=headers)
        print("Enviado!")

    # 6. FAXINA
    for msg_id in messages_to_delete:
        requests.delete(f"https://discord.com/api/v9/channels/{SOURCE_CHANNEL_ID}/messages/{msg_id}", headers=headers)
        time.sleep(0.5)

if __name__ == "__main__":
    run_bot()
