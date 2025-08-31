# Builds a SQLite database with >=60 sample products and their perceptual hashes (pHash)
# Run: python scripts/build_index.py

import os
import sqlite3
import random
import time
import io
from typing import List, Dict

import requests
from PIL import Image
import imagehash

DB_PATH = os.path.join("data", "products.db")
os.makedirs("data", exist_ok=True)

CATEGORIES = [
    "T-Shirts",
    "Sneakers",
    "Backpacks",
    "Watches",
    "Headphones",
    "Sunglasses",
]

def make_products(n: int = 60) -> List[Dict]:
    products = []
    random.seed(42)
    for i in range(1, n + 1):
        category = random.choice(CATEGORIES)
        name = f"{category[:-1]} Model #{i}"
        price = round(random.uniform(19, 199), 2)
        # picsum seed makes deterministic placeholder images
        image_url = f"https://picsum.photos/seed/prod{i}/600/600"
        products.append(
            {
                "id": i,
                "name": name,
                "category": category,
                "price": price,
                "image_url": image_url,
            }
        )
    return products


def download_image(url: str, timeout=10):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def compute_phash(img: Image.Image) -> str:
    img = img.convert("RGB")
    return str(imagehash.phash(img))  # hex string


def init_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT NOT NULL,
            phash TEXT NOT NULL
        )
        """
    )
    conn.execute("DELETE FROM products")


def main():
    print("[build_index] Generating sample products...")
    products = make_products(60)
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        for p in products:
            try:
                img = download_image(p["image_url"])
                phash = compute_phash(img)
                conn.execute(
                    """
                    INSERT INTO products (id, name, category, price, image_url, phash)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (p["id"], p["name"], p["category"], p["price"], p["image_url"], phash),
                )
                conn.commit()
                print(f"[build_index] Indexed {p['id']:02d}: {p['name']} | phash={phash}")
                # be kind to the placeholder service
                time.sleep(0.05)
            except Exception as e:
                print(f"[build_index] Failed {p['id']:02d}: {e}")

    print(f"[build_index] Done. DB at {DB_PATH}")


if __name__ == "__main__":
    main()
