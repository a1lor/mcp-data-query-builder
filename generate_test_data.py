"""Script utilitaire pour générer un fichier CSV de test.

Ce script crée (ou écrase) un fichier `test_data.csv` dans le répertoire
courant, contenant quelques lignes de produits avec prix et catégorie.
"""

from __future__ import annotations

import csv
from pathlib import Path


def main() -> None:
    data = [
        {"product": "Laptop", "price": 1299.99, "category": "Electronics"},
        {"product": "Headphones", "price": 199.90, "category": "Electronics"},
        {"product": "Coffee Machine", "price": 89.50, "category": "Home"},
        {"product": "Desk Chair", "price": 159.00, "category": "Furniture"},
        {"product": "Notebook", "price": 4.99, "category": "Stationery"},
    ]

    csv_path = Path("test_data.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product", "price", "category"])
        writer.writeheader()
        writer.writerows(data)

    print(f"Fichier de test généré : {csv_path.resolve()}")


if __name__ == "__main__":
    main()

