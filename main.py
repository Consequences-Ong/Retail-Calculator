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
# DYNAMIC (quantity-tiered) PRICING — fixed in code on purpose.
# Each tuple: (min_qty, max_qty, price_per_unit_usd). Beyond the
# last tier's max, the last tier's price is used.
# ---------------------------------------------------------------
DYNAMIC_PRICING_USD = {
    "Leather Jacket": [(1,5,134.50),(6,33,129.50),(34,38,127.00),(39,44,126.50),(45,50,125.00),(51,55,124.00)],
    "Shearling Jacket": [(1,1,228.00),(2,3,208.50),(4,22,199.50),(23,29,197.00),(30,33,195.00),(34,37,193.00)],
    "Motorbike/Racing Jacket": [(1,2,207.00),(3,26,166.50),(27,30,163.00),(31,39,162.00),(40,43,160.00)],
    "Wool Overcoat": [(1,2,164.50),(3,27,121.00),(28,31,118.00),(32,36,117.50),(37,45,116.00)],
    "Varsity/Bomber Jacket": [(1,1,102.00),(2,3,97.00),(4,6,87.50),(7,46,81.50),(47,53,80.50),(54,61,80.00)],
    "Denim Jacket": [(1,1,72.50),(2,6,66.50),(7,11,55.50),(12,50,53.50),(51,56,52.50),(57,62,52.00)],
    "Wool/Knit Sweater": [(1,1,72.50),(2,7,66.50),(8,12,52.00),(13,50,50.50),(51,57,50.00),(58,64,49.50)],
    "Fleece Hoodie": [(1,1,65.00),(2,3,52.50),(4,8,50.00),(9,15,42.50),(16,66,40.00)],
    "Leather Vest": [(1,1,99.00),(2,6,93.50),(7,11,82.00),(12,43,80.50),(44,50,80.00),(51,56,79.50),(57,62,79.00)],
    "Denim Jeans": [(1,1,66.50),(2,6,61.00),(7,11,50.00),(12,43,48.00),(44,50,47.50),(51,56,47.00),(57,62,46.50)],
    "Cargo Pants": [(1,1,68.00),(2,7,62.50),(8,12,48.00),(13,50,46.50),(51,64,45.50)],
    "Flannel Shirt": [(1,2,64.00),(3,5,40.50),(6,12,39.00),(13,22,34.50),(23,30,31.00),(31,50,30.50),(51,62,29.00)],
    "Polo Shirt": [(1,4,59.50),(5,9,28.00),(10,22,27.00),(23,40,23.50),(41,54,22.00),(55,63,21.00)],
    "Linen Shirt": [(1,5,68.00),(6,25,34.50),(26,45,31.00),(46,60,29.50)],
    "Shorts": [(1,3,59.50),(4,16,32.00),(17,30,26.50),(31,66,24.00)],
    "T-shirt (regular)": [(1,5,58.00),(6,25,24.50),(26,45,21.50),(46,60,20.00)],
    "T-shirt (oversized)": [(1,3,61.00),(4,7,32.50),(8,17,31.00),(18,32,27.50),(33,42,25.00),(43,71,24.50)],
}

def get_dynamic_price(name, qty):
    tiers = DYNAMIC_PRICING_USD.get(name)
    if not tiers or not qty or qty <= 0:
        return 0.0
    for lo, hi, price in tiers:
        if lo <= qty <= hi:
            return price
    return tiers[-1][2]

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

def get_price(item, mode, qty=None):
    if mode == "dynamic":
        return get_dynamic_price(item["name"], qty)
    return item["retail"] if mode == "retail" else item["distributor"]

def compute_shipment_cost(cart_items, settings, mode):
    total_weight = sum(it["weight"] * q for it, q in cart_items)
    shipping_usd = get_shipping_cost(total_weight, settings["pkr_per_usd"])
    is_batch = total_weight > 2.0
    if is_batch:
        duty_usd = sum(settings["duty_rate"] * settings["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
    else:
        duty_usd = sum(settings["duty_rate"] * get_price(it, mode, q) * q for it, q in cart_items)
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

class ItemEditIn(BaseModel):
    original_name: str
    name: str
    season: str = "All-Year"
    retail: float
    distributor: float
    prod: float
    weight: float

class ItemDeleteIn(BaseModel):
    name: str

class CalcIn(BaseModel):
    quantities: Dict[str, int]
    price_mode: str = "retail"
    insurance_enabled: bool = False

# ---------------------------------------------------------------
# API routes
# ---------------------------------------------------------------
@app.api_route("/healthz", methods=["GET", "HEAD"])
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

@app.put("/api/items")
def edit_item(item: ItemEditIn):
    for i, it in enumerate(STATE["items"]):
        if it["name"] == item.original_name:
            STATE["items"][i] = item.dict(exclude={"original_name"})
            persist("items", STATE["items"])
            return STATE["items"]
    return {"error": "not found"}

@app.delete("/api/items")
def delete_item(body: ItemDeleteIn):
    STATE["items"] = [i for i in STATE["items"] if i["name"] != body.name]
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
    total_revenue = sum(get_price(it, body.price_mode, q) * q for it, q in cart_items)
    shipping_cost = get_shipping_cost(total_weight, s["pkr_per_usd"])
    is_batch = total_weight > 2.0

    if is_batch:
        duty = sum(s["duty_rate"] * s["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
        declared_value = sum(s["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
        mode_label = "BATCH"
    else:
        duty = sum(s["duty_rate"] * get_price(it, body.price_mode, q) * q for it, q in cart_items)
        declared_value = sum(get_price(it, body.price_mode, q) * q for it, q in cart_items)
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
        "cart": [{"name": it["name"], "qty": q, "price": get_price(it, body.price_mode, q), "prod": it["prod"]} for it, q in cart_items],
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
# SHARED CSS (mirrors the Tkinter COLORS/FONT palette exactly)
# ---------------------------------------------------------------
BASE_CSS = """
:root{
  --bg:#0f1420; --card:#1a2236; --input:#232c42; --accent:#c9a24b; --accent-hover:#e0ba63;
  --text:#eef1f7; --dim:#8b93a8; --success:#3ecf8e; --danger:#e35d6a; --purple:#8e6fce; --border:#2a3450;
}
*{box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:"Segoe UI",Arial,sans-serif;margin:0;min-height:100vh;}
.topbar{display:flex;align-items:center;padding:18px 20px 10px 20px;gap:18px;}
.topbar h1{font-size:20px;margin:0;font-weight:700;}
.topbar .right{margin-left:auto;display:flex;gap:10px;}
button{border:none;border-radius:6px;font-weight:700;cursor:pointer;font-family:inherit;padding:10px 18px;font-size:14px;}
button.accent{background:var(--accent);color:#111318;}
button.accent:hover{background:var(--accent-hover);}
button.alt{background:var(--input);color:var(--text);}
button.purple{background:var(--purple);color:#fff;}
button.success{background:var(--success);color:#0a1f14;}
button.danger{background:var(--danger);color:#2a0a0d;}
button.small{padding:6px 12px;font-size:13px;}
button.icon-btn{width:34px;height:34px;padding:0;font-size:16px;border-radius:6px;}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin:0 20px 20px 20px;padding:16px;}
.card h3{color:var(--accent);margin:0 0 12px 0;font-size:14px;font-weight:700;}
.home-wrap{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:90vh;text-align:center;}
.home-wrap .glyph{font-size:34px;color:var(--accent);margin-bottom:10px;}
.home-wrap h1{font-size:26px;margin:4px 0;}
.home-wrap .sub{color:var(--dim);margin-bottom:36px;}
.home-btn{width:280px;padding:18px;font-size:15px;margin:8px 0;border-radius:8px;}
.home-btn.cfg{background:var(--card);color:var(--text);border:1px solid var(--accent);}
.home-btn.calc{background:var(--accent);color:#111318;}
table{width:100%;border-collapse:collapse;}
th{color:var(--accent);text-align:center;font-size:13px;padding:10px 8px;background:var(--input);}
td{text-align:center;font-size:13px;padding:8px;border-bottom:1px solid var(--border);cursor:pointer;}
tr.selected td{background:var(--accent);color:#111318;}
tr:nth-child(even) td{background:rgba(255,255,255,0.02);}
tr.selected:nth-child(even) td{background:var(--accent);}
.tbl-scroll{max-height:320px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;}
.btn-row{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;}
.settings-grid{display:grid;grid-template-columns:1fr 140px;gap:10px;max-width:520px;align-items:center;}
.settings-grid label{color:var(--dim);font-size:13px;}
.settings-grid input{background:var(--input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:8px;font-family:inherit;}
.note{color:var(--dim);font-size:12px;font-style:italic;margin-top:10px;}
.mode-banner{text-align:center;font-weight:700;padding:6px 0 12px 0;}
.main-row{display:flex;gap:16px;margin:0 20px 16px 20px;height:320px;}
.cart-card{flex:1;background:var(--card);border:1px solid var(--border);border-radius:8px;overflow-y:auto;padding:10px;}
.result-card{flex:1;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;overflow-y:auto;}
.season-header{display:flex;justify-content:space-between;align-items:center;color:var(--accent);font-weight:700;font-size:13px;margin:12px 0 6px 4px;}
.season-header .cols{display:flex;gap:0;}
.season-header .cols span{width:100px;text-align:right;padding-right:10px;color:var(--dim);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;}
.item-row{display:flex;align-items:center;background:var(--input);border-radius:6px;padding:8px 10px;margin:4px 0;}
.item-row .name{flex:2;font-size:13px;}
.item-row .design{flex:1;color:var(--dim);font-size:13px;}
.item-row .sell{flex:1;color:var(--accent);font-weight:700;font-size:13px;}
.item-row .qtybox{display:flex;align-items:center;gap:8px;}
.item-row .qtybox span{min-width:18px;text-align:center;color:var(--accent);font-weight:700;}
.center-btns{display:flex;justify-content:center;gap:10px;margin:12px 20px;}
.insurance-row{text-align:center;margin-bottom:10px;font-size:13px;color:var(--text);}
pre.output{white-space:pre-wrap;font-family:Consolas,monospace;font-size:12.5px;margin:0;}
.profit{color:var(--success);font-weight:700;}
.loss{color:var(--danger);font-weight:700;}
.dim{color:var(--dim);}
.lbl{color:var(--dim);}
.hl{color:var(--text);font-weight:700;}
.money{color:var(--accent);font-weight:700;}
.money-dim{color:var(--dim);}
.accent-text{color:var(--accent);}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);align-items:center;justify-content:center;z-index:50;}
.modal-overlay.open{display:flex;}
.modal{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:22px;width:320px;}
.modal h3{margin-top:0;color:var(--text);}
.modal .note{margin-bottom:12px;}
.modal label{display:block;font-size:13px;color:var(--text);margin:10px 0 4px 0;}
.modal input,.modal select{width:100%;background:var(--input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:8px;font-family:inherit;}
.modal .actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;}
"""

NAV_JS = """
function getCurrency(){ return localStorage.getItem('rc_currency') || 'USD'; }
function setCurrency(v){ localStorage.setItem('rc_currency', v); }
function getPriceMode(){ return localStorage.getItem('rc_price_mode') || 'retail'; }
function setPriceMode(v){ localStorage.setItem('rc_price_mode', v); }
function goHome(){ window.location.href = '/'; }
"""

def page_shell(title, body, extra_script=""):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{BASE_CSS}</style></head>
<body>{body}
<script>{NAV_JS}
{extra_script}
</script>
</body></html>"""

# ---------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    body = """
    <div class="home-wrap">
      <div class="glyph">⚜</div>
      <h1>Clothing Export Business</h1>
      <div class="sub">Pakistan &rarr; USA margin &amp; shipping calculator</div>
      <button class="home-btn cfg" onclick="window.location.href='/config'">⚙&nbsp;&nbsp;Configuration</button>
      <button class="home-btn calc" onclick="window.location.href='/calculator'">🧮&nbsp;&nbsp;Calculator</button>
    </div>
    """
    return page_shell("Export Clothing Business Calculator", body)

# ---------------------------------------------------------------
# CONFIG PAGE
# ---------------------------------------------------------------
@app.get("/config", response_class=HTMLResponse)
def config_page():
    body = """
    <div class="topbar">
      <button class="alt small" onclick="goHome()">&larr; Home</button>
      <h1>Configuration</h1>
      <div class="right">
        <button class="purple" id="curBtn" onclick="toggleCurrency()">&#128176; <span id="curLabel">USD</span></button>
      </div>
    </div>

    <div class="card">
      <h3>Item Catalog</h3>
      <div class="tbl-scroll">
        <table>
          <thead><tr>
            <th>Name</th><th>Season</th>
            <th id="thRetail">Retail($)</th><th id="thDistrib">Distrib($)</th><th id="thProd">Prod($)</th>
            <th>Weight(kg)</th>
          </tr></thead>
          <tbody id="itemRows"></tbody>
        </table>
      </div>
      <div class="btn-row">
        <button class="success" onclick="openAddModal()">+ Add Item</button>
        <button class="alt" onclick="openEditModal()">&#9998; Edit Selected</button>
        <button class="danger" onclick="removeSelected()">&#10005; Remove Selected</button>
      </div>
    </div>

    <div class="card">
      <h3>Shipping / Remittance / Duty / Tax Settings</h3>
      <div class="settings-grid" id="settingsGrid"></div>
      <div class="note">Shipping/duty/tax settings always entered in USD/decimal, regardless of display currency above.</div>
      <div style="margin-top:14px;"><button class="accent" onclick="saveSettings()">&#128190; Save Settings</button></div>
    </div>

    <div class="modal-overlay" id="modalOverlay">
      <div class="modal">
        <h3 id="modalTitle">Add Item</h3>
        <div class="note" id="modalNote"></div>
        <label>Name</label><input id="f_name">
        <label>Season</label>
        <select id="f_season"><option>Winter</option><option>All-Year</option><option>Summer</option></select>
        <label>Retail price (consumer)</label><input id="f_retail" type="number" step="0.01">
        <label>Distributor price (B2B)</label><input id="f_distributor" type="number" step="0.01">
        <label>Production cost</label><input id="f_prod" type="number" step="0.01">
        <label>Weight (kg)</label><input id="f_weight" type="number" step="0.01">
        <div class="actions">
          <button class="alt" onclick="closeModal()">Cancel</button>
          <button class="accent" onclick="saveItemModal()">Save</button>
        </div>
      </div>
    </div>
    """
    script = """
let STATE = null;
let editingName = null;
let selectedName = null;
const SETTINGS_LABELS = {
  duty_rate: "Customs duty rate (0-1)",
  transfer_multiplier: "Transfer value multiplier (batch duty basis)",
  tax_rate: "Export tax rate on your share (0-1)",
  split: "Your split of gross margin (0-1)",
  remit_loss: "Remittance/FX loss (0-1)",
  pkr_per_usd: "PKR per USD rate",
  insurance_rate: "TCS insurance rate (0-1, official range 0.005-0.02)",
};

function sym(){ return getCurrency() === "PKR" ? "Rs" : "$"; }
function conv(usd){ return getCurrency() === "PKR" ? usd * STATE.settings.pkr_per_usd : usd; }
function fmtNum(usd){
  const v = conv(usd);
  return getCurrency() === "PKR" ? v.toLocaleString(undefined,{maximumFractionDigits:0}) : v.toFixed(2);
}

async function loadState(){
  const r = await fetch('/api/state');
  STATE = await r.json();
  document.getElementById('curLabel').innerText = getCurrency();
  renderTable();
  renderSettings();
}

function toggleCurrency(){
  setCurrency(getCurrency() === "USD" ? "PKR" : "USD");
  document.getElementById('curLabel').innerText = getCurrency();
  renderTable();
}

function renderTable(){
  const s = sym();
  document.getElementById('thRetail').innerText = `Retail(${s})`;
  document.getElementById('thDistrib').innerText = `Distrib(${s})`;
  document.getElementById('thProd').innerText = `Prod(${s})`;
  const tbody = document.getElementById('itemRows');
  tbody.innerHTML = "";
  STATE.items.forEach(it => {
    const tr = document.createElement('tr');
    if (it.name === selectedName) tr.className = 'selected';
    tr.onclick = () => { selectedName = it.name; renderTable(); };
    tr.innerHTML = `<td>${it.name}</td><td>${it.season}</td>
      <td>${fmtNum(it.retail)}</td><td>${fmtNum(it.distributor)}</td>
      <td>${fmtNum(it.prod)}</td><td>${it.weight}</td>`;
    tbody.appendChild(tr);
  });
}

function renderSettings(){
  const grid = document.getElementById('settingsGrid');
  grid.innerHTML = "";
  Object.keys(SETTINGS_LABELS).forEach(key => {
    const label = document.createElement('label');
    label.innerText = SETTINGS_LABELS[key];
    const input = document.createElement('input');
    input.type = "number"; input.step = "any"; input.id = "s_" + key;
    input.value = STATE.settings[key];
    grid.appendChild(label);
    grid.appendChild(input);
  });
}

async function saveSettings(){
  const payload = {};
  Object.keys(SETTINGS_LABELS).forEach(key => {
    payload[key] = parseFloat(document.getElementById('s_' + key).value);
  });
  const r = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  STATE.settings = await r.json();
  renderTable();
  alert("Settings updated.");
}

function openAddModal(){
  editingName = null;
  document.getElementById('modalTitle').innerText = "Add Item";
  document.getElementById('modalNote').innerText = `Enter Retail/Distributor/Production price in ${getCurrency()}. Stored internally as USD.`;
  ['f_name','f_retail','f_distributor','f_prod','f_weight'].forEach(id => document.getElementById(id).value = "");
  document.getElementById('f_season').value = "Winter";
  document.getElementById('modalOverlay').classList.add('open');
}

function openEditModal(){
  if (!selectedName){ alert("Select an item to edit first"); return; }
  const it = STATE.items.find(i => i.name === selectedName);
  if (!it) return;
  editingName = it.name;
  document.getElementById('modalTitle').innerText = "Edit Item";
  document.getElementById('modalNote').innerText = `Enter Retail/Distributor/Production price in ${getCurrency()}. Stored internally as USD.`;
  document.getElementById('f_name').value = it.name;
  document.getElementById('f_season').value = it.season;
  document.getElementById('f_retail').value = conv(it.retail).toFixed(2);
  document.getElementById('f_distributor').value = conv(it.distributor).toFixed(2);
  document.getElementById('f_prod').value = conv(it.prod).toFixed(2);
  document.getElementById('f_weight').value = it.weight;
  document.getElementById('modalOverlay').classList.add('open');
}

function closeModal(){ document.getElementById('modalOverlay').classList.remove('open'); }

async function saveItemModal(){
  const name = document.getElementById('f_name').value.trim();
  if (!name){ alert("Name required"); return; }
  let retail = parseFloat(document.getElementById('f_retail').value);
  let distributor = parseFloat(document.getElementById('f_distributor').value);
  let prod = parseFloat(document.getElementById('f_prod').value);
  const weight = parseFloat(document.getElementById('f_weight').value);
  if ([retail,distributor,prod,weight].some(isNaN)){ alert("Retail/Distributor/Prod/Weight must be numbers"); return; }
  if (getCurrency() === "PKR"){
    retail = retail / STATE.settings.pkr_per_usd;
    distributor = distributor / STATE.settings.pkr_per_usd;
    prod = prod / STATE.settings.pkr_per_usd;
  }
  const method = editingName ? 'PUT' : 'POST';
  const payload = editingName
    ? { original_name: editingName, name, season: document.getElementById('f_season').value, retail, distributor, prod, weight }
    : { name, season: document.getElementById('f_season').value, retail, distributor, prod, weight };
  const r = await fetch('/api/items', {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  STATE.items = await r.json();
  selectedName = name;
  closeModal();
  renderTable();
}

async function removeSelected(){
  if (!selectedName){ alert("Select an item to remove first"); return; }
  const r = await fetch('/api/items', {method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name: selectedName})});
  STATE.items = await r.json();
  selectedName = null;
  renderTable();
}

loadState();
"""
    return page_shell("Configuration", body, script)

# ---------------------------------------------------------------
# CALCULATOR PAGE
# ---------------------------------------------------------------
@app.get("/calculator", response_class=HTMLResponse)
def calculator_page():
    body = """
    <div class="topbar">
      <button class="alt small" onclick="goHome()">&larr; Home</button>
      <h1>Order Calculator</h1>
      <div class="right">
        <button class="success" id="modeBtn" onclick="togglePriceMode()"></button>
        <button class="purple" id="curBtn" onclick="toggleCurrency()"></button>
      </div>
    </div>
    <div class="mode-banner" id="modeBanner"></div>

    <div class="main-row">
      <div class="cart-card" id="cartCard"></div>
      <div class="result-card">
        <h3>&#128176; Order Summary</h3>
        <pre class="output" id="resultBox">Select quantities and press Calculate.</pre>
      </div>
    </div>

    <div class="center-btns">
      <button class="success" onclick="calculate()">&#9654; Calculate</button>
      <button class="purple" onclick="bestSplit()">&#128230; Best Split</button>
    </div>
    <div class="insurance-row">
      <label><input type="checkbox" id="insurance" onchange="calculate()"> Include TCS Insurance (0.5%-2% of declared value, official TCS range)</label>
    </div>

    <div class="card">
      <h3>&#128230; Order Split Analysis</h3>
      <pre class="output dim" id="splitBox">Click Calculate, then Best Split, to see the optimal way to break this order into shipments.</pre>
    </div>
    """
    script = """
let STATE = null;
let quantities = {};
let lastCartQuantities = null;

const DYNAMIC_PRICING = {
  "Leather Jacket": [[1,5,134.50],[6,33,129.50],[34,38,127.00],[39,44,126.50],[45,50,125.00],[51,55,124.00]],
  "Shearling Jacket": [[1,1,228.00],[2,3,208.50],[4,22,199.50],[23,29,197.00],[30,33,195.00],[34,37,193.00]],
  "Motorbike/Racing Jacket": [[1,2,207.00],[3,26,166.50],[27,30,163.00],[31,39,162.00],[40,43,160.00]],
  "Wool Overcoat": [[1,2,164.50],[3,27,121.00],[28,31,118.00],[32,36,117.50],[37,45,116.00]],
  "Varsity/Bomber Jacket": [[1,1,102.00],[2,3,97.00],[4,6,87.50],[7,46,81.50],[47,53,80.50],[54,61,80.00]],
  "Denim Jacket": [[1,1,72.50],[2,6,66.50],[7,11,55.50],[12,50,53.50],[51,56,52.50],[57,62,52.00]],
  "Wool/Knit Sweater": [[1,1,72.50],[2,7,66.50],[8,12,52.00],[13,50,50.50],[51,57,50.00],[58,64,49.50]],
  "Fleece Hoodie": [[1,1,65.00],[2,3,52.50],[4,8,50.00],[9,15,42.50],[16,66,40.00]],
  "Leather Vest": [[1,1,99.00],[2,6,93.50],[7,11,82.00],[12,43,80.50],[44,50,80.00],[51,56,79.50],[57,62,79.00]],
  "Denim Jeans": [[1,1,66.50],[2,6,61.00],[7,11,50.00],[12,43,48.00],[44,50,47.50],[51,56,47.00],[57,62,46.50]],
  "Cargo Pants": [[1,1,68.00],[2,7,62.50],[8,12,48.00],[13,50,46.50],[51,64,45.50]],
  "Flannel Shirt": [[1,2,64.00],[3,5,40.50],[6,12,39.00],[13,22,34.50],[23,30,31.00],[31,50,30.50],[51,62,29.00]],
  "Polo Shirt": [[1,4,59.50],[5,9,28.00],[10,22,27.00],[23,40,23.50],[41,54,22.00],[55,63,21.00]],
  "Linen Shirt": [[1,5,68.00],[6,25,34.50],[26,45,31.00],[46,60,29.50]],
  "Shorts": [[1,3,59.50],[4,16,32.00],[17,30,26.50],[31,66,24.00]],
  "T-shirt (regular)": [[1,5,58.00],[6,25,24.50],[26,45,21.50],[46,60,20.00]],
  "T-shirt (oversized)": [[1,3,61.00],[4,7,32.50],[8,17,31.00],[18,32,27.50],[33,42,25.00],[43,71,24.50]],
};

function getDynamicPriceUSD(name, qty){
  const tiers = DYNAMIC_PRICING[name];
  if (!tiers || !qty || qty <= 0) return null;
  for (const [lo,hi,price] of tiers){
    if (qty >= lo && qty <= hi) return price;
  }
  return tiers[tiers.length-1][2];
}

function getSellDisplay(it, qty){
  if (getPriceMode() === "dynamic"){
    const p = getDynamicPriceUSD(it.name, qty);
    return p === null ? "-" : fmt(p);
  }
  return fmt(getPrice(it));
}

function sym(){ return getCurrency() === "PKR" ? "Rs" : "$"; }
function conv(usd){ return getCurrency() === "PKR" ? usd * STATE.settings.pkr_per_usd : usd; }
function fmt(usd){
  const v = conv(usd);
  return getCurrency() === "PKR" ? "Rs " + v.toLocaleString(undefined,{maximumFractionDigits:0})
                                  : "$" + v.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
}
function getPrice(it){ return getPriceMode() === "retail" ? it.retail : it.distributor; }

function refreshTopButtons(){
  document.getElementById('curBtn').innerHTML = `&#128176; ${getCurrency() === "USD" ? "USD &rarr; PKR" : "PKR &rarr; USD"}`;
  const pm = getPriceMode();
  const banner = document.getElementById('modeBanner');
  if (pm === "retail"){
    document.getElementById('modeBtn').innerHTML = `&#127991; Retail mode &rarr; Distributor`;
    banner.innerHTML = "&#128717; RETAIL PRICING (consumer)";
    banner.style.color = "var(--accent)";
  } else if (pm === "distributor"){
    document.getElementById('modeBtn').innerHTML = `&#127991; Distributor mode &rarr; Dynamic`;
    banner.innerHTML = "&#128230; DISTRIBUTOR PRICING (B2B/wholesale)";
    banner.style.color = "var(--success)";
  } else {
    document.getElementById('modeBtn').innerHTML = `&#127991; Dynamic mode &rarr; Retail`;
    banner.innerHTML = "&#128200; DYNAMIC PRICING (qty-tiered)";
    banner.style.color = "var(--purple)";
  }
}

function toggleCurrency(){
  setCurrency(getCurrency() === "USD" ? "PKR" : "USD");
  refreshTopButtons();
  renderCart();
}
function togglePriceMode(){
  const order = ["retail","distributor","dynamic"];
  const idx = order.indexOf(getPriceMode());
  setPriceMode(order[(idx + 1) % order.length]);
  refreshTopButtons();
  renderCart();
}

async function loadState(){
  const r = await fetch('/api/state');
  STATE = await r.json();
  STATE.items.forEach(it => { if (!(it.name in quantities)) quantities[it.name] = 0; });
  refreshTopButtons();
  renderCart();
}

function renderCart(){
  const card = document.getElementById('cartCard');
  card.innerHTML = "";
  const sellLabel = getPriceMode() === "dynamic" ? "Price/Unit" : "Selling Price";
  const seasons = [["Winter","&#10052;"], ["All-Year","&#127772;"], ["Summer","&#9728;"]];
  seasons.forEach(([season, icon]) => {
    const items = STATE.items.filter(i => i.season === season);
    if (!items.length) return;
    const h = document.createElement('div');
    h.className = 'season-header';
    h.innerHTML = `<span>${icon} ${season}</span><span class="cols"><span>Design Cost</span><span>${sellLabel}</span></span>`;
    card.appendChild(h);
    items.forEach(it => {
      const row = document.createElement('div');
      row.className = 'item-row';
      const qty = quantities[it.name] || 0;
      row.innerHTML = `
        <span class="name">${it.name}</span>
        <span class="design">${fmt(it.prod)}</span>
        <span class="sell" id="sell_${it.name}">${getSellDisplay(it, qty)}</span>
        <span class="qtybox">
          <button class="alt icon-btn" onclick="changeQty('${it.name}',-1)">&minus;</button>
          <span id="q_${it.name}">${qty}</span>
          <button class="accent icon-btn" onclick="changeQty('${it.name}',1)">+</button>
        </span>`;
      card.appendChild(row);
    });
  });
}

function changeQty(name, delta){
  quantities[name] = Math.max(0, (quantities[name] || 0) + delta);
  document.getElementById('q_' + name).innerText = quantities[name];
  const it = STATE.items.find(i => i.name === name);
  document.getElementById('sell_' + name).innerText = getSellDisplay(it, quantities[name]);
}

async function calculate(){
  const insurance = document.getElementById('insurance').checked;
  const r = await fetch('/api/calculate', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({quantities, price_mode: getPriceMode(), insurance_enabled: insurance})
  });
  const d = await r.json();
  const box = document.getElementById('resultBox');
  if (d.error){ box.innerText = d.error; lastCartQuantities = null; return; }
  lastCartQuantities = JSON.parse(JSON.stringify(quantities));
  const pm = getPriceMode();
  const priceLabel = pm === "retail" ? "Retail" : pm === "distributor" ? "Distrib." : "Dyn/unit";
  let out = `<span class="lbl">Shipping mode:</span> <span class="hl">${d.mode_label}</span>  <span class="lbl">(total weight ${d.total_weight.toFixed(2)}kg)</span>\\n`;
  out += `<span class="lbl">Display currency: ${getCurrency()}   |   Price mode: ${pm}</span>\\n`;
  out += "-".repeat(50) + "\\n";
  out += `<span class="lbl">${"Item".padEnd(20)}${"Qty".padStart(5)}${priceLabel.padStart(12)}${"Prod".padStart(12)}</span>\\n`;
  d.cart.forEach(c => {
    out += `${c.name.padEnd(20)}<span class="hl">${String(c.qty).padStart(5)}</span><span class="money">${fmt(c.price).padStart(12)}</span><span class="money-dim">${fmt(c.prod).padStart(12)}</span>\\n`;
  });
  out += "-".repeat(50) + "\\n";
  out += `Total revenue:          <span class="money">${fmt(d.total_revenue)}</span>\\n`;
  out += `Total production cost:  <span class="money-dim">${fmt(d.total_prod)}</span>\\n`;
  out += `Total duty:             <span class="money-dim">${fmt(d.duty)}</span>\\n`;
  out += `Total shipping cost:    <span class="money-dim">${fmt(d.shipping_cost)}</span>\\n`;
  if (d.insurance_cost) out += `Insurance cost:         <span class="money-dim">${fmt(d.insurance_cost)}</span>\\n`;
  out += `Landed cost:            <span class="hl">${fmt(d.landed_cost)}</span>\\n`;
  out += `Gross margin:           <span class="${d.gross_margin >= 0 ? 'profit' : 'loss'}">${fmt(d.gross_margin)}</span>\\n`;
  out += `Your share (after remittance loss & export tax): <span class="${d.is_profit ? 'profit' : 'loss'}">${fmt(d.your_share_after_tax)}</span>\\n`;
  out += "-".repeat(50) + "\\n";
  out += `RESULT: <span class="${d.is_profit ? 'profit' : 'loss'}">${d.is_profit ? "PROFIT" : "LOSS"}</span>`;
  box.innerHTML = out;
  box.className = 'output';
}

async function bestSplit(){
  if (!lastCartQuantities){ alert("Click Calculate first, then Best Split."); return; }
  const r = await fetch('/api/best_split', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({quantities: lastCartQuantities, price_mode: getPriceMode()})
  });
  const d = await r.json();
  const box = document.getElementById('splitBox');
  if (d.error){ box.innerText = d.error; return; }
  const totalQty = d.shipments.reduce((a,b)=>a+b,0);
  let out = "";
  if (d.shipments.length === 1) out += `Ship all ${totalQty} units in ONE shipment.\\n\\n`;
  else out += `Split ${totalQty} units into ${d.shipments.length} shipments:\\n  ${d.shipments.join(' + ')}\\n\\n`;
  out += `One-shipment cost (duty+ship): ${fmt(d.one_shipment_cost)}\\n`;
  out += `Best-split cost (duty+ship):   ${fmt(d.best_cost)}\\n`;
  out += d.savings > 0.01 ? `\\nSaves ${fmt(d.savings)} vs one shipment` : "\\nOne shipment is already optimal.";
  box.innerText = out;
  box.className = d.savings > 0.01 ? 'output profit' : 'output dim';
}

loadState();
"""
    return page_shell("Order Calculator", body, script)
