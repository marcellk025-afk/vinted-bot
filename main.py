import discord
from discord.ext import tasks
from discord.ui import Button, View
import requests
import os
from datetime import datetime

# --- KONFIGURÁCIÓ ---
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else 0
SEARCH_TERM = "nike" 
MAX_PRICE = 45000     

seen_ids = set()

class VintedBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        self.first_run = True

    async def setup_hook(self):
        self.monitor.start()

    def get_vinted_data(self):
        # Kiírjuk a logba, hogy éppen lekérdezünk
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Keresés futtatása a Vinteden...")
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        headers = {"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Referer": "https://www.vinted.hu/"}
        url = f"https://www.vinted.hu/api/v2/catalog/items?search_text={SEARCH_TERM}&order=newest_first&countries[]=16&countries[]=24"
        try:
            self.session.cookies.clear()
            self.session.get("https://www.vinted.hu", headers=headers, timeout=10)
            res = self.session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sikeres válasz érkezett.")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] HIBA: Vinted kód {res.status_code}")
            return res
        except Exception as e: 
            print(f"Hiba a lekérdezés alatt: {e}")
            return None

    async def on_ready(self):
        print(f"--- {self.user} BEJELENTKEZVE ---")

    @tasks.loop(seconds=60)
    async def monitor(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel or not TOKEN: return

        response = self.get_vinted_data()
        
        if response and response.status_code == 200:
            items = response.json().get('items', [])
            
            # Első futásnál csak elmentjük a meglévőket
            if self.first_run:
                for item in items: seen_ids.add(item.get('id'))
                self.first_run = False
                print("Alapállapot elmentve, várakozás az új hirdetésekre...")
                return

            new_found = 0
            for item in items[:5]:
                item_id = item.get('id')
                if item_id not in seen_ids:
                    raw_p = item.get('price')
                    price = float(raw_p.get('amount')) if isinstance(raw_p, dict) else float(raw_p)
                    
                    if price <= MAX_PRICE:
                        url = item.get('url')
                        currency = item.get('currency', 'HUF')
                        flag = "🇭🇺" if currency == "HUF" else "🇵🇱"
                        
                        embed = discord.Embed(title=f"{flag} {item.get('title')}", url=url, color=0x00a8ff)
                        embed.add_field(name="💰 Ár", value=f"**{price} {currency}**", inline=False)
                        if item.get('photo'): embed.set_image(url=item['photo'].get('url'))

                        view = View()
                        view.add_item(Button(label="Megtekintés", url=url, style=discord.ButtonStyle.link))
                        await channel.send(embed=embed, view=view)
                        new_found += 1
                    seen_ids.add(item_id)
            
            if new_found == 0:
                print("Nincs új hirdetés a megadott feltételekkel.")

intents = discord.Intents.default()
intents.message_content = True 
client = VintedBot(intents=intents)
client.run(TOKEN)
