import random
from .database import Product

def seed(db):
    if db.query(Product).count():
        return
    rng = random.Random(42)
    groups = [
        ('Electronics', 'Wireless headphones', 89, {'connection': 'Bluetooth', 'form': 'over-ear'}, 'ABS'),
        ('Electronics', 'USB-C charger', 29, {'connector': 'USB-C', 'wattage': 65}, 'ABS'),
        ('Home & Kitchen', 'Water bottle', 24, {'capacity_ml': 750, 'food_safe': True}, 'Stainless steel'),
        ('Home & Kitchen', 'Frying pan', 45, {'diameter_cm': 28, 'induction': True}, 'Aluminium'),
        ('Grocery', 'Oat milk', 4, {'volume_ml': 1000, 'allergen': 'oats', 'vegan': True}, 'Carton'),
        ('Grocery', 'Ground coffee', 12, {'weight_g': 250, 'caffeine': True}, 'Paper'),
        ('Personal Care', 'Shampoo', 14, {'volume_ml': 300, 'sulfate_free': True}, 'Recycled plastic'),
        ('Personal Care', 'Face moisturizer', 19, {'volume_ml': 100, 'fragrance_free': True}, 'Glass'),
        ('Apparel', 'Cotton t-shirt', 22, {'fit': 'regular', 'size': 'M'}, 'Cotton'),
        ('Apparel', 'Running socks', 9, {'size': 'M', 'pairs': 3}, 'Cotton blend'),
    ]
    brands = ['Northline', 'Everwell', 'Forma', 'Kindred', 'Atlas', 'Origin']
    for i in range(600):
        category, sub, base, specs, material = groups[i % len(groups)]
        color = rng.choice(['Cloud', 'Charcoal', 'Sage', 'Navy'])
        price = round(base*rng.uniform(.75, 1.35), 2)
        brand = brands[(i//10) % len(brands)]
        db.add(Product(product_name=f'{brand} {sub} {i//60+1:02}', sku=f'SG-{i+1:05}', brand=brand,
            category=category, subcategory=sub, description=f'Synthetic retail sample. {color} {sub.lower()} from {brand}, designed for everyday use.',
            price=price, cost=round(price*rng.uniform(.45,.8),2), attributes={'color':color,'material':material,'tier':rng.choice(['essential','premium'])},
            specifications=specs, color=color, size=str(specs.get('size','Standard')), material=material,
            product_rating=round(rng.uniform(3.2,5),1), stock_quantity=0 if i%9==0 else rng.randint(1,180),
            supplier_id=f'SUP-{i%12+1:02}', sales_quantity=rng.randint(10,700), status='discontinued' if i%47==0 else 'active'))
    db.commit()
