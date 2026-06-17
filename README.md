# Reseapp – rösta på platser nära er, live

En enkel Flask-app för familjeresan. Den hämtar GPS-positionen från
mobilen, frågar OpenStreetMap om vad som finns i närheten (utsiktsplatser,
historiska platser, stränder, restauranger) och låter alla i familjen
rösta 👍/👎 på varje plats. Byggs stegvis – varje version är en egen
git-tagg så du kan se hur appen växer.

## Komma igång

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Öppna sedan http://localhost:5000 i mobilens webbläsare (mobilen måste
vara på samma wifi som datorn i de tidiga versionerna).

## Versioner (git-taggar)

- v0.1 – Flask-skelett + databas, ingen riktig funktionalitet än.
- v1.0 – Live "vad finns nära mig"-lista + röstning (MVP).

## Projektstruktur

reseapp/
  app.py          Flask-app: routes (URL:er) och vad de gör
  db.py           Allt som rör databasen (SQLite)
  overpass.py     Hämtar platser nära en GPS-position från OpenStreetMap
  templates/      HTML-sidor (Jinja2-mallar)
  static/         CSS och Javascript
  reseapp.db      Skapas automatiskt första gången du kör appen (gitignored)

## Om git-historiken

reseapp_med_git_historik.tar.gz (i samma Drive-mapp) innehåller HELA
projektet plus en riktig .git-mapp med alla commits och taggar (v0.1, v1.0).
Packa upp den lokalt på din dator om du vill se/följa historiken i git —
filerna här i Drive är bara läsbara kopior för att du ska kunna bläddra
i koden direkt i webbläsaren.
