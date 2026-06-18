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
    });
  });
}
initTabs();

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

function renderPlans(plans) {
  plansEl.innerHTML = "";

  const heading = document.createElement("h2");
  heading.textContent = "🗺️ Vilken reseplan gillar du bäst?";
  plansEl.appendChild(heading);

  const intro = document.createElement("p");
  intro.className = "plans-intro";
  intro.textContent =
    "Samma flyg (Stockholm ↔ Bergamo, 16 juli–5 augusti) men olika sätt att dela upp de 20 nätterna. Rösta på den ni gillar mest!";
  plansEl.appendChild(intro);

  for (const plan of plans) {
    plansEl.appendChild(renderPlanCard(plan));
  }
}

function renderPlanCard(plan) {
  const card = document.createElement("div");
  card.className = "plan-card";
  card.id = planCardId(plan);

  const rows = plan.legs
    .map(
      (leg) => `
        <tr>
          <td>
            <strong>${leg.name}</strong><br>
            <span class="plan-nights">${leg.nights}</span>
          </td>
          <td>${leg.hotel}</td>
          <td>${leg.price}</td>
          <td><a href="${leg.maps_query}" target="_blank" rel="noopener">Karta ↗</a></td>
        </tr>
      `
    )
    .join("");

  card.innerHTML = `
    <div class="plan-card-header">
      <strong>${plan.title}</strong>
    </div>
    <p class="plan-subtitle">${plan.subtitle}</p>
    <table class="plan-table">
      <thead>
        <tr>
          <th>Etapp</th>
          <th>Hotellförslag</th>
          <th>Pris</th>
          <th>Karta</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="vote-row">
      <button class="vote-btn up">👍 <span class="up-count">${plan.votes.up}</span></button>
      <button class="vote-btn down">👎 <span class="down-count">${plan.votes.down}</span></button>
    </div>
    <div class="vote-names"></div>
  `;

  card.querySelector(".up").addEventListener("click", () => sendPlanVote(plan, 1, card));
  card.querySelector(".down").addEventListener("click", () => sendPlanVote(plan, -1, card));

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

  renderPlaces(places);
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
      document
        .getElementById(placeCardId(place))
        .scrollIntoView({ behavior: "smooth", block: "center" });
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
      document
        .getElementById(`cat-${category}`)
        .scrollIntoView({ behavior: "smooth", block: "start" });
    });
    nav.appendChild(link);
  }
  resultsEl.appendChild(nav);

  for (const category of Object.keys(CATEGORY_LABELS)) {
    const placesInCategory = grouped[category];
    if (!placesInCategory || placesInCategory.length === 0) continue;

    const section = document.createElement("section");
    section.id = `cat-${category}`;
    section.innerHTML = `<h2>${CATEGORY_LABELS[category]}</h2>`;

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

  // distance_m kommer från servern (se app.py: _distance_m). Avrundar till
  // hela meter under 1 km, annars till en decimal i kilometer.
  const distanceText =
    place.distance_m < 1000
      ? `${place.distance_m} m bort`
      : `${(place.distance_m / 1000).toFixed(1)} km bort`;

  card.innerHTML = `
    <div class="card-header">
      <strong>${place.name}</strong>
      <a href="${mapsUrl}" target="_blank" rel="noopener">Karta ↗</a>
    </div>
    <div class="card-distance">${distanceText}</div>
    <div class="vote-row">
      <button class="vote-btn up">👍 <span class="up-count">${place.votes.up}</span></button>
      <button class="vote-btn down">👎 <span class="down-count">${place.votes.down}</span></button>
    </div>
    <div class="vote-names"></div>
  `;

  card.querySelector(".up").addEventListener("click", () => sendVote(place, 1, card));
  card.querySelector(".down").addEventListener("click", () => sendVote(place, -1, card));

  // Visa direkt vem som redan röstat (hämtat med platserna från
  // servern), och markera om DET ÄR JAG som redan gillat/ogillat den
  // här platsen – annars vet man inte varför knappen ser "tryckt" ut.
  updateVoteUI(card, place.votes);

  return card;
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
