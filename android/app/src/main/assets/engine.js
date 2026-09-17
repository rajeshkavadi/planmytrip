/* PlanMyTrip offline engine — a JS port of the backend intelligence
   (scoring, season, itinerary, cost, sample inventory) over window.PMT_DATA.
   Keeps the app fully self-contained on-device: no server needed. */
(function (global) {
  "use strict";
  const DATA = global.PMT_DATA || { destinations: [], wellness: [] };
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const CROWD_PENALTY = { very_low: 0, low: 2, moderate: 6, high: 14, peak: 22 };
  const INTENSITY_POINTS = { low: 1, medium: 2, high: 3 };
  const TOD_ORDER = { sunrise: 0, morning: 1, any: 2, afternoon: 3, evening: 4 };
  const W_INTENT = 0.55, W_SEASON = 0.35, DEFAULT_FIT = 30;

  const bySlug = {};
  DATA.destinations.forEach(d => { bySlug[d.slug] = d; });

  // ---------- season ----------
  function suitOf(s) { return Math.max(0, s.weather_score - (CROWD_PENALTY[s.crowd] || 0)); }
  function suitArray(dest) {
    const by = {}; dest.seasons.forEach(s => { by[s.month] = suitOf(s); });
    const a = []; for (let m = 1; m <= 12; m++) a.push(Math.round((by[m] || 0) * 10) / 10); return a;
  }
  function bestWindows(suit, threshold) {
    threshold = threshold || 70;
    const good = new Set(); for (let m = 0; m < 12; m++) if (suit[m] >= threshold) good.add(m);
    if (!good.size) return []; if (good.size === 12) return ["Year-round"];
    let start = [...good].find(m => !good.has((m + 11) % 12));
    const order = []; for (let i = 0; i < 12; i++) order.push((start + i) % 12);
    const runs = []; let run = [];
    order.forEach(m => { if (good.has(m)) run.push(m); else if (run.length) { runs.push(run); run = []; } });
    if (run.length) runs.push(run);
    return runs.map(r => r.length === 1 ? MONTHS[r[0]] : MONTHS[r[0]] + "–" + MONTHS[r[r.length - 1]]);
  }
  function sweetSpot(dest) {
    const suit = {}, crowd = {};
    dest.seasons.forEach(s => { suit[s.month] = suitOf(s); crowd[s.month] = CROWD_PENALTY[s.crowd] || 0; });
    const peak = Math.max(...Object.values(suit));
    const peakCrowd = Math.max(...Object.values(crowd));
    const out = [];
    for (let m = 1; m <= 12; m++) {
      if (suit[m] >= peak - 12 && crowd[m] <= Math.max(0, peakCrowd - 6)) out.push(m);
    }
    return out.sort((a, b) => a - b);
  }
  function seasonReport(dest, month) {
    const s = dest.seasons.find(x => x.month === month);
    const suit = suitArray(dest);
    const windows = bestWindows(suit);
    const sweet = sweetSpot(dest);
    const caveats = []; let verdict = "unknown", suitability = 0;
    if (s) {
      suitability = Math.round(suitOf(s) * 10) / 10;
      verdict = suitability >= 78 ? "excellent" : suitability >= 60 ? "good" : suitability >= 40 ? "workable" : "avoid";
      if (s.rainfall_mm >= 150) caveats.push("Heavy rain likely (" + s.rainfall_mm + "mm avg) — monsoon tail; pack layers.");
      else if (s.rainfall_mm >= 60) caveats.push("Some showers possible (" + s.rainfall_mm + "mm avg).");
      if (s.crowd === "high" || s.crowd === "peak") caveats.push("Crowded this month (" + s.crowd.replace("_", " ") + ") — book early.");
      if (s.festival) caveats.push(s.festival + " — vivid, but rooms spike; reserve ahead.");
    }
    return { month: MONTHS[month - 1], verdict, suitability, best_windows: windows,
             sweet_spot: sweet.map(m => MONTHS[m - 1]), in_sweet_spot: sweet.indexOf(month) >= 0, caveats };
  }

  // ---------- discovery ranking ----------
  function budgetAdj(base, budget) {
    if (!budget) return [0, false];
    if (base <= budget) return [Math.min(6, (budget - base) / budget * 12), false];
    return [-Math.min(30, (base - budget) / budget * 45), true];
  }
  function rankDestinations(intent, month, budget, limit) {
    limit = limit || 12;
    const scored = DATA.destinations.map(d => {
      const fit = (d.fits && d.fits[intent] != null) ? d.fits[intent] : DEFAULT_FIT;
      const s = d.seasons.find(x => x.month === month);
      const season = s ? suitOf(s) : 50;
      const adj = budgetAdj(d.base_cost_inr, budget);
      let composite = W_INTENT * fit + W_SEASON * season + adj[0];
      composite = Math.round(Math.max(0, Math.min(100, composite)) * 10) / 10;
      const bits = [fit + "/100 for " + intent];
      if (s) bits.push(MONTHS[month - 1] + " is " + Math.round(season) + "/100 here");
      if (adj[1]) bits.push("over budget"); else if (adj[0] > 0) bits.push("comfortably in budget");
      return { dest: d, composite: composite, intent_fit: fit, over: adj[1], why: bits.join(" · ") };
    }).filter(x => !x.over);
    scored.sort((a, b) => b.composite - a.composite);
    return scored.slice(0, limit);
  }

  // ---------- itinerary ----------
  const DAY_START = 510, DAY_END = 1200, LUNCH_EARLIEST = 750, LUNCH_MIN = 45;
  const HEAT_START = 780, HEAT_END = 930, MAX_POINTS = 6, REST_HIGH = 30, LONG_HOP = 75, REST_HOP = 20;
  const SPEED = 22, MIN_HOP = 8;
  function hhmm(m) { return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"); }
  function haversine(a, b, c, d) {
    const R = 6371, dl = (c - a) * Math.PI / 180, dn = (d - b) * Math.PI / 180;
    const x = Math.sin(dl / 2) ** 2 + Math.cos(a * Math.PI / 180) * Math.cos(c * Math.PI / 180) * Math.sin(dn / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  function travelMin(a, b, c, d) { const km = haversine(a, b, c, d); if (km <= 0) return 0; return Math.max(MIN_HOP, Math.round(km / SPEED * 60)); }
  function pts(p) { return INTENSITY_POINTS[p.intensity] || 2; }
  function overlaps(a, b, c, d) { return a < d && c < b; }

  function buildItinerary(places, days) {
    days = Math.max(1, days);
    const ordered = places.slice().sort((a, b) => (b.priority || 50) - (a.priority || 50));
    const buckets = Array.from({ length: days }, () => []);
    const dayPts = new Array(days).fill(0);
    const leftover = [];
    ordered.forEach(p => {
      let placed = false;
      for (let d = 0; d < days; d++) { if (dayPts[d] + pts(p) <= MAX_POINTS) { buckets[d].push(p); dayPts[d] += pts(p); placed = true; break; } }
      if (!placed) leftover.push(p);
    });
    const outDays = []; const overflow = leftover.slice();
    for (let di = 0; di < days; di++) {
      const list = buckets[di].slice().sort((a, b) => (TOD_ORDER[a.time_of_day] - TOD_ORDER[b.time_of_day]) || ((b.priority || 50) - (a.priority || 50)));
      const stops = []; let t = DAY_START, loc = null, hadLunch = false, dpts = 0;
      list.forEach(p => {
        if (loc) {
          const tt = travelMin(loc[0], loc[1], p.lat, p.lon);
          if (tt > 0) { stops.push({ kind: "travel", start: hhmm(t), end: hhmm(t + tt), title: "Travel to " + p.name, detail: "~" + tt + " min" }); t += tt;
            if (tt >= LONG_HOP) { stops.push({ kind: "rest", start: hhmm(t), end: hhmm(t + REST_HOP), title: "Breather", detail: "Long transfer — short rest" }); t += REST_HOP; } }
        }
        if (!hadLunch && t >= LUNCH_EARLIEST) { stops.push({ kind: "meal", start: hhmm(t), end: hhmm(t + LUNCH_MIN), title: "Lunch", detail: "Paced in, not skipped" }); t += LUNCH_MIN; hadLunch = true; }
        const openM = (p.open_hour || 0) * 60; let note = p.note || "";
        if (t < openM) { if (openM >= DAY_END) { overflow.push(p); return; } note = (note ? note + " · " : "") + "opens " + String(p.open_hour).padStart(2, "0") + ":00"; t = openM; }
        if (p.weather_sensitive && overlaps(t, t + p.visit_minutes, HEAT_START, HEAT_END)) { t = HEAT_END; note = (note ? note + " · " : "") + "shifted past midday heat"; }
        const startV = t, endV = t + p.visit_minutes, closeM = (p.close_hour || 24) * 60;
        if (endV > closeM || endV > DAY_END) { overflow.push(p); return; }
        const tod = p.time_of_day === "any" ? "" : (p.time_of_day + " · ");
        stops.push({ kind: "visit", start: hhmm(startV), end: hhmm(endV), title: p.name, detail: tod + p.category + (note ? " · " + note : "") });
        t = endV; dpts += pts(p); loc = [p.lat, p.lon];
        if (p.intensity === "high" && t + REST_HIGH <= DAY_END) { stops.push({ kind: "rest", start: hhmm(t), end: hhmm(t + REST_HIGH), title: "Rest", detail: "Recovery after a high-intensity stop" }); t += REST_HIGH; }
      });
      const active = stops.filter(s => s.kind === "visit").reduce((a, s) => a + (toMin(s.end) - toMin(s.start)), 0);
      outDays.push({ day: di + 1, intensity_points: dpts, active_minutes: active, stops });
    }
    return { days: outDays, unscheduled: overflow.map(p => ({ name: p.name })) };
  }
  function toMin(s) { const p = s.split(":"); return (+p[0]) * 60 + (+p[1]); }
  function applyFlightArrival(plan, arrivalHHMM, buffer) {
    buffer = buffer == null ? 60 : buffer;
    plan = JSON.parse(JSON.stringify(plan));
    const cutoff = toMin(arrivalHHMM) + buffer; const changes = [];
    if (plan.days && plan.days.length) {
      const d1 = plan.days[0]; let kept = [], dropped = [];
      d1.stops.forEach(s => { if (s.kind === "visit" && toMin(s.start) < cutoff) dropped.push(s); else kept.push(s); });
      const fv = kept.findIndex(s => s.kind === "visit");
      if (fv > 0) kept = kept.slice(fv);
      else if (!kept.length) kept = [{ kind: "rest", start: arrivalHHMM, end: arrivalHHMM, title: "Arrive & settle in", detail: "Flight lands late — Day 1 kept as arrival + rest" }];
      d1.stops = kept;
      d1.active_minutes = kept.filter(s => s.kind === "visit").reduce((a, s) => a + (toMin(s.end) - toMin(s.start)), 0);
      dropped.forEach(s => changes.push("Dropped '" + s.title + "' (started " + s.start + ", before arrival " + arrivalHHMM + ")"));
    }
    plan.changes = changes.length ? changes : ["Flight arrival still fits the plan — no changes."];
    return plan;
  }

  // ---------- cost ----------
  function estimateCost(nights, flightInr, stayPerNight) {
    const days = nights + 1;
    const lines = [
      { label: "Flights (return)", amount_inr: flightInr, hidden: false },
      { label: "Stays · " + nights + " nights", amount_inr: stayPerNight * nights, hidden: false },
      { label: "Local transport & transfers", amount_inr: 1000 * days, hidden: true },
      { label: "Entries, activities & permits", amount_inr: 250 * days, hidden: true },
      { label: "Data (eSIM) & tips", amount_inr: 150 * days, hidden: true },
      { label: "Food (estimate)", amount_inr: 900 * days, hidden: false }
    ];
    const total = lines.reduce((a, l) => a + l.amount_inr, 0);
    const hidden = lines.filter(l => l.hidden).reduce((a, l) => a + l.amount_inr, 0);
    return { lines, total_inr: total, hidden_total_inr: hidden };
  }

  // ---------- sample inventory ----------
  const AIR = [["IndiGo","6E"],["Air India","AI"],["Vistara","UK"],["Akasa Air","QP"],["SpiceJet","SG"]];
  const SLOTS = [["06:10","08:20",130,0,1.30],["11:30","15:05",215,1,0.85],["19:40","21:55",135,0,1.10]];
  function seed(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }
  function sampleFlights(slug, base) {
    const bf = Math.max(2500, Math.round(base * 0.22));
    return SLOTS.map((sl, i) => {
      const h = seed(slug + i), a = AIR[h % AIR.length];
      return { airline: a[0], flight_no: a[1] + "-" + (1000 + h % 8999), depart: sl[0], arrive: sl[1],
               duration_min: sl[2], stops: sl[3], price_inr: Math.round(bf * sl[4] / 100) * 100 + (h % 6) * 100 };
    });
  }
  const TIERS = [["Heritage / boutique",4.7,1.9],["Mid-range comfort",4.2,1.0],["Smart budget",3.9,0.6]];
  function sampleHotels(slug, name, base) {
    const bn = Math.max(1200, Math.round(base * 0.09)); const areas = ["Old town","Near centre","Lakeside"];
    const first = (name || "The").split(" ")[0];
    return TIERS.map((t, i) => ({ name: "The " + first + " " + ["Residency","House","Stay"][i], area: areas[i % 3],
      style: t[0], rating: t[1], price_per_night_inr: Math.round(bn * t[2] / 100) * 100 + (seed(slug + "h" + i) % 5) * 100 }));
  }

  // ---------- living trip doc ----------
  function tripDoc(dest, month, nights, pax, flightInr, stayPerNight, flightDesc, hotelName) {
    const cost = estimateCost(nights, flightInr || 9000, stayPerNight || 3500);
    cost.party_size = pax; cost.trip_total_inr = cost.total_inr * pax;
    return {
      title: dest.name, nights: nights,
      booking: { flight: flightDesc || null, hotel: hotelName || null },
      season: seasonReport(dest, month), cost: cost,
      shopping: { bargaining_norm: dest.bargaining_norm, items: dest.shopping }
    };
  }

  global.PMT = {
    MONTHS: MONTHS, destinations: DATA.destinations, wellness: DATA.wellness, bySlug: bySlug,
    suitArray, bestWindows, seasonReport, rankDestinations,
    buildItinerary, applyFlightArrival, estimateCost, sampleFlights, sampleHotels, tripDoc
  };
})(window);
