"""
db.py – allt som har att göra med databasen.

Vi använder SQLite, som är en databas som bor i en enda fil (reseapp.db)
istället för att kräva en separat databas-server. Perfekt för ett litet
projekt som detta: noll installation, men fungerar precis som en "riktig"
SQL-databas (samma SQL-språk som Postgres/MySQL).

Pedagogisk poäng: vi blandar inte SQL-strängar rakt in i app.py. All
databaslogik bor här, så app.py bara anropar t.ex. record_vote(...) utan
att veta HUR det sparas. Det kallas "separation of concerns" – varje
fil har ett tydligt ansvar.
"""

import os
import sqlite3
from pathlib import Path

# Path(__file__).parent ger mappen där DENNA fil ligger, oavsett varifrån
# du startar python-kommandot. Då hamnar databasen alltid bredvid app.py.
#
# DB_PATH kan dock övertrumfas med miljövariabeln DB_PATH – det behövs på
# Railway: där bor appens KOD i en container som nollställs vid varje ny
# deploy, men en "Volume" (en separat, permanent hårddisk man kopplar in
# på t.ex. /data) överlever deployer och omstarter. Genom att sätta
# DB_PATH=/data/reseapp.db i Railway pekar vi databasen dit istället för
# in i containerns tillfälliga filsystem – annars skulle alla röster
# försvinna nästa gång appen deployas om.
DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent / "reseapp.db"))


def get_connection():
    """
    Öppnar en anslutning till databasfilen.

    row_factory = sqlite3.Row gör att vi kan läsa kolumner med namn
    (row["namn"]) istället för bara index (row[0]) – mycket lättare
    att läsa och underhålla.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Skapar tabellen om den inte redan finns. Körs varje gång appen
    startar – "CREATE TABLE IF NOT EXISTS" gör att det är säkert att
    köra om och om igen utan att radera data.

    Kolumner:
      osm_id    - platsens unika id från OpenStreetMap (t.ex. "node/12345")
      name      - platsens namn, t.ex. "Vernazza utkikspunkt"
      category  - en av: viewpoint, historic, beach, restaurant
      lat/lon   - koordinater, så vi kan visa platsen på en karta senare
      person    - vem som röstade (förnamn, ingen inloggning behövs)
      vote      - 1 för tummen upp, -1 för tummen ner

      UNIQUE(osm_id, person) betyder: samma person kan bara ha EN röst
      per plats. Om de röstar igen uppdaterar vi rösten istället för att
      skapa en ny rad (se record_vote nedan).
    """
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            person TEXT NOT NULL,
            vote INTEGER NOT NULL CHECK (vote IN (1, -1)),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(osm_id, person)
        )
        """
    )
    conn.commit()
    conn.close()


def record_vote(osm_id, name, category, lat, lon, person, vote):
    """
    Sparar (eller uppdaterar) en röst.

    "INSERT ... ON CONFLICT ... DO UPDATE" är SQLite-varianten av
    "lägg till, men om den redan finns (samma osm_id+person), ändra
    den befintliga raden istället". Det här är samma idé som ett
    "upsert" i andra databaser.
    """
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO votes (osm_id, name, category, lat, lon, person, vote)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(osm_id, person)
        DO UPDATE SET vote = excluded.vote
        """,
        (osm_id, name, category, lat, lon, person, vote),
    )
    conn.commit()
    conn.close()


def get_vote_summary(osm_ids):
    """
    Hämtar antal upp- och nedröster för en lista av osm_id:n, OCH vilka
    personer som röstat vad – så familjen kan se VEM som gillade en
    plats, inte bara hur många.

    Returnerar t.ex.:
      {"node/12345": {"up": 2, "down": 1,
                       "up_names": ["Mamma", "Pappa"],
                       "down_names": ["Lisa"]},
       "node/6789":  {"up": 0, "down": 0, "up_names": [], "down_names": []}}

    Vi bygger frågan med "?" som platshållare för varje id (aldrig
    klistra in variabler direkt i SQL-strängen – det öppnar för
    SQL-injection. Platshållare gör sqlite3 ansvarig för att escapa
    värdena säkert).
    """
    if not osm_ids:
        return {}

    conn = get_connection()
    placeholders = ",".join("?" for _ in osm_ids)
    rows = conn.execute(
        f"""
        SELECT osm_id, person, vote
        FROM votes
        WHERE osm_id IN ({placeholders})
        """,
        list(osm_ids),
    ).fetchall()
    conn.close()

    summary = {
        osm_id: {"up": 0, "down": 0, "up_names": [], "down_names": []}
        for osm_id in osm_ids
    }
    for row in rows:
        bucket = summary[row["osm_id"]]
        if row["vote"] == 1:
            bucket["up"] += 1
            bucket["up_names"].append(row["person"])
        else:
            bucket["down"] += 1
            bucket["down_names"].append(row["person"])
    return summary


def get_vote_for_person(osm_id, person):
    """
    Hämtar VILKEN röst (1, -1) en specifik person redan gett en
    specifik plats, eller None om personen inte röstat alls. Används
    för att avgöra om ett nytt klick ska RÄKNAS som en ny röst eller
    TA BORT den befintliga (toggle) – se record_or_toggle_vote i app.py.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT vote FROM votes WHERE osm_id = ? AND person = ?",
        (osm_id, person),
    ).fetchone()
    conn.close()
    return row["vote"] if row else None


def remove_vote(osm_id, person):
    """
    Tar bort en persons röst på en plats helt (ångra-funktionen). Om
    raden inte finns händer ingenting – det är okej, DELETE utan
    matchande rad är ett "no-op" i SQL.
    """
    conn = get_connection()
    conn.execute(
        "DELETE FROM votes WHERE osm_id = ? AND person = ?",
        (osm_id, person),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Packlista – en DELAD att-göra-lista för packning. Alla i familjen ser
# samma lista och samma avbockningar (till skillnad från t.ex. ett privat
# minne i mobilen) – så ingen behöver fråga "tog du med solkräm?" i gruppchatten.
# ---------------------------------------------------------------------------


def init_packing_table():
    """Skapar packlista-tabellen om den inte redan finns."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS packing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            added_by TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def add_packing_item(item, added_by):
    """Lägger till en ny rad i packlistan, obockad."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO packing_items (item, added_by, done) VALUES (?, ?, 0)",
        (item, added_by),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_packing_items():
    """Hämtar hela packlistan, äldst tillagd först."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, item, added_by, done FROM packing_items ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "item": row["item"],
            "added_by": row["added_by"],
            "done": bool(row["done"]),
        }
        for row in rows
    ]


def toggle_packing_item(item_id):
    """Växlar en rad mellan packad/inte packad och returnerar nya statusen."""
    conn = get_connection()
    row = conn.execute(
        "SELECT done FROM packing_items WHERE id = ?", (item_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return None
    new_done = 0 if row["done"] else 1
    conn.execute(
        "UPDATE packing_items SET done = ? WHERE id = ?", (new_done, item_id)
    )
    conn.commit()
    conn.close()
    return bool(new_done)


def delete_packing_item(item_id):
    """Tar bort en rad från packlistan helt."""
    conn = get_connection()
    conn.execute("DELETE FROM packing_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
