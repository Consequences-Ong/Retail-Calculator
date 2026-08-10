import os
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Optional
import psycopg2

app = FastAPI()

# ---------------------------------------------------------------
# DEFAULT DATA (same as your Tkinter version, all values in USD)
# ---------------------------------------------------------------
DEFAULT_ITEMS = [
    {"name": "Leather Jacket",          "season": "Winter",   "retail": 240, "distributor": 205, "prod": 75.0,  "weight": 1.8},
    {"name": "Shearling Jacket",        "season": "Winter",   "retail": 300, "distributor": 291, "prod": 150.0, "weight": 2.7},
    {"name": "Motorbike/Racing Jacket", "season": "Winter",   "retail": 280, "distributor": 245, "prod": 110.0, "weight": 2.3},
    {"name": "Wool Overcoat",           "season": "Winter",   "retail": 175, "distributor": 157, "prod": 58.0,  "weight": 2.2},
    {"name": "Varsity/Bomber Jacket",   "season": "Winter",   "retail": 110, "distributor": 88,  "prod": 23.0,  "weight": 1.3},
    {"name": "Denim Jacket",            "season": "Winter",   "retail": 105, "distributor": 77,  "prod": 26.0,  "weight": 0.8},
    {"name": "Wool/Knit Sweater",       "season": "Winter",   "retail": 65,  "distributor": 52,  "prod": 15.0,  "weight": 0.7},
    {"name": "Fleece Hoodie",           "season": "Winter",   "retail": 65,  "distributor": 47,  "prod": 14.0,  "weight": 0.6},
    {"name": "Leather Vest",            "season": "All-Year", "retail": 120, "distributor": 92,  "prod": 34.0,  "weight": 0.8},
    {"name": "Denim Jeans",             "season": "All-Year", "retail": 85,  "distributor": 56,  "prod": 15.0,  "weight": 0.8},
    {"name": "Cargo Pants",             "season": "All-Year", "retail": 65,  "distributor": 50,  "prod": 14.0,  "weight": 0.7},
    {"name": "Flannel Shirt",           "season": "All-Year", "retail": 45,  "distributor": 31,  "prod": 9.0,   "weight": 0.4},
    {"name": "Polo Shirt",              "season": "All-Year", "retail": 40,  "distributor": 23,  "prod": 8.0,   "weight": 0.22},
    {"name": "Linen Shirt",             "season": "Summer",   "retail": 48,  "distributor": 30,  "prod": 12.0,  "weight": 0.2},
    {"name": "Shorts",                  "season": "Summer",   "retail": 38,  "distributor": 25,  "prod": 8.0,   "weight": 0.3},
    {"name": "T-shirt (regular)",       "season": "Summer",   "retail": 30,  "distributor": 16,  "prod": 5.0,   "weight": 0.2},
    {"name": "T-shirt (oversized)",     "season": "Summer",   "retail": 42,  "distributor": 23,  "prod": 7.0,   "weight": 0.28},
]

DEFAULT_SETTINGS = {
    "duty_rate": 0.28,
    "transfer_multiplier": 1.4,
    "tax_rate": 0.0125,
    "split": 0.50,
    "remit_loss": 0.02,
    "pkr_per_usd": 277.6,
    "insurance_rate": 0.0125,
}

SHIPPING_TIERS_PKR = [
    (0.5, 12262), (1, 12262), (1.5, 17376), (2, 17376),
    (2.1, 32054), (2.5, 32054), (3, 32054), (4, 32054), (5, 32054),
    (5.1, 53201), (6, 53201), (7, 53201), (8, 53201), (9, 53201), (10, 58321),
    (12, 81871), (14, 83913), (16, 109501), (18, 109501), (20, 109501),
    (20.1, 120320), (25, 130785), (30, 204371), (35, 269092), (40, 307579),
    (45, 346061), (50, 382184), (50.1, 389834),
    (60, 458676), (70, 535177), (80, 607888), (90, 683912), (100, 759935), (100.1, 767535),
]

# ---------------------------------------------------------------
# PERSISTENT STORAGE (Postgres) — falls back to defaults if
# DATABASE_URL isn't set, but changes won't survive restarts then.
# ---------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    if not DATABASE_URL:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value JSONB NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_state():
    if not DATABASE_URL:
        return {"items": [dict(i) for i in DEFAULT_ITEMS], "settings": dict(DEFAULT_SETTINGS)}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM app_state WHERE key IN ('items','settings')")
    rows = dict(cur.fetchall())
    cur.close()
    conn.close()
    items = rows.get("items") or [dict(i) for i in DEFAULT_ITEMS]
    settings = rows.get("settings") or dict(DEFAULT_SETTINGS)
    if not rows:
        persist("items", items)
        persist("settings", settings)
    return {"items": items, "settings": settings}

def persist(key, value):
    if not DATABASE_URL:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO app_state (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (key, json.dumps(value)))
    conn.commit()
    cur.close()
    conn.close()

init_db()
STATE = load_state()

def get_shipping_cost(total_weight_kg, pkr_per_usd):
    for ceiling_kg, cost_pkr in SHIPPING_TIERS_PKR:
        if total_weight_kg <= ceiling_kg:
            return cost_pkr / pkr_per_usd
    last_kg, last_cost = SHIPPING_TIERS_PKR[-1]
    return total_weight_kg * (last_cost / last_kg) / pkr_per_usd

def get_price(item, mode):
    return item["retail"] if mode == "retail" else item["distributor"]

def compute_shipment_cost(cart_items, settings, mode):
    total_weight = sum(it["weight"] * q for it, q in cart_items)
    shipping_usd = get_shipping_cost(total_weight, settings["pkr_per_usd"])
    is_batch = total_weight > 2.0
    if is_batch:
        duty_usd = sum(settings["duty_rate"] * settings["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
    else:
        duty_usd = sum(settings["duty_rate"] * get_price(it, mode) * q for it, q in cart_items)
    return duty_usd, shipping_usd, is_batch, total_weight

def optimal_split_single_item(item, qty, settings, mode):
    def shipment_cost(j):
        duty, shipping, _, _ = compute_shipment_cost([(item, j)], settings, mode)
        return duty + shipping
    INF = float("inf")
    dp = [0.0] + [INF] * qty
    choice = [0] * (qty + 1)
    for q in range(1, qty + 1):
        for j in range(1, q + 1):
            c = dp[q - j] + shipment_cost(j)
            if c < dp[q]:
                dp[q] = c
                choice[q] = j
    shipments = []
    remaining = qty
    while remaining > 0:
        j = choice[remaining]
        shipments.append(j)
        remaining -= j
    return sorted(shipments, reverse=True), dp[qty]

def best_proportional_split(cart_items, settings, mode, max_shipments=10):
    total_qty = sum(q for _, q in cart_items)
    max_shipments = max(1, min(max_shipments, total_qty))
    best_cost, best_plan = None, None
    for n in range(1, max_shipments + 1):
        shipments = [[] for _ in range(n)]
        for it, q in cart_items:
            base, rem = divmod(q, n)
            for i in range(n):
                amt = base + (1 if i < rem else 0)
                if amt > 0:
                    shipments[i].append((it, amt))
        total_cost = 0.0
        for shp in shipments:
            if not shp:
                continue
            duty, shipping, _, _ = compute_shipment_cost(shp, settings, mode)
            total_cost += duty + shipping
        if best_cost is None or total_cost < best_cost:
            best_cost = total_cost
            best_plan = [sum(q for _, q in shp) for shp in shipments if shp]
    return best_plan, best_cost

def find_best_shipping_plan(cart_items, settings, mode, max_shipments=10):
    if len(cart_items) == 1:
        item, qty = cart_items[0]
        return optimal_split_single_item(item, qty, settings, mode)
    return best_proportional_split(cart_items, settings, mode, max_shipments)

# ---------------------------------------------------------------
# API models
# ---------------------------------------------------------------
class SettingsIn(BaseModel):
    duty_rate: Optional[float] = None
    transfer_multiplier: Optional[float] = None
    tax_rate: Optional[float] = None
    split: Optional[float] = None
    remit_loss: Optional[float] = None
    pkr_per_usd: Optional[float] = None
    insurance_rate: Optional[float] = None

class ItemIn(BaseModel):
    name: str
    season: str = "All-Year"
    retail: float
    distributor: float
    prod: float
    weight: float

class CalcIn(BaseModel):
    quantities: Dict[str, int]
    price_mode: str = "retail"
    insurance_enabled: bool = False

# ---------------------------------------------------------------
# API routes
# ---------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/api/state")
def get_state():
    return STATE

@app.post("/api/settings")
def update_settings(s: SettingsIn):
    for k, v in s.dict(exclude_none=True).items():
        STATE["settings"][k] = v
    persist("settings", STATE["settings"])
    return STATE["settings"]

@app.post("/api/items")
def add_item(item: ItemIn):
    STATE["items"].append(item.dict())
    persist("items", STATE["items"])
    return STATE["items"]

@app.put("/api/items/{name}")
def edit_item(name: str, item: ItemIn):
    for i, it in enumerate(STATE["items"]):
        if it["name"] == name:
            STATE["items"][i] = item.dict()
            persist("items", STATE["items"])
            return STATE["items"]
    return {"error": "not found"}

@app.delete("/api/items/{name}")
def delete_item(name: str):
    STATE["items"] = [i for i in STATE["items"] if i["name"] != name]
    persist("items", STATE["items"])
    return STATE["items"]

def build_cart(quantities: Dict[str, int]):
    items_by_name = {i["name"]: i for i in STATE["items"]}
    cart = []
    for name, qty in quantities.items():
        if qty and qty > 0 and name in items_by_name:
            cart.append((items_by_name[name], qty))
    return cart

@app.post("/api/calculate")
def calculate(body: CalcIn):
    s = STATE["settings"]
    cart_items = build_cart(body.quantities)
    if not cart_items:
        return {"error": "No items selected."}

    total_weight = sum(it["weight"] * q for it, q in cart_items)
    total_prod = sum(it["prod"] * q for it, q in cart_items)
    total_revenue = sum(get_price(it, body.price_mode) * q for it, q in cart_items)
    shipping_cost = get_shipping_cost(total_weight, s["pkr_per_usd"])
    is_batch = total_weight > 2.0

    if is_batch:
        duty = sum(s["duty_rate"] * s["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
        declared_value = sum(s["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
        mode_label = "BATCH"
    else:
        duty = sum(s["duty_rate"] * get_price(it, body.price_mode) * q for it, q in cart_items)
        declared_value = sum(get_price(it, body.price_mode) * q for it, q in cart_items)
        mode_label = "INDIVIDUAL"

    insurance_cost = declared_value * s["insurance_rate"] if body.insurance_enabled else 0.0
    landed_cost = total_prod + duty + shipping_cost + insurance_cost
    gross_margin = total_revenue - landed_cost
    your_share = gross_margin * s["split"] * (1 - s["remit_loss"])
    your_share_after_tax = your_share * (1 - s["tax_rate"]) if your_share > 0 else your_share

    return {
        "mode_label": mode_label,
        "total_weight": total_weight,
        "total_revenue": total_revenue,
        "total_prod": total_prod,
        "duty": duty,
        "shipping_cost": shipping_cost,
        "insurance_cost": insurance_cost,
        "landed_cost": landed_cost,
        "gross_margin": gross_margin,
        "your_share_after_tax": your_share_after_tax,
        "is_profit": your_share_after_tax >= 0,
        "cart": [{"name": it["name"], "qty": q, "price": get_price(it, body.price_mode), "prod": it["prod"]} for it, q in cart_items],
    }

@app.post("/api/best_split")
def best_split(body: CalcIn):
    s = STATE["settings"]
    cart_items = build_cart(body.quantities)
    if not cart_items:
        return {"error": "No items selected."}
    shipments, best_cost = find_best_shipping_plan(cart_items, s, body.price_mode)
    duty, shipping, _, _ = compute_shipment_cost(cart_items, s, body.price_mode)
    one_shipment_cost = duty + shipping
    return {
        "shipments": shipments,
        "best_cost": best_cost,
        "one_shipment_cost": one_shipment_cost,
        "savings": one_shipment_cost - best_cost,
    }

# ---------------------------------------------------------------
# Frontend (single page)
# ---------------------------------------------------------------
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Export Clothing Calculator</title>
<style>
  :root{--bg:#0f1420;--card:#1a2236;--input:#232c42;--accent:#c9a24b;--text:#eef1f7;--dim:#8b93a8;--good:#3ecf8e;--bad:#e35d6a;--purple:#8e6fce;--border:#2a3450;}
  body{background:var(--bg);color:var(--text);font-family:Segoe UI,Arial,sans-serif;margin:0;padding:20px;}
  h1{color:var(--accent);font-size:22px;}
  h3{margin-top:0;}
  .row{display:flex;gap:16px;flex-wrap:wrap;}
  .card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;flex:1;min-width:300px;}
  button{background:var(--accent);color:#111318;border:none;border-radius:6px;padding:8px 14px;font-weight:bold;cursor:pointer;margin:2px;}
  button.alt{background:var(--input);color:var(--text);}
  button.purple{background:var(--purple);color:#fff;}
  button.good{background:var(--good);color:#0a1f14;}
  button.bad{background:var(--bad);color:#2a0a0d;}
  input,select{background:var(--input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:4px 6px;margin:2px;}
  .item{display:flex;align-items:center;justify-content:space-between;background:var(--input);border-radius:6px;padding:8px;margin:4px 0;flex-wrap:wrap;gap:6px;}
  .qty{display:flex;align-items:center;gap:6px;}
  pre{white-space:pre-wrap;font-family:Consolas,monospace;font-size:13px;}
  .profit{color:var(--good);font-weight:bold;}
  .loss{color:var(--bad);font-weight:bold;}
  .dim{color:var(--dim);}
  #configPanel{display:none;}
  .settingsGrid{display:grid;grid-template-columns:1fr 120px;gap:6px;align-items:center;max-width:400px;}
  .itemForm{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:10px;}
  .itemForm input{width:110px;}
</style>
</head>
<body>
<h1>⚜ Clothing Export Business — Calculator</h1>
<div>
  <button class="purple" onclick="toggleCurrency()">💱 Currency: <span id="curLabel">USD</span></button>
  <button class="good" onclick="togglePriceMode()">🏷 Price mode: <span id="modeLabel">Retail</span></button>
  <button class="alt" onclick="toggleConfig()">⚙ Config</button>
  <label style="margin-left:12px;"><input type="checkbox" id="insurance" onchange="calculate()"> Include TCS Insurance</label>
</div>

<div class="card" id="configPanel" style="margin-top:14px;">
  <h3>⚙ Configuration</h3>
  <b>Add / Edit Item</b> (prices entered in <span id="curLabel2">USD</span>)
  <div class="itemForm">
    <input id="f_name" placeholder="Name">
    <select id="f_season"><option>Winter</option><option>All-Year</option><option>Summer</option></select>
    <input id="f_retail" placeholder="Retail" type="number" step="0.01">
    <input id="f_distributor" placeholder="Distributor" type="number" step="0.01">
    <input id="f_prod" placeholder="Prod cost" type="number" step="0.01">
    <input id="f_weight" placeholder="Weight kg" type="number" step="0.01">
    <button onclick="saveItemForm()">💾 Save Item</button>
    <button class="alt" onclick="clearItemForm()">Clear</button>
  </div>
  <div id="itemAdminList"></div>

  <hr style="border-color:var(--border);margin:16px 0;">
  <b>Settings</b> (always in USD / decimal, regardless of display currency)
  <div class="settingsGrid" id="settingsGrid"></div>
  <button onclick="saveSettings()" style="margin-top:8px;">💾 Save Settings</button>
</div>

<div class="row" style="margin-top:14px;">
  <div class="card" id="itemsCard"><h3>Items</h3><div id="itemsList"></div></div>
  <div class="card"><h3>Order Summary</h3><pre id="resultBox">Select quantities and press Calculate.</pre></div>
</div>
<div style="margin-top:10px;">
  <button onclick="calculate()">▶ Calculate</button>
  <button class="purple" onclick="bestSplit()">📦 Best Split</button>
</div>
<div class="card" style="margin-top:14px;"><h3>📦 Order Split Analysis</h3><pre id="splitBox" class="dim">Calculate first, then Best Split.</pre></div>

<script>
let STATE = null;
let currency = "USD";
let priceMode = "retail";
let quantities = {};
const SETTINGS_LABELS = {
  duty_rate: "Customs duty rate (0-1)",
  transfer_multiplier: "Transfer value multiplier",
  tax_rate: "Export tax rate (0-1)",
  split: "Your split of margin (0-1)",
  remit_loss: "Remittance/FX loss (0-1)",
  pkr_per_usd: "PKR per USD rate",
  insurance_rate: "TCS insurance rate (0-1)",
};

async function loadState() {
  const r = await fetch('/api/state');
  STATE = await r.json();
  renderItems();
  renderConfig();
}

function fmt(usdVal) {
  const val = currency === "PKR" ? usdVal * STATE.settings.pkr_per_usd : usdVal;
  return currency === "PKR" ? "Rs " + val.toLocaleString(undefined,{maximumFractionDigits:0})
                             : "$" + val.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
}

function toggleCurrency() {
  currency = currency === "USD" ? "PKR" : "USD";
  document.getElementById('curLabel').innerText = currency;
  document.getElementById('curLabel2').innerText = currency;
  renderItems();
}
function togglePriceMode() {
  priceMode = priceMode === "retail" ? "distributor" : "retail";
  document.getElementById('modeLabel').innerText = priceMode === "retail" ? "Retail" : "Distributor";
  renderItems();
}
function toggleConfig() {
  const p = document.getElementById('configPanel');
  p.style.display = p.style.display === "none" || !p.style.display ? "block" : "none";
}

function renderItems() {
  const seasons = ["Winter","All-Year","Summer"];
  const div = document.getElementById('itemsList');
  div.innerHTML = "";
  seasons.forEach(season => {
    const items = STATE.items.filter(i => i.season === season);
    if (!items.length) return;
    const h = document.createElement('div');
    h.innerHTML = "<b style='color:var(--accent)'>" + season + "</b>";
    div.appendChild(h);
    items.forEach(it => {
      const price = priceMode === "retail" ? it.retail : it.distributor;
      const qty = quantities[it.name] || 0;
      const row = document.createElement('div');
      row.className = "item";
      row.innerHTML = `
        <span>${it.name}</span>
        <span class="dim">${fmt(it.prod)}</span>
        <span style="color:var(--accent);font-weight:bold;">${fmt(price)}</span>
        <span class="qty">
          <button class="alt" onclick="changeQty('${it.name}',-1)">−</button>
          <span id="q_${it.name}">${qty}</span>
          <button onclick="changeQty('${it.name}',1)">+</button>
        </span>`;
      div.appendChild(row);
    });
  });
}

function changeQty(name, delta) {
  quantities[name] = Math.max(0, (quantities[name] || 0) + delta);
  document.getElementById('q_' + name).innerText = quantities[name];
}

// ---------- CONFIG PANEL ----------
function renderConfig() {
  const grid = document.getElementById('settingsGrid');
  grid.innerHTML = "";
  Object.keys(SETTINGS_LABELS).forEach(key => {
    const label = document.createElement('div');
    label.innerText = SETTINGS_LABELS[key];
    const input = document.createElement('input');
    input.type = "number"; input.step = "any"; input.id = "s_" + key;
    input.value = STATE.settings[key];
    grid.appendChild(label);
    grid.appendChild(input);
  });

  const list = document.getElementById('itemAdminList');
  list.innerHTML = "";
  STATE.items.forEach(it => {
    const row = document.createElement('div');
    row.className = "item";
    row.innerHTML = `<span>${it.name} (${it.season})</span>
      <span class="dim">R:${it.retail} D:${it.distributor} P:${it.prod} W:${it.weight}kg</span>
      <span>
        <button class="alt" onclick='editItemForm(${JSON.stringify(it)})'>✎ Edit</button>
        <button class="bad" onclick="deleteItem('${it.name}')">✕ Remove</button>
      </span>`;
    list.appendChild(row);
  });
}

function clearItemForm() {
  document.getElementById('f_name').value = "";
  document.getElementById('f_retail').value = "";
  document.getElementById('f_distributor').value = "";
  document.getElementById('f_prod').value = "";
  document.getElementById('f_weight').value = "";
}
function editItemForm(it) {
  document.getElementById('f_name').value = it.name;
  document.getElementById('f_season').value = it.season;
  document.getElementById('f_retail').value = it.retail;
  document.getElementById('f_distributor').value = it.distributor;
  document.getElementById('f_prod').value = it.prod;
  document.getElementById('f_weight').value = it.weight;
}

async function saveItemForm() {
  const name = document.getElementById('f_name').value.trim();
  if (!name) { alert("Name required"); return; }
  const payload = {
    name,
    season: document.getElementById('f_season').value,
    retail: parseFloat(document.getElementById('f_retail').value) || 0,
    distributor: parseFloat(document.getElementById('f_distributor').value) || 0,
    prod: parseFloat(document.getElementById('f_prod').value) || 0,
    weight: parseFloat(document.getElementById('f_weight').value) || 0,
  };
  const exists = STATE.items.some(i => i.name === name);
  const url = exists ? '/api/items/' + encodeURIComponent(name) : '/api/items';
  const method = exists ? 'PUT' : 'POST';
  const r = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  STATE.items = await r.json();
  clearItemForm();
  renderItems();
  renderConfig();
}

async function deleteItem(name) {
  const r = await fetch('/api/items/' + encodeURIComponent(name), {method:'DELETE'});
  STATE.items = await r.json();
  delete quantities[name];
  renderItems();
  renderConfig();
}

async function saveSettings() {
  const payload = {};
  Object.keys(SETTINGS_LABELS).forEach(key => {
    payload[key] = parseFloat(document.getElementById('s_' + key).value);
  });
  const r = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  STATE.settings = await r.json();
  renderItems();
  alert("Settings saved permanently.");
}

// ---------- CALCULATE / SPLIT ----------
async function calculate() {
  const insurance = document.getElementById('insurance').checked;
  const r = await fetch('/api/calculate', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({quantities, price_mode: priceMode, insurance_enabled: insurance})
  });
  const d = await r.json();
  const box = document.getElementById('resultBox');
  if (d.error) { box.innerText = d.error; return; }
  let out = `Shipping mode: ${d.mode_label} (weight ${d.total_weight.toFixed(2)}kg)\\n`;
  out += `Currency: ${currency} | Price mode: ${priceMode}\\n` + "-".repeat(50) + "\\n";
  d.cart.forEach(c => out += `${c.name} x${c.qty}  price ${fmt(c.price)}  prod ${fmt(c.prod)}\\n`);
  out += "-".repeat(50) + "\\n";
  out += `Total revenue:        ${fmt(d.total_revenue)}\\n`;
  out += `Total production:     ${fmt(d.total_prod)}\\n`;
  out += `Total duty:           ${fmt(d.duty)}\\n`;
  out += `Total shipping:       ${fmt(d.shipping_cost)}\\n`;
  if (d.insurance_cost) out += `Insurance:            ${fmt(d.insurance_cost)}\\n`;
  out += `Landed cost:          ${fmt(d.landed_cost)}\\n`;
  out += `Gross margin:         ${fmt(d.gross_margin)}\\n`;
  out += `Your share (after tax/remit): ${fmt(d.your_share_after_tax)}\\n`;
  out += "-".repeat(50) + "\\n";
  out += d.is_profit ? "RESULT: ✅ PROFIT" : "RESULT: ❌ LOSS";
  box.innerHTML = out;
  box.className = d.is_profit ? "profit" : "loss";
}

async function bestSplit() {
  const r = await fetch('/api/best_split', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({quantities, price_mode: priceMode})
  });
  const d = await r.json();
  const box = document.getElementById('splitBox');
  if (d.error) { box.innerText = d.error; return; }
  const totalQty = d.shipments.reduce((a,b)=>a+b,0);
  let out = "";
  if (d.shipments.length === 1) out += `Ship all ${totalQty} units in ONE shipment.\\n\\n`;
  else out += `Split ${totalQty} units into ${d.shipments.length} shipments:\\n  ${d.shipments.join(' + ')}\\n\\n`;
  out += `One-shipment cost: ${fmt(d.one_shipment_cost)}\\n`;
  out += `Best-split cost:   ${fmt(d.best_cost)}\\n`;
  out += d.savings > 0.01 ? `\\n✅ Saves ${fmt(d.savings)} vs one shipment` : "\\nOne shipment is already optimal.";
  box.innerText = out;
}

loadState();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML