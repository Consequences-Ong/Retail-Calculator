"""
Profit Target & Best-Batch Calculator
--------------------------------------
Companion to the distributor pricing script. For each item (using its
distributor price), answers three things:

  1. Minimum quantity needed so "your share" (the 50/50 net profit share,
     after remittance loss & export tax — same formula as the app's
     render_result) reaches Rs 1,000+.
  2. Minimum quantity needed so that share reaches Rs 2,000+.
  3. The single BEST quantity to sell at — the point that maximizes your
     share PER UNIT. Shipping is tiered in steps, so profit-per-unit is a
     sawtooth, not a smooth curve — exactly what your 25 vs 26 T-shirt
     example showed: 25 lands just under a shipping-tier ceiling, 26 tips
     it over and shipping jumps ~66% for one extra unit, cutting your
     share by more than half.

Uses the exact same math as ClothingCalcApp.render_result() (batch-mode
duty/shipping thresholds, split, remittance loss, export tax).
"""

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

def get_shipping_cost(total_weight_kg, pkr_per_usd):
    for ceiling_kg, cost_pkr in SHIPPING_TIERS_PKR:
        if total_weight_kg <= ceiling_kg:
            return cost_pkr / pkr_per_usd
    last_kg, last_cost = SHIPPING_TIERS_PKR[-1]
    return total_weight_kg * (last_cost / last_kg) / pkr_per_usd

# (name, distributor_price_usd, prod_cost_usd, weight_kg) — from corrected DEFAULT_ITEMS
ITEMS = [
    ("Leather Jacket",          205, 75.0,  1.8),
    ("Shearling Jacket",        291, 150.0, 2.7),
    ("Motorbike/Racing Jacket", 245, 110.0, 2.3),
    ("Wool Overcoat",           157, 58.0,  2.2),
    ("Varsity/Bomber Jacket",   88,  23.0,  1.3),
    ("Denim Jacket",            77,  26.0,  0.8),
    ("Wool/Knit Sweater",       52,  15.0,  0.7),
    ("Fleece Hoodie",           47,  14.0,  0.6),
    ("Leather Vest",            92,  34.0,  0.8),
    ("Denim Jeans",             56,  15.0,  0.8),
    ("Cargo Pants",             50,  14.0,  0.7),
    ("Joggers",                 41,  11.0,  0.6),
    ("Flannel Shirt",           31,  9.0,   0.4),
    ("Polo Shirt",              23,  8.0,   0.22),
    ("Linen Shirt",             30,  12.0,  0.2),
    ("Shorts",                  25,  8.0,   0.3),
    ("T-shirt (regular)",       16,  5.0,   0.2),
    ("T-shirt (oversized)",     23,  7.0,   0.28),
]


def compute_order(price_usd, prod_usd, weight_kg, qty, settings):
    """Same math as ClothingCalcApp.render_result() for a single-item cart.
    Insurance assumed OFF. Returns all line items in PKR."""
    pkr = settings["pkr_per_usd"]
    total_weight = weight_kg * qty

    revenue_usd = price_usd * qty
    prod_total_usd = prod_usd * qty
    shipping_usd = get_shipping_cost(total_weight, pkr)
    is_batch = total_weight > 2.0

    if is_batch:
        duty_usd = settings["duty_rate"] * settings["transfer_multiplier"] * prod_usd * qty
    else:
        duty_usd = settings["duty_rate"] * price_usd * qty

    landed_usd = prod_total_usd + duty_usd + shipping_usd
    gross_margin_usd = revenue_usd - landed_usd
    your_share_usd = gross_margin_usd * settings["split"] * (1 - settings["remit_loss"])
    if your_share_usd > 0:
        your_share_usd *= (1 - settings["tax_rate"])

    return {
        "qty": qty, "weight": total_weight, "batch": is_batch,
        "revenue_pkr": revenue_usd * pkr,
        "prod_pkr": prod_total_usd * pkr,
        "duty_pkr": duty_usd * pkr,
        "shipping_pkr": shipping_usd * pkr,
        "landed_pkr": landed_usd * pkr,
        "gross_margin_pkr": gross_margin_usd * pkr,
        "share_pkr": your_share_usd * pkr,
    }


MAX_WEIGHT_KG = 25.0   # <-- change this to 20 or 30 etc. as needed

def max_qty_for_weight(weight_kg, max_weight_kg=MAX_WEIGHT_KG):
    """Largest whole quantity of this item that stays within the weight cap."""
    return max(1, int(max_weight_kg // weight_kg))


def find_min_qty_for_target(price_usd, prod_usd, weight_kg, target_pkr, settings,
                             max_weight_kg=MAX_WEIGHT_KG):
    """Smallest qty where share_pkr >= target_pkr, capped at max_weight_kg.
    Returns (qty, share) or (None, None) if unreachable within the cap."""
    cap_qty = max_qty_for_weight(weight_kg, max_weight_kg)
    for q in range(1, cap_qty + 1):
        r = compute_order(price_usd, prod_usd, weight_kg, q, settings)
        if r["share_pkr"] >= target_pkr:
            return q, r["share_pkr"]
    return None, None


def find_best_qty(price_usd, prod_usd, weight_kg, settings, max_weight_kg=MAX_WEIGHT_KG):
    """Best qty (max share per unit), searched only up to max_weight_kg —
    won't ever recommend an order heavier than the physical cap."""
    cap_qty = max_qty_for_weight(weight_kg, max_weight_kg)
    best_q, best_per_unit, best_share = 1, float("-inf"), 0
    for q in range(1, cap_qty + 1):
        r = compute_order(price_usd, prod_usd, weight_kg, q, settings)
        per_unit = r["share_pkr"] / q
        if per_unit > best_per_unit:
            best_q, best_per_unit, best_share = q, per_unit, r["share_pkr"]
    return best_q, best_per_unit, best_share


if __name__ == "__main__":
    s = DEFAULT_SETTINGS
    print(f"{'Item':30s}{'Qty→1000+':>12s}{'Qty→2000+':>12s}{'Best Qty':>10s}{'Best/unit':>12s}{'Best Total':>13s}")
    print("-" * 90)
    for name, price, prod, weight in ITEMS:
        q1000, _ = find_min_qty_for_target(price, prod, weight, 1000, s)
        q2000, _ = find_min_qty_for_target(price, prod, weight, 2000, s)
        best_q, best_per_unit, best_share = find_best_qty(price, prod, weight, s)
        print(f"{name:30s}{str(q1000 or 'n/a'):>12s}{str(q2000 or 'n/a'):>12s}{best_q:>10d}"
              f"{best_per_unit:>10,.0f}/u{best_share:>13,.0f}")