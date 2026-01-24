import discord
from discord.ext import tasks
from discord.ui import Button, View
import requests
import asyncio
import random
import os  # Ez kell a környezeti változókhoz

# --- KONFIGURÁCIÓ ---
# Railway-en a Variables fülre írd be ezeket, vagy hagyd itt, ha nem félted
TOKEN = "MTQ1NzI5NjcxNjE0NjQxMzU3OA.GBRyMr.y9EMSbdls4O0PWK6M7J_-xVhaGSwfWOuDkp7wc"
CHANNEL_ID = 1464610272718094514
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
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        headers = {"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Referer": "https://www.vinted.hu/"}
        url = f"https://www.vinted.hu/api/v2/catalog/items?search_text={SEARCH_TERM}&order=newest_first&countries[]=16&countries[]=24"
        try:
            self.session.cookies.clear()
            self.session.get("https://www.vinted.hu", headers=headers, timeout=10)
            return self.session.get(url, headers=headers, timeout=10)
        except: return None

    async def on_ready(self):
        print(f"--- {self.user} BEJELENTKEZVE ---")
        print(f"--- {SEARCH_TERM.upper()} MONITOR INDUL ---")

    @tasks.loop(seconds=60) # 60 másodpercre állítva a biztonság kedvéért
    async def monitor(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        if self.first_run:
            res = self.get_vinted_data()
            if res and res.status_code == 200:
                for item in res.json().get('items', []): seen_ids.add(item.get('id'))
            self.first_run = False

        response = self.get_vinted_data()
        if response and response.status_code == 200:
            items = response.json().get('items', [])
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
                        embed.description = f"{item.get('description', 'Nincs leírás')[:150]}..."
                        embed.add_field(name="📏 Méret", value=item.get('size_title', 'Nincs'), inline=True)
                        embed.add_field(name="💰 Ár", value=f"**{price} {currency}**", inline=True)

                        if item.get('photo'): embed.set_image(url=item['photo'].get('url'))

                        view = View()
                        view.add_item(Button(label="Megtekintés", url=url, style=discord.ButtonStyle.link, emoji="🔗"))

                        await channel.send(embed=embed, view=view)
                    seen_ids.add(item_id)

intents = discord.Intents.default()
intents.message_content = True 
client = VintedBot(intents=intents)

client.run(TOKEN)
