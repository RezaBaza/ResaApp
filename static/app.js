/*
 * app.js – all logik som körs i mobilens webbläsare.
 *
 * Tre steg när man trycker på knappen:
 *   1. Be webbläsaren om GPS-positionen (navigator.geolocation).
 *   2. Skicka den till vår Flask-server (/api/nearby) och vänta på svar.
 *   3. Rita upp resultatet som kort på sidan, med röstknappar.
 *
 * Vi använder "async/await" istället för gamla callback-funktioner –
 * det gör asynkron kod (kod som väntar på saker, t.ex. nätverkssvar)
 * mycket lättare att läsa: det ser nästan ut som vanlig, sekventiell kod.
 */

const CATEGORY_LABELS = {
  viewpoint: "🌄 Utsiktsplatser",
  historic: "🏰 Historiska platser",
  beach: "🏖️ Strand & bad",
  restaurant: "🍝 Restauranger",
  marina: "⛵ Hamn & marina",
  sweets: "🍦 Glass & bageri",
  park: "🌳 Parker & trädgårdar",
  lighthouse: "🗼 Fyrar",
  parking: "🅿️ Parkering",
};

// Hur många platser vi visar PER kategori. Overpass kan ge hundratals
// träffar i en kategori (t.ex. "historic" i en gammal stadskärna) – det
// blir ohanterligt att skrolla igenom. Backend (app.py) sorterar redan
// platserna efter avstånd, så vi visar bara de NÄRMASTE 20.
const MAX_PER_CATEGORY = 20;

// Översätter OSM:s "cuisine"-taggvärden (t.ex. "italian", "seafood") till
// svenska rubriker för att gruppera restauranger. Listan är inte komplett –
// allt som inte finns här visas med första bokstaven versal istället
// (se cuisineLabel nedan).
const CUISINE_LABELS = {
  italian: "Italienskt",
  french: "Franskt",
  pizza: "Pizza",
  seafood: "Skaldjur",
  fish: "Fisk",
  regional: "Lokala specialiteter",
  local: "Lokala specialiteter",
  mediterranean: "Medelhavskök",
  international: "Internationellt",
  vegetarian: "Vegetariskt",
  vegan: "Veganskt",
  ice_cream: "Glass",
  burger: "Burgare",
  kebab: "Kebab",
  asian: "Asiatiskt",
  greek: "Grekiskt",
  spanish: "Spanskt",
  steak_house: "Kött & grill",
};

// Gör en text till ett HTML-vänligt id, t.ex. "Lokala specialiteter"
// -> "lokala-specialiteter". Används för att länka mattyps-pillarna i
// cuisine-nav till rätt <h3>-rubrik.
function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9åäö]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function cuisineLabel(rawCuisine) {
  if (!rawCuisine) return "Okänd typ";
  // OSM tillåter flera värden separerade med ";" eller "," (t.ex.
  // "italian;pizza") – vi grupperar på det FÖRSTA värdet för enkelhetens
  // skull.
  const first = rawCuisine.split(/[;,]/)[0].trim();
  if (CUISINE_LABELS[first]) return CUISINE_LABELS[first];
  return first.charAt(0).toUpperCase() + first.slice(1).replace(/_/g, " ");
}

const personInput = document.getElementById("person");
const findBtn = document.getElementById("find-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const plansEl = document.getElementById("plans");
const radiusSelect = document.getElementById("radius");
const sortPlacesSelect = document.getElementById("sort-places");

// Resans datum (se projektinstruktionerna: Sto-Bgy 16 juli, hemresa 5
// aug). Används av både nedräkningen (renderCountdown) och vädersidan
// (loadWeather) – en enda källa istället för att hårdkoda datumen på
// flera ställen.
const TRIP_START = new Date("2026-07-16T00:00:00");
const TRIP_END = new Date("2026-08-05T00:00:00");

// Återanvänd sparat namn om man besökt sidan tidigare.
personInput.value = localStorage.getItem("person") || "";
personInput.addEventListener("input", () => {
  localStorage.setItem("person", personInput.value);
});

// Återanvänd senast valda sökradie också, så den inte nollställs till
// default (2 km) varje gång sidan öppnas igen.
radiusSelect.value = localStorage.getItem("radius") || "2";
radiusSelect.addEventListener("change", () => {
  localStorage.setItem("radius", radiusSelect.value);
});

// Två flikar ("Reseplaner" / "Hitta platser") istället för en lång sida
// man måste skrolla igenom – se .tab-nav/.tab-section i index.html.
// Bara EN sektion visas åt gången; knapparnas data-tab pekar på vilken
// sektions-id som ska visas.
function initTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  const sections = document.querySelectorAll(".tab-section");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.toggle("active", b === button));
      sections.forEach((section) =>
        section.classList.toggle("hidden", section.id !== button.dataset.tab)
      );

      // Kartan ligger i en flik som är dold (display:none) tills man
      // klickar dit – Leaflet kan inte räkna ut storleken på en osynlig
      // ruta, så vi måste invalidateSize() FÖRST när rutan blivit synlig,
      // annars blir kartan bara grå tills man råkar resiza fönstret.
      if (button.dataset.tab === "tab-map") {
        initMapIfNeeded();
        renderMapCategoryFilter();
        requestAnimationFrame(() => {
          leafletMap.invalidateSize();
          renderMap();
        });
      }

      if (button.dataset.tab === "tab-weather") {
        loadWeatherOnce();
      }
    });
  });
}
initTabs();

// ---------------------------------------------------------------------------
// Mörkt läge – sparas i localStorage så valet finns kvar nästa besök.
// Vi skriver INTE om hela style.css till CSS-variabler (stor omskrivning
// för en liten funktion) – istället ligger ett färdigt mörkt tema i en
// "body.dark-mode ..."-sektion längst ner i style.css, och vi växlar bara
// den klassen här.
// ---------------------------------------------------------------------------
const themeToggleBtn = document.getElementById("theme-toggle");

function applyTheme(theme) {
  document.body.classList.toggle("dark-mode", theme === "dark");
  themeToggleBtn.textContent = theme === "dark" ? "☀️" : "🌙";
}

applyTheme(localStorage.getItem("theme") || "light");

themeToggleBtn.addEventListener("click", () => {
  const newTheme = document.body.classList.contains("dark-mode") ? "light" : "dark";
  localStorage.setItem("theme", newTheme);
  applyTheme(newTheme);
});

// ---------------------------------------------------------------------------
// KPI-kort: dagar kvar, kostnad, körsträcka och antal röster. Visas som en
// rad små "nyckeltal"-kort istället för en lång textbanner – lättare att
// skumma. Kostnad/körsträcka hämtas från den reseplan som LIGGER I TOPP just
// nu (samma rankningslogik som renderPopularityBanner/renderPlanLeaderboard);
// finns inga röster än används första planen som ett preliminärt förslag.
// ---------------------------------------------------------------------------
function formatKr(amount) {
  return `${Math.round(amount).toLocaleString("sv-SE")} kr`;
}

function renderKpis() {
  const el = document.getElementById("kpi-row");
  if (!el) return;

  const cards = [];

  const today = new Date();
  const daysToDeparture = Math.ceil((TRIP_START - today) / 86400000);
  const daysToReturn = Math.ceil((TRIP_END - today) / 86400000);

  let daysValue;
  let daysLabel;
  if (daysToDeparture > 0) {
    daysValue = daysToDeparture;
    daysLabel = "dagar kvar till avresan";
  } else if (daysToReturn > 0) {
    daysValue = daysToReturn;
    daysLabel = "dagar kvar till hemresan";
  } else {
    daysValue = "🏠";
    daysLabel = "resan är klar!";
  }
  cards.push(`
    <div class="kpi-card">
      <div class="kpi-icon">🧳</div>
      <div class="kpi-value">${daysValue}</div>
      <div class="kpi-label">${daysLabel}</div>
    </div>
  `);

  if (currentPlans.length) {
    const ranked = [...currentPlans].sort((a, b) => {
      const scoreA = a.votes.up - a.votes.down;
      const scoreB = b.votes.up - b.votes.down;
      return scoreB - scoreA || b.votes.up - a.votes.up;
    });
    const top = ranked[0];
    const hasVotes = top.votes.up > 0 || top.votes.down > 0;
    const suffix = hasVotes ? "" : " (förslag)";

    if (top.cost_estimate) {
      cards.push(`
        <div class="kpi-card">
          <div class="kpi-icon">💰</div>
          <div class="kpi-value">${formatKr(top.cost_estimate.total_low)}–${formatKr(top.cost_estimate.total_high)}</div>
          <div class="kpi-label">uppskattad kostnad${suffix}</div>
        </div>
      `);
    }

    if (top.total_drive) {
      cards.push(`
        <div class="kpi-card">
          <div class="kpi-icon">🚗</div>
          <div class="kpi-value">${top.total_drive.km} km</div>
          <div class="kpi-label">körsträcka${suffix}</div>
        </div>
      `);
    }

    const totalVotes =
      currentPlans.reduce((sum, plan) => sum + plan.votes.up + plan.votes.down, 0) +
      lastPlaces.reduce((sum, place) => sum + place.votes.up + place.votes.down, 0);
    cards.push(`
      <div class="kpi-card">
        <div class="kpi-icon">🗳️</div>
        <div class="kpi-value">${totalVotes}</div>
        <div class="kpi-label">röster avgivna</div>
      </div>
    `);
  }

  el.innerHTML = cards.join("");
}
renderKpis();

// ---------------------------------------------------------------------------
// "Mest poppis just nu" – kombinerar topplistan för reseplaner
// (currentPlans, redan beräknad av renderPlanLeaderboard) och topplistan
// för platser (lastPlaces, ifyllt av loadPlaces nedan).
// ---------------------------------------------------------------------------
function renderPopularityBanner() {
  const el = document.getElementById("popularity-banner");
  if (!el) return;

  const parts = [];

  if (currentPlans.length) {
    const ranked = [...currentPlans].sort((a, b) => {
      const scoreA = a.votes.up - a.votes.down;
      const scoreB = b.votes.up - b.votes.down;
      return scoreB - scoreA || b.votes.up - a.votes.up;
    });
    const top = ranked[0];
    if (top.votes.up > 0 || top.votes.down > 0) {
      parts.push(`🏆 Reseplan: <strong>${top.title}</strong>`);
    }
  }

  if (lastPlaces.length) {
    const ranked = lastPlaces
      .map((place) => ({ place, score: place.votes.up - place.votes.down }))
      .filter((entry) => entry.place.votes.up > 0 || entry.place.votes.down > 0)
      .sort((a, b) => b.score - a.score || b.place.votes.up - a.place.votes.up);
    if (ranked.length) {
      parts.push(`📍 Plats: <strong>${ranked[0].place.name}</strong>`);
    }
  }

  if (parts.length === 0) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  el.innerHTML = `Mest poppis just nu — ${parts.join(" &nbsp;|&nbsp; ")}`;
}

// ---------------------------------------------------------------------------
// Kart-vy (Leaflet) – visar de senast hämtade platserna från
// "Hitta platser" som markörer. Reseplanernas etapper har bara
// textadresser (inga koordinater) i plans.py, så de visas inte som
// markörer – men hela bilrutten finns redan som en klickbar Google
// Maps-länk i varje plan-kort.
// ---------------------------------------------------------------------------
let leafletMap = null;
let markersLayer = null;

function initMapIfNeeded() {
  if (leafletMap) return;
  leafletMap = L.map("map");
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap-bidragsgivare",
  }).addTo(leafletMap);
  markersLayer = L.layerGroup().addTo(leafletMap);
  leafletMap.setView([45.0, 9.0], 6);
}

// Vilken kategori kartan filtrerar på just nu. "alla" stänger av
// filtreringen. Defaultar till "beach" enligt önskemål – annars dyker ALLA
// kategorier upp samtidigt och kartan blir en enda klump av markörer (det
// var precis det som hände innan detta filter fanns). Sparas i
// localStorage så valet finns kvar nästa besök.
let mapCategoryFilter = localStorage.getItem("mapCategory") || "beach";

// Bygger filterknapparna ovanför kartan – samma kategorier (CATEGORY_LABELS)
// och samma "pill med antal"-stil som .category-nav under "Hitta platser",
// plus en extra "Alla"-knapp. Antalen räknas om varje gång (lastPlaces kan
// ha ändrats av en ny sökning).
function renderMapCategoryFilter() {
  const nav = document.getElementById("map-category-filter");
  if (!nav) return;

  const counts = {};
  for (const place of lastPlaces) {
    counts[place.category] = (counts[place.category] || 0) + 1;
  }

  const allOption = { key: "alla", label: "🗺️ Alla", count: lastPlaces.length };
  const categoryOptions = Object.keys(CATEGORY_LABELS).map((key) => ({
    key,
    label: CATEGORY_LABELS[key],
    count: counts[key] || 0,
  }));

  nav.innerHTML = [allOption, ...categoryOptions]
    .map(({ key, label, count }) => {
      const active = key === mapCategoryFilter ? " active" : "";
      return `<button type="button" class="map-filter-btn${active}" data-category="${key}">${label} (${count})</button>`;
    })
    .join("");

  nav.querySelectorAll(".map-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      mapCategoryFilter = btn.dataset.category;
      localStorage.setItem("mapCategory", mapCategoryFilter);
      renderMapCategoryFilter();
      renderMap();
    });
  });
}

function renderMap() {
  if (!leafletMap || !markersLayer) return;
  markersLayer.clearLayers();

  const places =
    mapCategoryFilter === "alla"
      ? lastPlaces
      : lastPlaces.filter((place) => place.category === mapCategoryFilter);

  if (!places.length) {
    return;
  }

  const bounds = [];
  for (const place of places) {
    const marker = L.marker([place.lat, place.lon]).addTo(markersLayer);
    const commentsLine = place.comment_count
      ? `<br>💬 ${place.comment_count} kommentarer`
      : "";
    marker.bindPopup(
      `<strong>${place.name}</strong><br>👍 ${place.votes.up} 👎 ${place.votes.down}${commentsLine}`
    );
    bounds.push([place.lat, place.lon]);
  }
  leafletMap.fitBounds(bounds, { padding: [30, 30] });
}

// ---------------------------------------------------------------------------
// Väderprognos. Open-Meteo ger bara prognoser upp till ~16 dagar framåt –
// så länge avresan ligger längre bort än det visar vi typiska
// juli/augusti-värden istället, och växlar automatiskt till en riktig
// live-prognos när det är nära nog.
// ---------------------------------------------------------------------------
const WEATHER_LOCATIONS = [
  { name: "Comosjön", lat: 45.81, lon: 9.09 },
  { name: "Cinque Terre / La Spezia", lat: 44.10, lon: 9.82 },
  { name: "Nice", lat: 43.70, lon: 7.27 },
  { name: "Saint-Tropez", lat: 43.27, lon: 6.64 },
  { name: "Courmayeur (bergsklimat)", lat: 45.79, lon: 6.97 },
  { name: "Milano", lat: 45.46, lon: 9.19 },
];

const TYPICAL_CLIMATE = [
  { name: "Comosjön", high: 28, low: 18, rain: "Låg regnrisk" },
  { name: "Cinque Terre / La Spezia", high: 27, low: 20, rain: "Låg regnrisk" },
  { name: "Nice", high: 27, low: 20, rain: "Mycket låg regnrisk" },
  { name: "Saint-Tropez", high: 28, low: 20, rain: "Mycket låg regnrisk" },
  { name: "Courmayeur (bergsklimat)", high: 22, low: 12, rain: "Större chans för eftermiddagsskurar" },
  { name: "Milano", high: 29, low: 20, rain: "Måttlig, kan vara fuktigt" },
];

let weatherLoaded = false;

function loadWeatherOnce() {
  if (weatherLoaded) return;
  weatherLoaded = true;
  loadWeather();
}

function formatDateISO(date) {
  return date.toISOString().slice(0, 10);
}

async function loadWeather() {
  const el = document.getElementById("weather-content");
  el.innerHTML = `<p class="weather-loading">Hämtar väderdata...</p>`;

  const today = new Date();
  const daysUntilTrip = Math.ceil((TRIP_START - today) / 86400000);

  if (daysUntilTrip > 15) {
    el.innerHTML = renderStaticClimateTable(daysUntilTrip);
    return;
  }

  try {
    const results = await Promise.all(WEATHER_LOCATIONS.map(fetchForecast));
    el.innerHTML = renderForecastTable(results);
  } catch (err) {
    el.innerHTML =
      renderStaticClimateTable(daysUntilTrip) +
      `<p class="weather-error">Kunde inte hämta en live-prognos just nu, visar ungefärliga julivärden istället.</p>`;
  }
}

async function fetchForecast(loc) {
  const start = formatDateISO(new Date());
  const end = formatDateISO(new Date(Date.now() + 15 * 86400000));
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${loc.lat}&longitude=${loc.lon}` +
    `&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_mean` +
    `&timezone=auto&start_date=${start}&end_date=${end}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("väder-API svarade inte ok");
  const data = await response.json();
  return { loc, data };
}

function renderForecastTable(results) {
  return results
    .map(({ loc, data }) => {
      const days = data.daily.time
        .map((date, i) => {
          const max = Math.round(data.daily.temperature_2m_max[i]);
          const min = Math.round(data.daily.temperature_2m_min[i]);
          const rain = Math.round(data.daily.precipitation_probability_mean?.[i] ?? 0);
          return `<tr><td>${date}</td><td>${max}° / ${min}°</td><td>${rain}%</td></tr>`;
        })
        .join("");
      return `
        <div class="weather-card">
          <h3>${loc.name}</h3>
          <table class="weather-table">
            <thead><tr><th>Datum</th><th>Max/Min</th><th>Regnrisk</th></tr></thead>
            <tbody>${days}</tbody>
          </table>
        </div>
      `;
    })
    .join("");
}

function renderStaticClimateTable(daysUntilTrip) {
  const rows = TYPICAL_CLIMATE.map(
    (loc) => `<tr><td>${loc.name}</td><td>${loc.high}° / ${loc.low}°</td><td>${loc.rain}</td></tr>`
  ).join("");
  return `
    <p class="weather-note">
      ${daysUntilTrip} dagar kvar till avresan – en riktig väderprognos visas
      automatiskt här när det är 16 dagar eller mindre kvar. Tills då,
      ungefärliga juli/augusti-värden (dagstemperatur / natt-temperatur):
    </p>
    <table class="weather-table">
      <thead><tr><th>Plats</th><th>Typisk temp</th><th>Nederbörd</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// Reseplans-alternativen (se plans.py) är statiska och behöver ingen
// GPS-position – ladda dem direkt när sidan öppnas, så familjen kan
// rösta på HELA resrutter utan att först trycka på "Hitta platser".
loadPlans();

async function loadPlans() {
  const response = await fetch("/api/plans");
  if (!response.ok) return;
  const plans = await response.json();
  renderPlans(plans);
}

function planCardId(plan) {
  return `plan-${plan.id}`;
}

// Sparar senaste /api/plans-svaret så vi kan bygga om resultattavlan
// (renderPlanLeaderboard) efter varje röst, utan att hämta om hela listan
// från servern – sendPlanVote uppdaterar redan plan.votes i denna array.
let currentPlans = [];

function renderPlans(plans) {
  currentPlans = plans;
  plansEl.innerHTML = "";

  const heading = document.createElement("h2");
  heading.textContent = "🗺️ Vilken reseplan gillar du bäst?";
  plansEl.appendChild(heading);

  const intro = document.createElement("p");
  intro.className = "plans-intro";
  intro.textContent =
    "Samma flyg (Stockholm ↔ Bergamo, 16 juli–5 augusti) men olika sätt att dela upp de 20 nätterna. Rösta på den ni gillar mest!";
  plansEl.appendChild(intro);

  // Resultattavla: visar ALLA fyra alternativ direkt, rankade efter poäng
  // (👍 minus 👎) – det är HÄR man tydligt ser "vilket alternativ vinner"
  // istället för att behöva räkna ihop antalet röster i varje kort själv.
  const leaderboard = document.createElement("div");
  leaderboard.className = "plan-leaderboard";
  leaderboard.id = "plan-leaderboard";
  plansEl.appendChild(leaderboard);
  renderPlanLeaderboard();

  for (const plan of plans) {
    plansEl.appendChild(renderPlanCard(plan));
  }

  renderPopularityBanner();
  renderKpis();
}

function renderPlanLeaderboard() {
  const leaderboardEl = document.getElementById("plan-leaderboard");
  if (!leaderboardEl) return;

  const ranked = [...currentPlans].sort((a, b) => {
    const scoreA = a.votes.up - a.votes.down;
    const scoreB = b.votes.up - b.votes.down;
    return scoreB - scoreA || b.votes.up - a.votes.up;
  });

  const rowsHtml = ranked
    .map((plan, index) => {
      const score = plan.votes.up - plan.votes.down;
      const leaderClass = index === 0 && score > 0 ? " plan-leaderboard-leader" : "";
      return `
        <a href="#${planCardId(plan)}" class="plan-leaderboard-row${leaderClass}">
          <span class="plan-leaderboard-rank">${index + 1}.</span>
          <span class="plan-leaderboard-title">${plan.title}</span>
          <span class="plan-leaderboard-score">👍 ${plan.votes.up} 👎 ${plan.votes.down} (${score >= 0 ? "+" : ""}${score})</span>
        </a>
      `;
    })
    .join("");

  const totalVotes = ranked.reduce((sum, plan) => sum + plan.votes.up + plan.votes.down, 0);
  const headlineHtml = totalVotes
    ? `🏆 Just nu ligger <strong>${ranked[0].title}</strong> i topp`
    : `Ingen har röstat än – bli först!`;

  leaderboardEl.innerHTML = `
    <p class="plan-leaderboard-headline">${headlineHtml}</p>
    <div class="plan-leaderboard-rows">${rowsHtml}</div>
  `;
}

function renderPlanCard(plan) {
  const card = document.createElement("div");
  card.className = "plan-card";
  card.id = planCardId(plan);

  const rows = plan.legs
    .map((leg) => {
      // "drive" = körsträcka/körtid FRÅN föregående stopp (se plans.py).
      // Saknas den (borde aldrig hända, men skydda ändå) visas raden
      // helt enkelt inte.
      const driveLine = leg.drive
        ? `🚗 ${leg.drive.km} km (${leg.drive.time}) från ${leg.drive.from}`
        : "";
      const highlightsLine = (leg.highlights || []).length
        ? `💡 ${leg.highlights.join(" · ")}`
        : "";
      const parkingLine = leg.parking || "";

      return `
        <tr>
          <td>
            <strong>${leg.name}</strong><br>
            <span class="plan-nights">${leg.nights}</span>
          </td>
          <td>${leg.hotel}</td>
          <td>${leg.price}</td>
          <td><a href="${leg.maps_query}" target="_blank" rel="noopener">Karta ↗</a></td>
          <td>${leg.booking ? `<a href="${leg.booking}" target="_blank" rel="noopener">Boka ↗</a>` : ""}</td>
        </tr>
        <tr class="plan-info-row">
          <td colspan="5">
            ${driveLine ? `<div class="plan-drive">${driveLine}</div>` : ""}
            ${parkingLine ? `<div class="plan-parking">${parkingLine}</div>` : ""}
            ${highlightsLine ? `<div class="plan-highlights">${highlightsLine}</div>` : ""}
          </td>
        </tr>
      `;
    })
    .join("");

  // Total körsträcka/-tid för HELA planen (summerad i plans.py, inkl.
  // sista dagens transfer till flygplatsen), så man kan jämföra "hur
  // mycket bilkörning" planerna innebär utan att räkna ihop etapperna
  // själv.
  const totalDriveLine = plan.total_drive
    ? `🚗 Totalt under resan: ca ${plan.total_drive.km} km körning, ${plan.total_drive.time}`
    : "";

  // Sista dagens transfer (Milano -> Bergamo flygplats för hemflyget) –
  // ingen egen övernattning, bara en kort körning innan man lämnar
  // hyrbilen.
  const transferLine = plan.departure_transfer
    ? `✈️ Sista dagen: kör till Bergamo flygplats (${plan.departure_transfer.km} km, ${plan.departure_transfer.time}) för hemflyget.`
    : "";

  // En enda Google Maps-länk som visar HELA bilrutten i ordning
  // (Bergamo flygplats -> etapp A -> etapp B -> ... -> Bergamo
  // flygplats), så man kan se hela slingan på kartan utan att öppna
  // varje hotells karta för sig.
  const routeMapLine = plan.route_map
    ? `<a class="plan-route-map" href="${plan.route_map}" target="_blank" rel="noopener">🗺️ Se hela bilrutten på kartan ↗</a>`
    : "";

  // Klickbara strandnamn (varje namn länkar direkt till Google Maps) –
  // visas i sammanfattningen så man snabbt ser var man kan sola/bada på
  // den här rutten utan att leta i etapp-tabellen.
  const beachesLine = (plan.beaches || []).length
    ? `<p class="plan-beaches">🏖️ Stränder: ${plan.beaches
        .map(
          (beach) =>
            `<a href="${beach.maps_query}" target="_blank" rel="noopener">${beach.name}</a>`
        )
        .join(", ")}</p>`
    : "";

  // Grov totalkostnad (boende + uppskattad bensin) – räknad ut i plans.py
  // utifrån nätter × pris/natt och total körsträcka. Ingen flygbiljett
  // eller mat inräknat, bara det som faktiskt skiljer planerna åt.
  const costLine = plan.cost_estimate
    ? `<p class="plan-cost">💰 ${plan.cost_estimate.summary}</p>`
    : "";

  // Korten visar alltid det viktigaste på en gång (titel, karta, total
  // körsträcka, röstning) – men etapptabellen och "vad ni kan göra" är
  // ofta det mesta att skrolla igenom, så det göms i en <details> som
  // fälls ut med ett klick, precis som kategorierna under "Hitta platser".
  card.innerHTML = `
    <div class="plan-card-header">
      <strong>${plan.title}</strong>
      <div class="plan-card-actions">
        <button type="button" class="plan-print-btn" title="Skriv ut / spara som PDF">🖨️</button>
        <button type="button" class="plan-share-btn" title="Dela reseplan">🔗</button>
      </div>
    </div>
    <p class="plan-subtitle">${plan.subtitle}</p>
    ${routeMapLine}
    ${totalDriveLine ? `<p class="plan-total-drive">${totalDriveLine}</p>` : ""}
    ${transferLine ? `<p class="plan-transfer">${transferLine}</p>` : ""}
    <details class="plan-details">
      <summary>📋 Etapper, hotell &amp; vad ni kan göra</summary>
      <div class="plan-table-wrap">
        <table class="plan-table">
          <thead>
            <tr>
              <th>Etapp</th>
              <th>Hotellförslag</th>
              <th>Pris</th>
              <th>Karta</th>
              <th>Boka</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      ${
        plan.summary
          ? `<div class="plan-summary">
              <strong>✨ Vad ni kan göra</strong>
              <p>${plan.summary}</p>
              ${beachesLine}
              ${costLine}
            </div>`
          : ""
      }
    </details>
    <div class="vote-row">
      <button class="vote-btn up">👍 <span class="up-count">${plan.votes.up}</span></button>
      <button class="vote-btn down">👎 <span class="down-count">${plan.votes.down}</span></button>
    </div>
    <div class="vote-names"></div>
  `;

  card.querySelector(".up").addEventListener("click", () => sendPlanVote(plan, 1, card));
  card.querySelector(".down").addEventListener("click", () => sendPlanVote(plan, -1, card));
  card.querySelector(".plan-print-btn").addEventListener("click", () => printPlan(plan, card));
  card.querySelector(".plan-share-btn").addEventListener("click", () => sharePlan(plan));

  updateVoteUI(card, plan.votes);

  return card;
}

async function sendPlanVote(plan, voteValue, card) {
  const person = personInput.value.trim();
  if (!person) {
    statusEl.textContent = "Skriv ditt namn först, så vi vet vem som röstar.";
    return;
  }

  const payload = {
    osm_id: plan.id,
    name: plan.title,
    category: "reseplan",
    lat: plan.lat,
    lon: plan.lon,
    person: person,
    vote: voteValue,
  };

  const response = await fetch("/api/vote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    statusEl.textContent = "Kunde inte spara rösten.";
    return;
  }

  const votes = await response.json();
  plan.votes = votes;
  updateVoteUI(card, votes);
  // Rösten kan ha ändrat vilket alternativ som ligger i topp, så bygg om
  // resultattavlan direkt – annars ser man bara sitt eget kort uppdateras
  // och måste själv jämföra siffrorna i alla fyra korten för att veta.
  renderPlanLeaderboard();
  renderPopularityBanner();
  renderKpis();
}

// Skriver ut/sparar en enskild reseplan som PDF via webbläsarens vanliga
// utskriftsdialog (window.print). Fäller ut etapp-detaljerna FÖRST, så de
// kommer med på utskriften även om de var hopfällda på skärmen. En
// @media print-regel i style.css döljer nav/knappar/formulär som inte är
// relevanta på papper.
function printPlan(plan, card) {
  const details = card.querySelector(".plan-details");
  if (details) details.open = true;
  window.print();
}

// Delar reseplanen via webbläsarens inbyggda delningsruta
// (navigator.share – finns på mobil/iOS/Android), eller kopierar en kort
// textsammanfattning + kart-länk till urklipp om delning inte stöds
// (vanligast på dator).
async function sharePlan(plan) {
  const text = `${plan.title}\n${plan.subtitle}${plan.route_map ? `\n${plan.route_map}` : ""}`;

  if (navigator.share) {
    try {
      await navigator.share({ title: plan.title, text, url: plan.route_map || undefined });
    } catch (err) {
      // Användaren ångrade delningen – inget fel att visa.
    }
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    statusEl.textContent = "Reseplanen kopierad till urklipp – klistra in var du vill dela den!";
  } catch (err) {
    statusEl.textContent = "Kunde inte kopiera reseplanen.";
  }
}

findBtn.addEventListener("click", () => {
  if (!personInput.value.trim()) {
    statusEl.textContent = "Skriv ditt namn först, så vi vet vem som röstar.";
    return;
  }
  findNearbyPlaces();
});

function findNearbyPlaces() {
  statusEl.textContent = "Hämtar din position...";
  resultsEl.innerHTML = "";

  // navigator.geolocation är webbläsarens inbyggda GPS-API. Den frågar
  // användaren om lov första gången (popup: "tillåt platsåtkomst?").
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;
      loadPlaces(latitude, longitude);
    },
    (error) => {
      statusEl.textContent = "Kunde inte hämta position: " + error.message;
    }
  );
}

async function loadPlaces(lat, lon) {
  statusEl.textContent = "Letar efter platser i närheten...";

  // Radien (1-10 km, default 2 km) väljs av användaren i dropdownen
  // ovanför "Hitta platser"-knappen – se index.html (#radius) och
  // radiusSelect ovan. Overpass-API:et (se overpass.py) vill ha
  // radien i METER, så vi gångrar km-värdet med 1000.
  const radiusKm = parseInt(radiusSelect.value, 10) || 2;
  const radiusM = radiusKm * 1000;

  const url = `/api/nearby?lat=${lat}&lon=${lon}&radius=${radiusM}`;
  const response = await fetch(url);

  if (!response.ok) {
    statusEl.textContent = "Något gick fel när vi hämtade platser.";
    return;
  }

  const places = await response.json();
  const radiusText = radiusKm === 1 ? "1 km" : `${radiusKm} km`;
  statusEl.textContent = places.length
    ? `Hittade ${places.length} platser inom ${radiusText}.`
    : `Hittade inga platser inom ${radiusText} – prova en större radie.`;

  lastPlaces = places;
  renderPlaces(sortPlacesList(places));
  renderPopularityBanner();
  renderKpis();
  // Om man redan står på Karta-fliken när en ny sökning görs, uppdatera
  // filterknapparna (antalen per kategori har ändrats) och markörerna
  // direkt istället för att vänta på nästa flik-byte.
  if (leafletMap) {
    renderMapCategoryFilter();
    renderMap();
  }
}

// Senast hämtade platser från "Hitta platser" – används av sorteringen,
// "Mest poppis"-bannern och kart-fliken, så de inte behöver göra ett nytt
// nätverksanrop för att visa samma data på olika sätt.
let lastPlaces = [];

sortPlacesSelect.value = localStorage.getItem("sortPlaces") || "distance";
sortPlacesSelect.addEventListener("change", () => {
  localStorage.setItem("sortPlaces", sortPlacesSelect.value);
  if (lastPlaces.length) renderPlaces(sortPlacesList(lastPlaces));
});

// Sorterar EN KOPIA av listan – grupperingen per kategori (renderPlaces)
// sker fortfarande efteråt, så "sortera efter" avgör i vilken ordning
// platserna kommer INOM varje kategori, inte vilka kategorier som visas.
function sortPlacesList(places) {
  const sorted = [...places];
  const mode = sortPlacesSelect.value;
  if (mode === "votes") {
    sorted.sort((a, b) => (b.votes.up - b.votes.down) - (a.votes.up - a.votes.down));
  } else if (mode === "comments") {
    sorted.sort((a, b) => (b.comment_count || 0) - (a.comment_count || 0));
  }
  // "distance" -> ingen omsortering, redan sorterat efter avstånd av servern.
  return sorted;
}

// Hur många platser som visas i "Mest gillat"-listan högst upp.
const TOP_VOTED_COUNT = 5;

// Bygger en liten topplista över de mest uppskattade platserna, oavsett
// kategori. "Poäng" = antal 👍 minus antal 👎 – en plats med 3 gillar och
// 1 ogillar (poäng 2) rankas alltså under en med 2 gillar och 0 ogillar
// (poäng 2 – lika, men avgörs då av flest 👍). Platser utan några röster
// alls är inte intressanta här och filtreras bort.
function renderTopVoted(places) {
  const voted = places
    .map((place) => ({ place, score: place.votes.up - place.votes.down }))
    .filter((entry) => entry.place.votes.up > 0 || entry.place.votes.down > 0)
    .sort((a, b) => b.score - a.score || b.place.votes.up - a.place.votes.up)
    .slice(0, TOP_VOTED_COUNT);

  if (voted.length === 0) return null;

  const section = document.createElement("section");
  section.className = "top-voted";
  section.innerHTML = `<h2>🏆 Mest gillat just nu</h2>`;

  voted.forEach((entry, index) => {
    const { place, score } = entry;
    const row = document.createElement("a");
    row.className = "top-voted-row";
    row.href = `#${placeCardId(place)}`;
    row.addEventListener("click", (event) => {
      event.preventDefault();
      const placeCard = document.getElementById(placeCardId(place));
      // Kortet kan ligga inuti en hopfälld <details>-kategori (se
      // renderPlaces) – måste fällas ut FÖRST, annars scrollar vi till
      // ett osynligt kort.
      const details = placeCard.closest("details");
      if (details) details.open = true;
      placeCard.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    // CATEGORY_LABELS-texten innehåller redan en emoji (t.ex. "🍝
    // Restauranger") – vi visar bara den, inte hela ordet, så raden
    // förblir kompakt men man ser direkt om det är mat, utsikt osv.
    const categoryIcon = (CATEGORY_LABELS[place.category] || "").split(" ")[0];
    row.innerHTML = `
      <span class="top-voted-rank">${index + 1}.</span>
      <span class="top-voted-category" title="${CATEGORY_LABELS[place.category] || ""}">${categoryIcon}</span>
      <span class="top-voted-name">${place.name}</span>
      <span class="top-voted-score">👍 ${place.votes.up} 👎 ${place.votes.down}</span>
    `;
    section.appendChild(row);
  });

  return section;
}

// Ett stabilt id för platsens kort, byggt på dess osm_id (t.ex.
// "node/12345" -> "place-node-12345"). Används både av kortet självt
// och av "Mest gillat"-listans länkar, så ett klick kan hoppa rakt till
// rätt kort längre ner på sidan.
function placeCardId(place) {
  return `place-${place.osm_id.replace("/", "-")}`;
}

function renderPlaces(places) {
  resultsEl.innerHTML = "";

  const topVotedSection = renderTopVoted(places);
  if (topVotedSection) {
    resultsEl.appendChild(topVotedSection);
  }

  // Gruppera platserna per kategori, så vi kan rita en rubrik per grupp.
  // Platserna kommer redan sorterade efter avstånd från servern (se
  // app.py), så den första i varje kategori är den NÄRMASTE.
  const grouped = {};
  for (const place of places) {
    grouped[place.category] = grouped[place.category] || [];
    grouped[place.category].push(place);
  }

  // Snabbnavigering högst upp: en "pill" per kategori. Vi visar ALLA fyra
  // kategorier här, även de utan träffar (med "(0)") – annars ser det ut
  // som att t.ex. Strand saknas helt ur appen, när det egentligen bara
  // inte fanns någon strand taggad i OpenStreetMap nära just den platsen.
  // En tom kategori grås ut och går inte att klicka på (ingen sektion att
  // hoppa till).
  const nav = document.createElement("nav");
  nav.className = "category-nav";
  for (const category of Object.keys(CATEGORY_LABELS)) {
    const placesInCategory = grouped[category] || [];

    const link = document.createElement("a");
    link.href = placesInCategory.length ? `#cat-${category}` : "#";
    link.textContent = `${CATEGORY_LABELS[category]} (${placesInCategory.length})`;
    if (placesInCategory.length === 0) {
      link.classList.add("category-nav-empty");
    }
    link.addEventListener("click", (event) => {
      event.preventDefault();
      if (!placesInCategory.length) return;
      // Kategorin är en hopfälld <details> (se nedan) – fäll ut den
      // innan vi scrollar dit, annars hoppar man till en tom rubrik.
      const details = document.getElementById(`cat-${category}`);
      details.open = true;
      details.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    nav.appendChild(link);
  }
  resultsEl.appendChild(nav);

  for (const category of Object.keys(CATEGORY_LABELS)) {
    const placesInCategory = grouped[category];
    if (!placesInCategory || placesInCategory.length === 0) continue;

    // <details>/<summary> ger oss en hopfälld kategori "på köpet" – man
    // ser bara rubriken (+ antal) tills man klickar, då fälls ALLA
    // platser i kategorin ut. Default hopfälld (ingen "open"-attribut),
    // så man inte måste skrolla förbi 20 kort per kategori för att hitta
    // den man vill se.
    const section = document.createElement("details");
    section.className = "category-details";
    section.id = `cat-${category}`;
    const summary = document.createElement("summary");
    summary.textContent = `${CATEGORY_LABELS[category]} (${placesInCategory.length})`;
    section.appendChild(summary);

    // Visa bara de MAX_PER_CATEGORY (20) närmaste platserna i kategorin.
    const shown = placesInCategory.slice(0, MAX_PER_CATEGORY);

    if (category === "restaurant") {
      // Restauranger delas upp ytterligare per mattyp (OSM-taggen
      // "cuisine"), så man t.ex. lätt hittar "Skaldjur" eller "Italienskt"
      // istället för en enda lång lista – extra praktiskt på en road trip
      // i Ligurien/Nice där matkulturen är en stor del av resan.
      const byCuisine = {};
      for (const place of shown) {
        const label = cuisineLabel(place.cuisine);
        byCuisine[label] = byCuisine[label] || [];
        byCuisine[label].push(place);
      }

      // Egen liten snabbnavigering FÖR mattyperna, samma idé som
      // huvudnavigeringen högst upp men en nivå djupare – annars måste
      // man skrolla igenom alla italienska ställen innan man når
      // skaldjur, t.ex. Hoppar till rätt <h3> via dess id.
      const cuisineNav = document.createElement("nav");
      cuisineNav.className = "cuisine-nav";
      for (const cuisineName of Object.keys(byCuisine)) {
        const cuisineId = `cuisine-${slugify(cuisineName)}`;
        const link = document.createElement("a");
        link.href = `#${cuisineId}`;
        link.textContent = `${cuisineName} (${byCuisine[cuisineName].length})`;
        link.addEventListener("click", (event) => {
          event.preventDefault();
          document
            .getElementById(cuisineId)
            .scrollIntoView({ behavior: "smooth", block: "start" });
        });
        cuisineNav.appendChild(link);
      }
      section.appendChild(cuisineNav);

      for (const [cuisineName, placesForCuisine] of Object.entries(byCuisine)) {
        const subHeading = document.createElement("h3");
        subHeading.id = `cuisine-${slugify(cuisineName)}`;
        subHeading.textContent = cuisineName;
        section.appendChild(subHeading);
        for (const place of placesForCuisine) {
          section.appendChild(renderPlaceCard(place));
        }
      }
    } else {
      for (const place of shown) {
        section.appendChild(renderPlaceCard(place));
      }
    }

    // Finns det fler träffar än vi visar, säg det tydligt istället för
    // att bara tyst klippa bort dem.
    if (placesInCategory.length > MAX_PER_CATEGORY) {
      const hint = document.createElement("p");
      hint.className = "more-hint";
      hint.textContent =
        `Visar de ${MAX_PER_CATEGORY} närmaste av ${placesInCategory.length} hittade.`;
      section.appendChild(hint);
    }

    resultsEl.appendChild(section);
  }
}

function renderPlaceCard(place) {
  const card = document.createElement("div");
  card.className = "card";
  card.id = placeCardId(place);

  const mapsUrl =
    `https://www.google.com/maps/search/?api=1&query=${place.lat},${place.lon}`;
  // Direkt vägbeskrivning (bil) till platsen, istället för bara en
  // sök-länk – praktiskt när man redan är på väg och bara vill ha
  // navigering, inte leta upp platsen själv på kartan först.
  const directionsUrl =
    `https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lon}&travelmode=driving`;

  // distance_m kommer från servern (se app.py: _distance_m). Avrundar till
  // hela meter under 1 km, annars till en decimal i kilometer.
  const distanceText =
    place.distance_m < 1000
      ? `${place.distance_m} m bort`
      : `${(place.distance_m / 1000).toFixed(1)} km bort`;

  card.innerHTML = `
    <div class="card-header">
      <strong>${place.name}</strong>
      <div class="card-links">
        <a href="${mapsUrl}" target="_blank" rel="noopener">Karta ↗</a>
        <a href="${directionsUrl}" target="_blank" rel="noopener">Vägbeskrivning ↗</a>
      </div>
    </div>
    <div class="card-distance">${distanceText}</div>
    <div class="vote-row">
      <button class="vote-btn up">👍 <span class="up-count">${place.votes.up}</span></button>
      <button class="vote-btn down">👎 <span class="down-count">${place.votes.down}</span></button>
    </div>
    <div class="vote-names"></div>
    <details class="comments-details">
      <summary>💬 Kommentarer <span class="comment-count">${place.comment_count ? `(${place.comment_count})` : ""}</span></summary>
      <ul class="comments-list"></ul>
      <form class="comment-form">
        <input type="text" class="comment-input" placeholder="Skriv en kommentar..." autocomplete="off">
        <button type="submit">Skicka</button>
      </form>
    </details>
  `;

  card.querySelector(".up").addEventListener("click", () => sendVote(place, 1, card));
  card.querySelector(".down").addEventListener("click", () => sendVote(place, -1, card));

  // Visa direkt vem som redan röstat (hämtat med platserna från
  // servern), och markera om DET ÄR JAG som redan gillat/ogillat den
  // här platsen – annars vet man inte varför knappen ser "tryckt" ut.
  updateVoteUI(card, place.votes);

  // Kommentarerna hämtas bara EN gång, första gången man fäller ut
  // <details> – annars skulle vi göra ett onödigt nätverksanrop per
  // plats redan vid sidladdning (kan vara 100+ platser i en kategori).
  const commentsDetails = card.querySelector(".comments-details");
  let commentsLoaded = false;
  commentsDetails.addEventListener("toggle", () => {
    if (commentsDetails.open && !commentsLoaded) {
      commentsLoaded = true;
      loadComments(place.osm_id, card);
    }
  });

  card.querySelector(".comment-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitComment(place.osm_id, card);
  });

  return card;
}

async function loadComments(osmId, card) {
  const listEl = card.querySelector(".comments-list");
  listEl.innerHTML = `<li class="comment-loading">Hämtar kommentarer...</li>`;

  const response = await fetch(`/api/comments?osm_id=${encodeURIComponent(osmId)}`);
  if (!response.ok) {
    listEl.innerHTML = `<li class="comment-loading">Kunde inte hämta kommentarer.</li>`;
    return;
  }

  const comments = await response.json();
  renderComments(comments, card);
}

function renderComments(comments, card) {
  const listEl = card.querySelector(".comments-list");
  listEl.innerHTML = "";

  if (comments.length === 0) {
    listEl.innerHTML = `<li class="comment-empty">Inga kommentarer än – skriv den första!</li>`;
    return;
  }

  for (const comment of comments) {
    listEl.appendChild(renderCommentRow(comment));
  }
}

function renderCommentRow(comment) {
  const row = document.createElement("li");
  row.className = "comment-row";
  row.innerHTML = `
    <span class="comment-text"><strong>${comment.person}:</strong> ${comment.text}</span>
  `;
  return row;
}

async function submitComment(osmId, card) {
  const person = personInput.value.trim();
  if (!person) {
    statusEl.textContent = "Skriv ditt namn först, så vi vet vem som kommenterar.";
    return;
  }

  const input = card.querySelector(".comment-input");
  const text = input.value.trim();
  if (!text) return;

  const response = await fetch("/api/comments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ osm_id: osmId, person, text }),
  });

  if (!response.ok) {
    statusEl.textContent = "Kunde inte spara kommentaren.";
    return;
  }

  const newComment = await response.json();
  input.value = "";

  const listEl = card.querySelector(".comments-list");
  const empty = listEl.querySelector(".comment-empty");
  if (empty) empty.remove();
  listEl.appendChild(renderCommentRow(newComment));

  // Uppdatera räknaren i <summary> direkt, utan att hämta om listan.
  const countEl = card.querySelector(".comment-count");
  const current = listEl.querySelectorAll(".comment-row").length;
  countEl.textContent = `(${current})`;
}

// Skriver om röstknapparnas utseende (markerad/inte) och listan med
// namn under dem, utifrån den senaste röstsammanfattningen från
// servern. Används både direkt vid sidladdning och efter varje klick.
function updateVoteUI(card, votes) {
  card.querySelector(".up-count").textContent = votes.up;
  card.querySelector(".down-count").textContent = votes.down;

  const me = personInput.value.trim();
  card.querySelector(".up").classList.toggle("active", votes.up_names.includes(me));
  card.querySelector(".down").classList.toggle("active", votes.down_names.includes(me));

  const namesParts = [];
  if (votes.up_names.length) namesParts.push(`👍 ${votes.up_names.join(", ")}`);
  if (votes.down_names.length) namesParts.push(`👎 ${votes.down_names.join(", ")}`);
  card.querySelector(".vote-names").textContent = namesParts.join("   ");
}

async function sendVote(place, voteValue, card) {
  const person = personInput.value.trim();
  if (!person) {
    statusEl.textContent = "Skriv ditt namn först, så vi vet vem som röstar.";
    return;
  }

  const payload = {
    osm_id: place.osm_id,
    name: place.name,
    category: place.category,
    lat: place.lat,
    lon: place.lon,
    person: person,
    vote: voteValue,
  };

  const response = await fetch("/api/vote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    statusEl.textContent = "Kunde inte spara rösten.";
    return;
  }

  // Servern svarar med den FULLA, uppdaterade sammanfattningen – den
  // vet om klicket räknades som en ny röst eller tog bort en gammal
  // (klickar man 👍 två gånger i rad försvinner rösten igen, precis
  // som man "ångrar" ett gilla-markering).
  const votes = await response.json();
  place.votes = votes;
  updateVoteUI(card, votes);
}

// ---------------------------------------------------------------------------
// Packlista – delad checklista (se db.py: packing_items / app.py: /api/packing).
// Laddas direkt vid sidladdning (precis som reseplanerna) eftersom den inte
// behöver GPS-position, och uppdateras live för alla utan att sidan laddas om.
// ---------------------------------------------------------------------------

const packingForm = document.getElementById("packing-form");
const packingInput = document.getElementById("packing-input");
const packingForSelect = document.getElementById("packing-for");
const packingListEl = document.getElementById("packing-list");
const packingFilterEl = document.getElementById("packing-filter");

// Vilken person-flik som är vald just nu i packlistan ("alla" = ingen
// filtrering). Sparas i en vanlig variabel (inte localStorage) – det är
// en visningsinställning för stunden, inget man behöver komma ihåg
// mellan besök.
let packingFilter = "alla";
let allPackingItems = [];

loadPacking();

packingFilterEl.addEventListener("click", (event) => {
  const button = event.target.closest(".packing-filter-btn");
  if (!button) return;
  packingFilter = button.dataset.filter;
  packingFilterEl
    .querySelectorAll(".packing-filter-btn")
    .forEach((b) => b.classList.toggle("active", b === button));
  renderPacking(allPackingItems);
});

async function loadPacking() {
  const response = await fetch("/api/packing");
  if (!response.ok) return;
  const items = await response.json();
  allPackingItems = items;
  renderPacking(items);
}

function renderPacking(items) {
  packingListEl.innerHTML = "";

  const visible =
    packingFilter === "alla"
      ? items
      : items.filter((item) => item.for_person === packingFilter || item.for_person === "Alla");

  if (visible.length === 0) {
    const empty = document.createElement("li");
    empty.className = "packing-empty";
    empty.textContent = items.length
      ? "Inget i listan för det filtret än."
      : "Listan är tom – lägg till första grejen ovan!";
    packingListEl.appendChild(empty);
    return;
  }

  // Obockade saker först (det som fortfarande behöver packas), sen det
  // som redan är klart – annars drunknar det man faktiskt behöver göra
  // längst ner i en lång lista av redan-packade-saker.
  const sorted = [...visible].sort((a, b) => Number(a.done) - Number(b.done));

  for (const item of sorted) {
    packingListEl.appendChild(renderPackingItem(item));
  }
}

// Liten färgad etikett som visar vem grejen är till – "Alla" får en
// neutral grå, namnen sin egen ton, så man snabbt ser i listan vems
// väska man tittar på.
function forPersonBadge(forPerson) {
  const cls = forPerson === "Alla" ? "packing-for-alla" : "packing-for-person";
  return `<span class="packing-for ${cls}">${forPerson}</span>`;
}

function renderPackingItem(item) {
  const row = document.createElement("li");
  row.className = "packing-item" + (item.done ? " packing-done" : "");

  row.innerHTML = `
    <label class="packing-label">
      <input type="checkbox" ${item.done ? "checked" : ""}>
      <span class="packing-text">${item.item}</span>
      ${forPersonBadge(item.for_person || "Alla")}
    </label>
    <span class="packing-added-by">tillagt av ${item.added_by}</span>
    <button type="button" class="packing-delete" aria-label="Ta bort">✕</button>
  `;

  row.querySelector("input").addEventListener("change", () => togglePacking(item, row));
  row.querySelector(".packing-delete").addEventListener("click", () => deletePacking(item, row));

  return row;
}

async function togglePacking(item, row) {
  const response = await fetch(`/api/packing/${item.id}/toggle`, { method: "POST" });
  if (!response.ok) return;
  const result = await response.json();
  item.done = result.done;
  row.classList.toggle("packing-done", item.done);
}

async function deletePacking(item, row) {
  const response = await fetch(`/api/packing/${item.id}`, { method: "DELETE" });
  if (!response.ok) return;
  row.remove();
  allPackingItems = allPackingItems.filter((i) => i.id !== item.id);
  // Visa "listan är tom"-meddelandet om det var sista raden (i det
  // aktuella filtret).
  if (!packingListEl.querySelector(".packing-item")) {
    renderPacking(allPackingItems);
  }
}

packingForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const person = personInput.value.trim();
  if (!person) {
    statusEl.textContent = "Skriv ditt namn först, så vi vet vem som lade till.";
    return;
  }

  const text = packingInput.value.trim();
  if (!text) return;

  const forPerson = packingForSelect.value;

  const response = await fetch("/api/packing", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item: text, person, for_person: forPerson }),
  });

  if (!response.ok) {
    statusEl.textContent = "Kunde inte lägga till i packlistan.";
    return;
  }

  const newItem = await response.json();
  packingInput.value = "";
  allPackingItems.push(newItem);

  // Rendera om hela (filtrerade) listan istället för att bara stoppa in
  // raden längst ner – annars syns den nya grejen även när filtret inte
  // matchar (t.ex. man lägger till något för "Viana" men "Reza"-filtret
  // är aktivt).
  renderPacking(allPackingItems);
});
