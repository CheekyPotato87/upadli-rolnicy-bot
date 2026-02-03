import os
import discord
from discord.ext import commands
import requests
import csv
from io import StringIO

SUMMARY_CHANNEL_ID = 1446194852046962921  # ID kanału testowego

#SUMMARY_CHANNEL_ID = 1464696629138292948
# ID kanału podsumowania PeGeRusy

GABLOTA_CHANNEL_ID = 1446194852046962921 # ID kanału testowego gabloty

#GABLOTA_CHANNEL_ID = 123456789012345678
# ID kanału gabloty PeGeRusy
BOSS_ID = 1434948198052532306             # ID szefa

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ===== BOT =====
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== READY EVENT =====
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")

# ===== TEST COMMAND =====
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")
# ===== LOAD SHEET DATA =====
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/13_GhKgOcFTPeVF4Ra9TMlpl6V_thNHMGtARqHtVQPkw/export?format=csv"
# ===== LOAD GABLOTA DATA =====
GABLOTA_CSV_URL = "https://docs.google.com/spreadsheets/d/13_GhKgOcFTPeVF4Ra9TMlpl6V_thNHMGtARqHtVQPkw/export?format=csv&gid=837047272"
# ===== GABLOTA WEBHOOK =====
GABLOTA_WEBHOOK = "https://script.google.com/macros/s/AKfycbzFA1SkeBpb7XFlRLlhInkco-oQYtUQsOYmTIy6pLTxFFSIy2AkqGXha-dCGfv6SZKRMw/exec"
# ===== ARCHIWUM WEBHOOK =====
ARCHIWUM_WEBHOOK = "https://script.google.com/macros/s/AKfycbzcN79roMynWf0bbRMQ9_BqbkUkD5wI865zU4mZjKwqfngftrr3uLVB-9Q9oAqO-02h/exec"
# ===== BUILD TABLE =====
def build_table(data):
    nick_width = max(len(row['nick']) for row in data)
    nick_width = max(nick_width, len("Nick"))

    header = f"{'Nick':<{nick_width}} | {'Punkty':>6}\n"
    header += "-" * (nick_width + 11) + "\n"

    rows = ""
    for row in data:
        rows += f"{row['nick']:<{nick_width}} | {row['points']:>6}\n"

    return f"```\n{header}{rows}```"
# ===== RUN SEASON =====
def run_season(ctx, save_gablota=True):
    data = load_sheet_data()

    if not data:
        return None, "❌ Brak danych w arkuszu."

    data = sort_by_points_desc(data)

    if save_gablota:
        top3 = data[:3]
        update_gablota(top3)

    embed = build_season_embed(data)

    return embed, None
# ===== LOAD GABLOTA =====
def load_gablota():
    response = requests.get(GABLOTA_CSV_URL)
    response.raise_for_status()

    csv_file = StringIO(response.text)
    reader = csv.DictReader(csv_file)
    return list(reader)

def save_gablota(gablota):
    # zapis przez Google Forms API nie działa w CSV,
    # więc użyjemy prostego webhooka przez Sheets (Apps Script)
    pass
# ===== UPDATE GABLOTA =====
# ===== UPDATE GABLOTA =====
def update_gablota(top3):
    gablota = load_gablota()
    print("GABLOTA PRZED:", gablota)  # debug

    def find(nick):
        for r in gablota:
            if r.get("nick") == nick:
                return r
        return None

    def add(nick, medal):
        row = find(nick)
        if not row:
            row = {"nick": nick, "gold": "0", "silver": "0", "bronze": "0"}
            gablota.append(row)

        row[medal] = str(int(row[medal]) + 1)

    add(top3[0]["nick"], "gold")
    add(top3[1]["nick"], "silver")
    add(top3[2]["nick"], "bronze")

    print("GABLOTA PO:", gablota)  # debug

    resp = requests.post(GABLOTA_WEBHOOK, json=gablota)

    print("WEBHOOK STATUS:", resp.status_code)
    print("WEBHOOK TEXT:", resp.text)
    
# ===== LOAD SHEET DATA =====  
def load_sheet_data():
    response = requests.get(SHEET_CSV_URL)
    response.raise_for_status()

    csv_file = StringIO(response.text)
    reader = csv.DictReader(csv_file)
    return list(reader)
# ===== CHECK COMMAND =====
@bot.command()
async def check(ctx):
    user_id = str(ctx.author.id)

    data = load_sheet_data()

    for row in data:
        if row["discord_id"] == user_id:
            await ctx.send(
                f"📊 **Twoje dane**\n"
                f"Punkty: {row['points']}\n"
                f"Status: {row['status']}"
            )
            return

    await ctx.send("❌ Nie znaleziono Cię w bazie.")
# ===== SORT BY POINTS DESC =====
def sort_by_points_desc(data):
    def safe_int(value):
        try:
            return int(value)
        except:
            return 0

    return sorted(
        data,
        key=lambda row: safe_int(row.get("points")),
        reverse=True
    )
# ===== GET TOP 3 =====
def get_top3(data):
    top = data[:3]

    medals = ["🥇", "🥈", "🥉"]
    result = "🏆 PODIUM UPADŁYCH ROLNIKÓW - ELITA SEZONU\n\n"

    for i, row in enumerate(top):
        nick = row.get("nick", "Brak")
        points = row.get("points", 0)
        result += f"{medals[i]} {nick} — {points} pkt\n"

    return result + "\n"
# ===== PROGRESS BAR =====
def progress_bar(percent, size=12):
    filled = int(round((percent / 100) * size))
    empty = size - filled
    return "🌾" * filled + "⬜" * empty
# ===== BUILD SEASON STATS =====
def build_season_stats(data):
    total = len(data)
    active = 0
    ok = 0
    low = 0

    for row in data:
        try:
            points = int(row.get("points", 0))
        except:
            points = 0

        status = row.get("status", "").lower()

        if points > 0:
            active += 1

        if "low" in status:
            if points >= 1500:
                ok += 1
            else:
                low += 1
        else:
            if points >= 2000:
                ok += 1
            else:
                low += 1

    # zabezpieczenie przed dzieleniem przez zero
    def percent(part, whole):
        return round((part / whole) * 100, 1) if whole else 0

    return {
        "total": total,
        "active": active,
        "ok": ok,
        "low": low,
        "ok_pct": percent(ok, total),
        "low_pct": percent(low, total),
        "active_pct": percent(active, total)
    }
# ===== BUILD SEASON EMBED =====
def build_season_embed(data):
    embed = discord.Embed(
        title="🌾 Podsumowanie Sezonu — Upadli Rolnicy",
        description="Elita sezonu oraz pełne zestawienie punktów",
        color=0x2ecc71  # zielony premium
    )

    # ===== TOP 3 =====
    medals = ["🥇", "🥈", "🥉"]
    top_lines = []

    for i, row in enumerate(data[:3]):
        nick = row.get("nick", "Brak")
        points = row.get("points", 0)
        top_lines.append(f"{medals[i]} **{nick}** — `{points} pkt`")

    embed.add_field(
        name="🏆 Podium sezonu",
        value="\n".join(top_lines),
        inline=False
    )

    # ===== TABELA =====
    # ===== TABELA W JEDNEJ KOLUMNIE =====
    nick_width = max(len(row["nick"]) for row in data)
    nick_width = max(nick_width, len("Nick"))

    header = f"{'Nick':<{nick_width}} | {'Punkty':>6}\n"
    header += "-" * (nick_width + 11) + "\n"

    rows = ""
    for row in data:
        rows += f"{row['nick']:<{nick_width}} | {row['points']:>6}\n"

    table_text = f"```\n{header}{rows}```"

    if len(table_text) > 1000:
        table_text = table_text[:1000] + "\n...```"

    embed.add_field(
        name="📊 Ranking sezonu",
        value=table_text,
        inline=False
    )
# ===== STATYSTYKI SYNDYKATU =====
    stats = build_season_stats(data)

    active_bar = progress_bar(stats["active_pct"])
    ok_bar = progress_bar(stats["ok_pct"])
    low_bar = progress_bar(stats["low_pct"])

    total = stats["total"]

    stats_text = (
        f"🌾 Rolników w sezonie: **{total}**\n\n"

        f"🚜 Aktywni\n"
        f"{active_bar} {stats['active_pct']}% ({stats['active']}/{total})\n\n"

        f"✅ W normie\n"
        f"{ok_bar} {stats['ok_pct']}% ({stats['ok']}/{total})\n\n"

        f"⚠️ Pod kreską\n"
        f"{low_bar} {stats['low_pct']}% ({stats['low']}/{total})"
    )

    embed.add_field(
        name="📈 Kronika Sezonu Upadłych Rolników",
        value=stats_text,
        inline=False
    )
    embed.set_footer(text="Upadli Rolnicy Bot • Sezonowe statystyki")
    embed.set_author(name="Created by FarmAgra Poland")

    return embed
# ===== SEZON COMMAND =====
SEASON_NUMBER = 14   # zmieniasz ręcznie co sezon
@bot.command()
async def sezon(ctx):
    # autoryzacja
    print("SEZON ODPALONY") #test 
    if ctx.author.id != BOSS_ID:
        await ctx.send("❌ Nie masz uprawnień.")
        return

    channel = bot.get_channel(SUMMARY_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Kanał podsumowania nie istnieje.")
        return

    data = load_sheet_data()
    
    if not data:
        await ctx.send("❌ Brak danych w arkuszu.")
        return
    embed, error = run_season(ctx, save_gablota=True)

    if error:
        await ctx.send(error)
        return
        
    data = sort_by_points_desc(data)
    save_season_archive(data, SEASON_NUMBER) # dodajemy zapis do archiwum
    # ===== GABLOTA =====
    #top3 = data[:3]
    #update_gablota(top3)
         #await update_gablota_status_same_channel(channel)
    # ===== EMBED =====
    embed = build_season_embed(data)
    #await update_gablota_status_same_channel(channel)
    await channel.send(embed=embed)
# ===== SEZON TEST COMMAND =====
@bot.command()
async def sezon_test(ctx):
    if ctx.author.id != BOSS_ID:
        await ctx.send("❌ Nie masz uprawnień.")
        return

    embed, error = run_season(ctx, save_gablota=False)

    if error:
        await ctx.send(error)
        return

    await ctx.send("🧪 TRYB TESTOWY — brak zapisu do gabloty")
    await ctx.send(embed=embed)

# ===== SAVE SEASON ARCHIVE =====
from datetime import datetime

def save_season_archive(data, season_number):
    today = datetime.now().strftime("%Y-%m-%d")

    payload = []

    for idx, row in enumerate(data, start=1):
        payload.append({
            "sezon": season_number,
            "miejsce": idx,
            "nick": row["nick"],
            "punkty": row["points"],
            "data": today
        })

    requests.post(ARCHIWUM_WEBHOOK, json=payload)

# ===== GABLOTA COMMAND (ONE MESSAGE) =====
@bot.command()
async def gablota(ctx):

    channel = bot.get_channel(GABLOTA_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Kanał gabloty nie istnieje.")
        return

    gablota = load_gablota()

    if not gablota:
        await ctx.send("❌ Gablota jest pusta.")
        return

    # sortowanie: złoto -> srebro -> brąz
    def medal_sort(row):
        return (
            int(row.get("gold", 0)),
            int(row.get("silver", 0)),
            int(row.get("bronze", 0))
        )

    gablota_sorted = sorted(gablota, key=medal_sort, reverse=True)

    embed = discord.Embed(
        title="🏆 Gablota Sław — Upadli Rolnicy",
        description="Łączne osiągnięcia z wszystkich sezonów",
        color=0xf1c40f
    )

    lines = []

    for idx, row in enumerate(gablota_sorted, start=1):
        nick = row["nick"]
        gold = row.get("gold", "0")
        silver = row.get("silver", "0")
        bronze = row.get("bronze", "0")

        lines.append(
            f"**{idx}. {nick}** — 🥇 {gold} | 🥈 {silver} | 🥉 {bronze}"
        )

    text = "\n".join(lines)

    if len(text) > 4000:
        text = text[:4000] + "\n..."

    embed.add_field(
        name="🥇 Ranking medalowy",
        value=text,
        inline=False
    )

    embed.set_footer(text="Automatycznie aktualizowane po każdym sezonie")

    # ===== SZUKAMY STAREGO EMBEDA BOTA =====
    async for msg in channel.history(limit=20):
        if msg.author == bot.user and msg.embeds:
            await msg.edit(embed=embed)
            from datetime import datetime

            now = datetime.now().strftime("%Y-%m-%d %H:%M")

            await ctx.send(f"✅ Gablota została zaktualizowana — {now}")
            return

    # ===== JAK NIE MA — TWORZYMY PIERWSZY =====
    await channel.send(embed=embed)
    await ctx.send("📌 Utworzono pierwszą gablotę.")
# ===== TOKEN =====
TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)
