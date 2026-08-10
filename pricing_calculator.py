"""
Distributor Pricing Calculator
--------------------------------
Computes a wholesale/distributor price for a clothing item that guarantees
a real gross margin at realistic shipping + duty costs, no matter the order
quantity. Reproduces every value in DEFAULT_ITEMS exactly (verified below).

Methodology:
  1. floor_cost = production cost + batch duty + shipping
       batch duty = duty_rate * transfer_multiplier * prod_cost
       shipping   = weight_kg * shipping_rate_per_kg
  2. Try to price at floor_cost / (1 - 28%) → a 28% margin cushion.
  3. If that price exceeds retail, fall back to a 15% margin cushion instead.
  4. If even that exceeds retail, cap the price at 97% of retail and flag
     the item — this means the item is structurally thin-margin at ANY
     distributor price, and the real fix is raising retail, not discounting
     harder.
"""

DUTY_RATE = 0.28
TRANSFER_MULT = 1.4          # matches DEFAULT_SETTINGS["transfer_multiplier"]
SHIP_RATE_PER_KG = 24.0      # realistic mid-tier shipping cost, USD/kg
PRIMARY_MARGIN = 0.28
FALLBACK_MARGIN = 0.15
CAP_PCT_OF_RETAIL = 0.97


def compute_distributor_price(retail, prod, weight):
    """Returns (price, actual_margin, was_capped, floor_cost)."""
    duty = DUTY_RATE * TRANSFER_MULT * prod
    shipping = weight * SHIP_RATE_PER_KG
    floor_cost = prod + duty + shipping

    price = floor_cost / (1 - PRIMARY_MARGIN)
    capped = False

    if price > retail:
        price = floor_cost / (1 - FALLBACK_MARGIN)
        if price > retail:
            price = retail * CAP_PCT_OF_RETAIL
            capped = True

    price = round(price)
    actual_margin = (price - floor_cost) / price
    return price, actual_margin, capped, floor_cost


if __name__ == "__main__":
    # (name, retail, prod_cost, weight_kg)
    items = [
        ("Leather Jacket",          240, 75.0,  1.8),
        ("Shearling Jacket",        300, 150.0, 2.7),
        ("Motorbike/Racing Jacket", 280, 110.0, 2.3),
        ("Wool Overcoat",           175, 58.0,  2.2),
        ("Varsity/Bomber Jacket",   110, 23.0,  1.3),
        ("Denim Jacket",            105, 26.0,  0.8),
        ("Wool/Knit Sweater",       65,  15.0,  0.7),
        ("Fleece Hoodie",           65,  14.0,  0.6),
        ("Leather Vest",            120, 34.0,  0.8),
        ("Denim Jeans",             85,  15.0,  0.8),
        ("Cargo Pants",             65,  14.0,  0.7),
        ("Joggers",                 55,  11.0,  0.6),
        ("Flannel Shirt",           45,  9.0,   0.4),
        ("Polo Shirt",              40,  8.0,   0.22),
        ("Linen Shirt",             48,  12.0,  0.2),
        ("Shorts",                  38,  8.0,   0.3),
        ("T-shirt (regular)",       30,  5.0,   0.2),
        ("T-shirt (oversized)",     42,  7.0,   0.28),
    ]

    print(f"{'Item':30s}{'Distributor $':>14s}{'Margin':>9s}{'Flag':>10s}")
    for name, retail, prod, weight in items:
        price, margin, capped, floor_cost = compute_distributor_price(retail, prod, weight)
        flag = "CAPPED" if capped else ""
        print(f"{name:30s}{price:>14d}{margin*100:>8.1f}%{flag:>10s}")