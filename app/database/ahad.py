items = [
    {"sku": "rice-001", "quantity": 5},
    {"sku": "milk-001", "quantity": 2},
    {"sku": "rice-001", "quantity": 4},
    {"sku": "bread-001", "quantity": 1},
]

cart = {}

for item in items:
    sku = item["sku"].strip().lower()
    cart[sku] = cart.get(sku, 0) + item["quantity"]

for sku, quantity in cart.items():
    print(sku)
    print(quantity)

print(cart)
