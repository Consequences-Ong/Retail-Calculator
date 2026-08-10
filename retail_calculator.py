import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------
# COLOR PALETTE — premium dark theme
# ---------------------------------------------------------------
COLORS = {
    "bg":          "#0f1420",   # deep navy background
    "bg_card":     "#1a2236",   # slightly lighter card background
    "bg_input":    "#232c42",   # input field background
    "accent":      "#c9a24b",   # muted gold accent
    "accent_hover":"#e0ba63",
    "text":        "#eef1f7",   # near-white text
    "text_dim":    "#8b93a8",   # muted secondary text
    "success":     "#3ecf8e",   # green
    "danger":      "#e35d6a",   # red
    "purple":      "#8e6fce",   # currency toggle
    "border":      "#2a3450",
}

FONT_TITLE   = ("Segoe UI", 22, "bold")
FONT_HEADER  = ("Segoe UI", 15, "bold")
FONT_SUB     = ("Segoe UI", 11, "bold")
FONT_BODY    = ("Segoe UI", 10)
FONT_BODY_B  = ("Segoe UI", 10, "bold")
FONT_MONO    = ("Consolas", 10)

# ---------------------------------------------------------------
# DEFAULT DATA — pre-loaded from our conversation (all in USD)
# ---------------------------------------------------------------
DEFAULT_ITEMS = [
    {"name": "Leather Jacket",          "season": "Winter",   "retail": 240, "distributor": 205, "prod": 75.0,  "weight": 1.8},
    {"name": "Shearling Jacket",        "season": "Winter",   "retail": 300, "distributor": 291, "prod": 150.0, "weight": 2.7},  # THIN MARGIN (6%) even at this price — recommend raising retail
    {"name": "Motorbike/Racing Jacket", "season": "Winter",   "retail": 280, "distributor": 245, "prod": 110.0, "weight": 2.3},  # tight (15% margin) — weight-driven
    {"name": "Wool Overcoat",           "season": "Winter",   "retail": 175, "distributor": 157, "prod": 58.0,  "weight": 2.2},  # tight (15% margin) — weight-driven
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
    "insurance_rate": 0.0125,   # midpoint of TCS's official 0.5%-2% CVI range, adjustable
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
# NOTE: 120/150/200kg were excluded — quoted data was inconsistent with every
# other data point and needs to be re-checked before trusting anything past 100kg.

def get_shipping_cost(total_weight_kg, pkr_per_usd):
    """Returns total shipment cost in USD for a given total weight,
    using the nearest real verified TCS quote at or above that weight
    (step-lookup — matches TCS's actual box/tier billing behavior)."""
    for ceiling_kg, cost_pkr in SHIPPING_TIERS_PKR:
        if total_weight_kg <= ceiling_kg:
            return cost_pkr / pkr_per_usd
    last_kg, last_cost = SHIPPING_TIERS_PKR[-1]
    return total_weight_kg * (last_cost / last_kg) / pkr_per_usd

# ---------------------------------------------------------------
# SHIPMENT SPLIT OPTIMIZER
# ---------------------------------------------------------------
def compute_shipment_cost(cart_items, settings, price_fn):
    """cart_items: list of (item, qty) for ONE shipment. Returns
    (duty_usd, shipping_usd, is_batch, total_weight) — same duty/shipping
    logic as render_result, isolated so it can be re-run per shipment."""
    total_weight = sum(it["weight"] * q for it, q in cart_items)
    shipping_usd = get_shipping_cost(total_weight, settings["pkr_per_usd"])
    is_batch = total_weight > 2.0
    if is_batch:
        duty_usd = sum(settings["duty_rate"] * settings["transfer_multiplier"] * it["prod"] * q
                        for it, q in cart_items)
    else:
        duty_usd = sum(settings["duty_rate"] * price_fn(it) * q for it, q in cart_items)
    return duty_usd, shipping_usd, is_batch, total_weight


def optimal_split_single_item(item, qty, settings, price_fn):
    """Exact DP over every way to partition `qty` units of ONE item into
    any number of shipments. Revenue and production cost don't change with
    how you split, so minimizing duty+shipping is the same as maximizing
    profit. O(qty^2) — instant for any realistic order size."""
    def shipment_cost(j):
        duty, shipping, _, _ = compute_shipment_cost([(item, j)], settings, price_fn)
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


def best_proportional_split(cart_items, settings, price_fn, max_shipments=10):
    """Heuristic for MIXED carts (multiple item types): tries splitting the
    whole order into N shipments (N = 1..max_shipments), each getting a
    proportional share of every item, and keeps whichever N minimizes total
    duty+shipping. Mirrors how you'd actually pack N similar-sized boxes."""
    total_qty = sum(q for _, q in cart_items)
    max_shipments = max(1, min(max_shipments, total_qty))
    best_n, best_cost, best_plan = 1, None, None
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
            duty, shipping, _, _ = compute_shipment_cost(shp, settings, price_fn)
            total_cost += duty + shipping
        if best_cost is None or total_cost < best_cost:
            best_cost, best_n = total_cost, n
            best_plan = [sum(q for _, q in shp) for shp in shipments if shp]
    return best_plan, best_cost


def find_best_shipping_plan(cart_items, settings, price_fn, max_shipments=10):
    """Entry point: exact optimum for a single-item order, proportional
    heuristic for mixed orders."""
    if len(cart_items) == 1:
        item, qty = cart_items[0]
        return optimal_split_single_item(item, qty, settings, price_fn)
    return best_proportional_split(cart_items, settings, price_fn, max_shipments)

# ---------------------------------------------------------------
# UI HELPERS
# ---------------------------------------------------------------
def styled_button(parent, text, command, bg=None, fg=None, font=FONT_BODY_B, pad=(18, 10)):
    bg = bg or COLORS["accent"]
    fg = fg or "#111318"
    btn = tk.Button(
        parent, text=text, command=command, font=font,
        bg=bg, fg=fg, activebackground=COLORS["accent_hover"], activeforeground="#111318",
        relief="flat", bd=0, cursor="hand2",
        padx=pad[0], pady=pad[1], highlightthickness=0,
    )
    return btn

def card(parent, **kwargs):
    f = tk.Frame(parent, bg=COLORS["bg_card"], highlightbackground=COLORS["border"],
                 highlightthickness=1, bd=0)
    return f

# ---------------------------------------------------------------
# APP
# ---------------------------------------------------------------
class ClothingCalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Export Clothing Business Calculator")
        self.geometry("1000x900")
        try:
            self.state("zoomed")  # start maximized (Windows). Falls back silently elsewhere.
        except tk.TclError:
            pass
        self.configure(bg=COLORS["bg"])
        self.items = [dict(i) for i in DEFAULT_ITEMS]
        self.settings = dict(DEFAULT_SETTINGS)
        self.quantities = {i["name"]: 0 for i in self.items}
        self.currency = "USD"
        self.price_mode = tk.StringVar(value="retail")  # "retail" or "distributor" — controls which price is used everywhere
        self.insurance_enabled = tk.BooleanVar(value=False)
        self.last_result_cart = None  # stores (cart_items, mode_is_batch, total_weight) for re-rendering across currency toggles
        self.last_split_result = None  # stores (shipments, best_cost_usd, one_shipment_cost_usd) from Best Split

        self._setup_ttk_style()

        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)

        self.show_home()

    def _setup_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Treeview",
                         background=COLORS["bg_card"],
                         fieldbackground=COLORS["bg_card"],
                         foreground=COLORS["text"],
                         rowheight=30,
                         borderwidth=0,
                         font=FONT_BODY)
        style.map("Treeview",
                  background=[("selected", COLORS["accent"])],
                  foreground=[("selected", "#111318")])
        style.configure("Treeview.Heading",
                         background=COLORS["bg_input"],
                         foreground=COLORS["accent"],
                         font=FONT_SUB,
                         borderwidth=0,
                         relief="flat")
        style.map("Treeview.Heading", background=[("active", COLORS["bg_input"])])

        style.configure("Vertical.TScrollbar",
                         background=COLORS["bg_card"],
                         troughcolor=COLORS["bg"],
                         bordercolor=COLORS["bg"],
                         arrowcolor=COLORS["text_dim"])

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ---------------- CURRENCY HELPERS ----------------
    def toggle_currency(self):
        self.currency = "PKR" if self.currency == "USD" else "USD"
        if self.active_screen == "config":
            self.show_config()
        elif self.active_screen == "calculator":
            self.show_calculator()

    def conv(self, usd_value):
        if self.currency == "PKR":
            return usd_value * self.settings["pkr_per_usd"]
        return usd_value

    def sym(self):
        return "Rs" if self.currency == "PKR" else "$"

    def fmt(self, usd_value):
        val = self.conv(usd_value)
        if self.currency == "PKR":
            return f"Rs {val:,.0f}"
        return f"${val:,.2f}"

    def currency_button(self, parent):
        btn = styled_button(
            parent, f"💱  {self.currency} → {'PKR' if self.currency=='USD' else 'USD'}",
            self.toggle_currency, bg=COLORS["purple"], fg="#ffffff", pad=(14, 8)
        )
        btn.pack(side="right", padx=10)

    # ---------------- PRICE MODE (Retail / Distributor) ----------------
    def get_price(self, item):
        """Returns the price to use for this item based on the current
        price mode toggle — retail (consumer) or distributor (B2B/wholesale)."""
        return item["retail"] if self.price_mode.get() == "retail" else item["distributor"]

    def toggle_price_mode(self):
        self.price_mode.set("distributor" if self.price_mode.get() == "retail" else "retail")
        if self.active_screen == "calculator":
            self.show_calculator()

    def price_mode_button(self, parent):
        current = self.price_mode.get().capitalize()
        nxt = "Retail" if self.price_mode.get() == "distributor" else "Distributor"
        btn = styled_button(
            parent, f"🏷  {current} mode → {nxt}",
            self.toggle_price_mode, bg=COLORS["success"], fg="#0a1f14", pad=(14, 8)
        )
        btn.pack(side="right", padx=10)

    def topbar(self, title_text):
        top = tk.Frame(self.container, bg=COLORS["bg"])
        top.pack(fill="x", padx=20, pady=(18, 10))
        back = styled_button(top, "←  Home", self.show_home,
                              bg=COLORS["bg_input"], fg=COLORS["text"], pad=(14, 8))
        back.pack(side="left")
        tk.Label(top, text=title_text, font=FONT_HEADER, bg=COLORS["bg"], fg=COLORS["text"]).pack(side="left", padx=18)
        return top

    # ---------------- HOME ----------------
    def show_home(self):
        self.active_screen = "home"
        self.clear()

        wrap = tk.Frame(self.container, bg=COLORS["bg"])
        wrap.pack(expand=True)

        tk.Label(wrap, text="⚜", font=("Segoe UI", 34), bg=COLORS["bg"], fg=COLORS["accent"]).pack(pady=(60, 0))
        tk.Label(wrap, text="Clothing Export Business", font=FONT_TITLE,
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(pady=(4, 2))
        tk.Label(wrap, text="Pakistan → USA margin & shipping calculator", font=FONT_BODY,
                 bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(pady=(0, 40))

        btn_frame = tk.Frame(wrap, bg=COLORS["bg"])
        btn_frame.pack()

        cfg_btn = styled_button(btn_frame, "⚙   Configuration", self.show_config,
                                 bg=COLORS["bg_card"], fg=COLORS["text"], font=("Segoe UI", 13, "bold"),
                                 pad=(40, 18))
        cfg_btn.configure(highlightbackground=COLORS["accent"], highlightthickness=1)
        cfg_btn.pack(pady=10)

        calc_btn = styled_button(btn_frame, "🧮   Calculator", self.show_calculator,
                                  bg=COLORS["accent"], fg="#111318", font=("Segoe UI", 13, "bold"),
                                  pad=(40, 18))
        calc_btn.pack(pady=10)

    # ---------------- CONFIG ----------------
    def show_config(self):
        self.active_screen = "config"
        self.clear()

        top = self.topbar("Configuration")
        self.currency_button(top)

        # --- Item table card ---
        table_card = card(self.container)
        table_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        tk.Label(table_card, text="Item Catalog", font=FONT_SUB,
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 6))

        table_frame = tk.Frame(table_card, bg=COLORS["bg_card"])
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        sym = self.sym()
        cols = ("Name", "Season", f"Retail({sym})", f"Distrib({sym})", f"Prod({sym})", "Weight(kg)")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.refresh_tree()

        btn_frame = tk.Frame(table_card, bg=COLORS["bg_card"])
        btn_frame.pack(pady=(0, 14))
        styled_button(btn_frame, "+ Add Item", self.add_item_dialog,
                      bg=COLORS["success"], fg="#0a1f14", pad=(16, 8)).pack(side="left", padx=5)
        styled_button(btn_frame, "✎ Edit Selected", self.edit_item_dialog,
                      bg=COLORS["bg_input"], fg=COLORS["text"], pad=(16, 8)).pack(side="left", padx=5)
        styled_button(btn_frame, "✕ Remove Selected", self.remove_item,
                      bg=COLORS["danger"], fg="#2a0a0d", pad=(16, 8)).pack(side="left", padx=5)

        # --- Settings card ---
        settings_card = card(self.container)
        settings_card.pack(fill="x", padx=20, pady=(0, 20))

        tk.Label(settings_card, text="Shipping / Remittance / Duty / Tax Settings", font=FONT_SUB,
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 8))

        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill="x", padx=16, pady=(0, 6))

        self.setting_vars = {}
        labels = {
            "duty_rate": "Customs duty rate (0-1)",
            "transfer_multiplier": "Transfer value multiplier (batch duty basis)",
            "tax_rate": "Export tax rate on your share (0-1)",
            "split": "Your split of gross margin (0-1)",
            "remit_loss": "Remittance/FX loss (0-1)",
            "pkr_per_usd": "PKR per USD rate",
            "insurance_rate": "TCS insurance rate (0-1, official range 0.005-0.02)",
        }
        r = 0
        for key, label in labels.items():
            tk.Label(settings_inner, text=label, font=FONT_BODY, bg=COLORS["bg_card"],
                     fg=COLORS["text_dim"]).grid(row=r, column=0, sticky="w", pady=5)
            var = tk.StringVar(value=str(self.settings[key]))
            self.setting_vars[key] = var
            e = tk.Entry(settings_inner, textvariable=var, width=12, font=FONT_BODY,
                         bg=COLORS["bg_input"], fg=COLORS["text"], insertbackground=COLORS["text"],
                         relief="flat", highlightthickness=1, highlightbackground=COLORS["border"],
                         highlightcolor=COLORS["accent"])
            e.grid(row=r, column=1, padx=14, pady=5, ipady=4)
            r += 1

        tk.Label(settings_card, text="Shipping/duty/tax settings always entered in USD/decimal, "
                                       "regardless of display currency above.",
                 font=("Segoe UI", 9, "italic"), fg=COLORS["text_dim"], bg=COLORS["bg_card"]
                 ).pack(anchor="w", padx=16, pady=(0, 10))

        styled_button(settings_card, "💾 Save Settings", self.save_settings,
                      bg=COLORS["accent"], fg="#111318", pad=(20, 10)).pack(pady=(0, 16))

    def refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, it in enumerate(self.items):
            retail_disp = self.conv(it["retail"])
            distrib_disp = self.conv(it["distributor"])
            prod_disp = self.conv(it["prod"])
            if self.currency == "PKR":
                retail_str, distrib_str, prod_str = f"{retail_disp:,.0f}", f"{distrib_disp:,.0f}", f"{prod_disp:,.0f}"
            else:
                retail_str, distrib_str, prod_str = f"{retail_disp:,.2f}", f"{distrib_disp:,.2f}", f"{prod_disp:,.2f}"
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(it["name"], it["season"], retail_str, distrib_str, prod_str, it["weight"]), tags=(tag,))
        self.tree.tag_configure("even", background=COLORS["bg_card"])
        self.tree.tag_configure("odd", background="#202a42")

    def add_item_dialog(self, existing=None):
        dlg = tk.Toplevel(self)
        dlg.title("Edit Item" if existing else "Add Item")
        dlg.geometry("340x460")
        dlg.configure(bg=COLORS["bg"])

        note = f"Enter Retail/Distributor/Production price in {self.currency}. Stored internally as USD."
        tk.Label(dlg, text=note, wraplength=290, fg=COLORS["text_dim"], bg=COLORS["bg"],
                 font=("Segoe UI", 9, "italic")).pack(pady=(14, 10), padx=20)

        fields = ["name", "season", "retail", "distributor", "prod", "weight"]
        field_labels = {"name": "Name", "season": "Season", "retail": "Retail price (consumer)",
                         "distributor": "Distributor price (B2B)", "prod": "Production cost",
                         "weight": "Weight (kg)"}
        entries = {}
        for f in fields:
            tk.Label(dlg, text=field_labels[f], font=FONT_BODY, bg=COLORS["bg"],
                     fg=COLORS["text"]).pack(pady=(6, 2))
            e = tk.Entry(dlg, font=FONT_BODY, bg=COLORS["bg_input"], fg=COLORS["text"],
                         insertbackground=COLORS["text"], relief="flat",
                         highlightthickness=1, highlightbackground=COLORS["border"],
                         highlightcolor=COLORS["accent"], justify="center")
            if existing:
                val = existing[f]
                if f in ("retail", "distributor", "prod"):
                    val = round(self.conv(val), 2)
                e.insert(0, str(val))
            e.pack(ipady=5, padx=30, fill="x")
            entries[f] = e

        def save():
            try:
                retail_input = float(entries["retail"].get())
                distributor_input = float(entries["distributor"].get())
                prod_input = float(entries["prod"].get())
                if self.currency == "PKR":
                    retail_input = retail_input / self.settings["pkr_per_usd"]
                    distributor_input = distributor_input / self.settings["pkr_per_usd"]
                    prod_input = prod_input / self.settings["pkr_per_usd"]
                new_item = {
                    "name": entries["name"].get().strip(),
                    "season": entries["season"].get().strip() or "All-Year",
                    "retail": retail_input,
                    "distributor": distributor_input,
                    "prod": prod_input,
                    "weight": float(entries["weight"].get()),
                }
            except ValueError:
                messagebox.showerror("Error", "Retail/Distributor/Prod/Weight must be numbers")
                return
            if not new_item["name"]:
                messagebox.showerror("Error", "Name required")
                return
            if existing:
                idx = self.items.index(existing)
                self.items[idx] = new_item
            else:
                self.items.append(new_item)
                self.quantities[new_item["name"]] = 0
            self.refresh_tree()
            dlg.destroy()

        styled_button(dlg, "Save", save, bg=COLORS["accent"], fg="#111318",
                      pad=(30, 10)).pack(pady=18)

    def edit_item_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select item", "Select an item to edit first")
            return
        name = self.tree.item(sel[0])["values"][0]
        existing = next((i for i in self.items if i["name"] == name), None)
        if existing:
            self.add_item_dialog(existing)

    def remove_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select item", "Select an item to remove first")
            return
        name = self.tree.item(sel[0])["values"][0]
        self.items = [i for i in self.items if i["name"] != name]
        self.quantities.pop(name, None)
        self.refresh_tree()

    def save_settings(self):
        try:
            for key, var in self.setting_vars.items():
                self.settings[key] = float(var.get())
            messagebox.showinfo("Saved", "Settings updated.")
        except ValueError:
            messagebox.showerror("Error", "All settings must be numbers")

    # ---------------- CALCULATOR ----------------
    def show_calculator(self):
        self.active_screen = "calculator"
        self.clear()

        top = self.topbar("Order Calculator")
        self.currency_button(top)
        self.price_mode_button(top)

        mode_color = COLORS["accent"] if self.price_mode.get() == "retail" else COLORS["success"]
        mode_text = "🛍  RETAIL PRICING (consumer)" if self.price_mode.get() == "retail" else "📦  DISTRIBUTOR PRICING (B2B/wholesale)"
        tk.Label(self.container, text=mode_text, font=FONT_BODY_B, bg=COLORS["bg"], fg=mode_color).pack(pady=(0, 8))

        main_row = tk.Frame(self.container, bg=COLORS["bg"], height=300)
        main_row.pack(fill="x", padx=20, pady=(0, 10))
        main_row.pack_propagate(False)  # keep cart/summary row capped at 300px so
                                         # the split card below always gets real space

        cart_card = card(main_row)
        cart_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        result_card = card(main_row)
        result_card.pack(side="right", fill="both", expand=True)

        tk.Label(result_card, text="💰 Order Summary", font=FONT_SUB,
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 6))
        result_text_frame = tk.Frame(result_card, bg=COLORS["bg_card"])
        result_text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.result_text = tk.Text(result_text_frame, font=FONT_MONO,
                                    bg=COLORS["bg_card"], fg=COLORS["text"], relief="flat",
                                    insertbackground=COLORS["text"], padx=14, pady=12,
                                    highlightthickness=0, wrap="word")
        result_sb = ttk.Scrollbar(result_text_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_sb.set)
        self.result_text.pack(side="left", fill="both", expand=True)
        result_sb.pack(side="right", fill="y")
        self.result_text.tag_configure("profit", foreground=COLORS["success"], font=FONT_MONO + ("bold",))
        self.result_text.tag_configure("loss", foreground=COLORS["danger"], font=FONT_MONO + ("bold",))
        self.result_text.tag_configure("dim", foreground=COLORS["text_dim"])
        self.result_text.tag_configure("accent", foreground=COLORS["accent"])

        canvas_frame = tk.Frame(cart_card, bg=COLORS["bg_card"])
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_card"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_card"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.qty_labels = {}
        header_row = tk.Frame(scroll_frame, bg=COLORS["bg_card"], height=18)
        header_row.pack(fill="x", padx=6, pady=(0, 0))
        header_row.pack_propagate(False)
        tk.Label(header_row, text="", width=24, bg=COLORS["bg_card"]).pack(side="left", padx=(14, 0))
        tk.Label(header_row, text="Design", font=("Segoe UI", 8, "bold"), width=13, anchor="sw",
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).pack(side="left", fill="y")
        tk.Label(header_row, text=self.price_mode.get().capitalize(), font=("Segoe UI", 8, "bold"), width=13, anchor="sw",
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(side="left", fill="y")
        first_season = True
        for season in ["Winter", "All-Year", "Summer"]:
            season_items = [i for i in self.items if i["season"] == season]
            if not season_items:
                continue
            season_icon = {"Winter": "❄", "All-Year": "🌤", "Summer": "☀"}[season]
            top_pad = 4 if first_season else 14
            first_season = False
            tk.Label(scroll_frame, text=f"{season_icon}  {season}", font=FONT_SUB,
                     bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w", pady=(top_pad, 4), padx=6)
            for it in season_items:
                row = tk.Frame(scroll_frame, bg=COLORS["bg_input"])
                row.pack(fill="x", pady=4, padx=6)
                design_disp = self.fmt(it["prod"])
                sell_disp = self.fmt(self.get_price(it))
                tk.Label(row, text=it["name"], font=FONT_BODY, bg=COLORS["bg_input"],
                         fg=COLORS["text"], anchor="w", width=24).pack(side="left", padx=(14, 0), pady=10)
                tk.Label(row, text=design_disp, font=FONT_BODY, bg=COLORS["bg_input"],
                         fg=COLORS["text_dim"], anchor="w", width=13).pack(side="left")
                tk.Label(row, text=sell_disp, font=FONT_BODY_B, bg=COLORS["bg_input"],
                         fg=COLORS["accent"], anchor="w", width=13).pack(side="left")

                qty_frame = tk.Frame(row, bg=COLORS["bg_input"])
                qty_frame.pack(side="right", padx=(0, 16))
                minus = styled_button(qty_frame, "−", lambda n=it["name"]: self.change_qty(n, -1),
                                       bg=COLORS["bg_card"], fg=COLORS["text"], pad=(12, 5))
                minus.pack(side="left", padx=4)
                lbl = tk.Label(qty_frame, text=str(self.quantities.get(it["name"], 0)), width=3,
                                font=FONT_BODY_B, bg=COLORS["bg_input"], fg=COLORS["accent"])
                lbl.pack(side="left")
                self.qty_labels[it["name"]] = lbl
                plus = styled_button(qty_frame, "+", lambda n=it["name"]: self.change_qty(n, 1),
                                      bg=COLORS["accent"], fg="#111318", pad=(12, 5))
                plus.pack(side="left", padx=(4, 0))

        btn_row = tk.Frame(self.container, bg=COLORS["bg"])
        btn_row.pack(pady=12)
        calc_btn = styled_button(btn_row, "▶  Calculate", self.calculate,
                                  bg=COLORS["success"], fg="#0a1f14", font=("Segoe UI", 12, "bold"),
                                  pad=(30, 12))
        calc_btn.pack(side="left", padx=6)
        split_btn = styled_button(btn_row, "📦  Best Split", self.show_best_split,
                                   bg=COLORS["purple"], fg="#ffffff", font=("Segoe UI", 12, "bold"),
                                   pad=(30, 12))
        split_btn.pack(side="left", padx=6)
        insurance_frame = tk.Frame(self.container, bg=COLORS["bg"])
        insurance_frame.pack(pady=(0, 10))
        tk.Checkbutton(
            insurance_frame, text="  Include TCS Insurance (0.5%-2% of declared value, official TCS range)",
            variable=self.insurance_enabled, command=self.render_result,
            font=FONT_BODY, bg=COLORS["bg"], fg=COLORS["text"],
            selectcolor=COLORS["bg_input"], activebackground=COLORS["bg"],
            activeforeground=COLORS["text"], relief="flat", highlightthickness=0
        ).pack()

        split_card = card(self.container)
        split_card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        tk.Label(split_card, text="📦 Order Split Analysis", font=FONT_SUB,
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 6))
        split_text_frame = tk.Frame(split_card, bg=COLORS["bg_card"])
        split_text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.split_text = tk.Text(split_text_frame, height=10, font=FONT_MONO, bg=COLORS["bg_card"], fg=COLORS["text"],
                                   relief="flat", insertbackground=COLORS["text"], padx=14, pady=8,
                                   highlightthickness=0, wrap="word")
        split_sb = ttk.Scrollbar(split_text_frame, orient="vertical", command=self.split_text.yview)
        self.split_text.configure(yscrollcommand=split_sb.set)
        self.split_text.pack(side="left", fill="both", expand=True)
        split_sb.pack(side="right", fill="y")
        self.split_text.tag_configure("profit", foreground=COLORS["success"], font=FONT_MONO + ("bold",))
        self.split_text.tag_configure("dim", foreground=COLORS["text_dim"])
        self.split_text.tag_configure("accent", foreground=COLORS["accent"], font=FONT_MONO + ("bold",))
        self.split_text.insert("end", "Click Calculate, then Best Split,\nto see the optimal way to break\nthis order into shipments.\n", "dim")
        # re-display the last result (if any) whenever this screen is rebuilt,
        # e.g. after switching currency — quantities/cart data survive independently
        self.render_result()
        self.render_best_split()

    def change_qty(self, name, delta):
        self.quantities[name] = max(0, self.quantities.get(name, 0) + delta)
        self.qty_labels[name].config(text=str(self.quantities[name]))

    def calculate(self):
        s = self.settings
        total_weight = 0.0
        total_qty = 0
        cart_items = []

        for it in self.items:
            q = self.quantities.get(it["name"], 0)
            if q <= 0:
                continue
            cart_items.append((it, q))
            total_weight += it["weight"] * q
            total_qty += q

        if total_qty == 0:
            self.result_text.delete("1.0", "end")
            self.result_text.insert("end", "No items selected.\n", "dim")
            self.last_result_cart = None
            return

        # store the raw inputs needed to recompute/redisplay at any currency
        self.last_result_cart = {"cart_items": cart_items, "total_weight": total_weight}
        self.last_split_result = None  # cart changed — old split analysis is stale
        self.render_result()

    def show_best_split(self):
        if not self.last_result_cart:
            messagebox.showinfo("Calculate first", "Click Calculate first, then Best Split.")
            return
        cart_items = self.last_result_cart["cart_items"]
        s = self.settings
        shipments, best_cost_usd = find_best_shipping_plan(cart_items, s, self.get_price)
        one_duty, one_shipping, _, _ = compute_shipment_cost(cart_items, s, self.get_price)
        one_shipment_cost_usd = one_duty + one_shipping
        self.last_split_result = {
            "shipments": shipments,
            "best_cost_usd": best_cost_usd,
            "one_shipment_cost_usd": one_shipment_cost_usd,
        }
        self.render_best_split()

    def render_best_split(self):
        """Renders the last split analysis using self.fmt(), so it
        redisplays correctly if currency is toggled afterward."""
        if not self.last_split_result:
            return
        r = self.last_split_result
        shipments = r["shipments"]
        total_qty = sum(shipments)
        savings_usd = r["one_shipment_cost_usd"] - r["best_cost_usd"]

        self.split_text.delete("1.0", "end")
        self.split_text.insert("end", "📦 Best Shipping Split\n", "accent")
        self.split_text.insert("end", "─" * 34 + "\n", "dim")
        if len(shipments) == 1:
            self.split_text.insert("end", f"Ship all {total_qty} units in ONE shipment.\n\n")
        else:
            plan_str = " + ".join(str(x) for x in shipments)
            self.split_text.insert("end", f"Split {total_qty} units into {len(shipments)} shipments:\n")
            self.split_text.insert("end", f"  {plan_str}\n\n")
        self.split_text.insert("end", f"One-shipment cost (duty+ship): {self.fmt(r['one_shipment_cost_usd'])}\n", "dim")
        self.split_text.insert("end", f"Best-split cost (duty+ship):   {self.fmt(r['best_cost_usd'])}\n", "dim")
        if savings_usd > 0.01:
            self.split_text.insert("end", f"\n✅ Saves {self.fmt(savings_usd)} vs one shipment\n", "profit")
        else:
            self.split_text.insert("end", "\nOne shipment is already optimal — no split needed.\n", "dim")

    def render_result(self):
        """Renders the last calculated result using self.fmt(), which
        automatically respects whichever currency is currently selected."""
        if not self.last_result_cart:
            return
        s = self.settings
        cart_items = self.last_result_cart["cart_items"]
        total_weight = self.last_result_cart["total_weight"]

        total_prod = sum(it["prod"] * q for it, q in cart_items)
        total_revenue = sum(self.get_price(it) * q for it, q in cart_items)

        shipping_cost = get_shipping_cost(total_weight, s["pkr_per_usd"])
        is_batch = total_weight > 2.0

        if is_batch:
            duty = sum(s["duty_rate"] * (s["transfer_multiplier"] * it["prod"]) * q for it, q in cart_items)
            declared_value = sum(s["transfer_multiplier"] * it["prod"] * q for it, q in cart_items)
            mode = f"BATCH  (total weight {total_weight:.2f}kg, tiered shipping ${shipping_cost:.2f})"
        else:
            duty = sum(s["duty_rate"] * self.get_price(it) * q for it, q in cart_items)
            declared_value = sum(self.get_price(it) * q for it, q in cart_items)
            mode = f"INDIVIDUAL  (total weight {total_weight:.2f}kg, tiered shipping ${shipping_cost:.2f})"

        insurance_cost = declared_value * s["insurance_rate"] if self.insurance_enabled.get() else 0.0

        landed_cost = total_prod + duty + shipping_cost + insurance_cost
        gross_margin = total_revenue - landed_cost
        your_share_usd = gross_margin * s["split"] * (1 - s["remit_loss"])
        your_share_usd_after_tax = your_share_usd * (1 - s["tax_rate"]) if your_share_usd > 0 else your_share_usd

        is_profit = your_share_usd_after_tax >= 0

        self.result_text.delete("1.0", "end")
        price_label = "Retail" if self.price_mode.get() == "retail" else "Distrib."
        self.result_text.insert("end", f"Shipping mode: ", "dim")
        self.result_text.insert("end", f"{mode}\n", "accent")
        self.result_text.insert("end", f"Display currency: {self.currency}   |   Price mode: {self.price_mode.get().capitalize()}\n", "dim")
        self.result_text.insert("end", "─" * 80 + "\n", "dim")
        self.result_text.insert("end", f"{'Item':30s}{'Qty':>6s}{price_label:>14s}{'Prod':>14s}\n", "accent")
        for it, q in cart_items:
            self.result_text.insert("end", f"{it['name']:30s}{q:>6d}{self.fmt(self.get_price(it)):>14s}{self.fmt(it['prod']):>14s}\n")
        self.result_text.insert("end", "─" * 80 + "\n", "dim")
        self.result_text.insert("end", f"Total revenue:          {self.fmt(total_revenue)}\n")
        self.result_text.insert("end", f"Total production cost:  {self.fmt(total_prod)}\n")
        self.result_text.insert("end", f"Total duty:             {self.fmt(duty)}\n")
        self.result_text.insert("end", f"Total shipping cost:    {self.fmt(shipping_cost)}\n")
        if self.insurance_enabled.get():
            self.result_text.insert("end", f"Insurance cost ({s['insurance_rate']*100:.2f}%): {self.fmt(insurance_cost)}\n", "dim")
        self.result_text.insert("end", f"Landed cost:            {self.fmt(landed_cost)}\n")
        self.result_text.insert("end", f"Gross margin:           {self.fmt(gross_margin)}\n")
        self.result_text.insert("end", f"Your 50/50 share (after remittance loss & export tax): {self.fmt(your_share_usd_after_tax)}\n")
        self.result_text.insert("end", "─" * 80 + "\n", "dim")
        self.result_text.insert("end", f"RESULT: {'✅ PROFIT' if is_profit else '❌ LOSS'}\n",
                                 "profit" if is_profit else "loss")


if __name__ == "__main__":
    app = ClothingCalcApp()
    app.mainloop()