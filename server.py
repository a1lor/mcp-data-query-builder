"""MCP server for Project B: Data Query Builder.

Serveur MCP FastMCP permettant de :
- charger des fichiers CSV dans une base SQLite en mémoire,
- inspecter le schéma courant,
- exécuter des requêtes SQL en lecture seule,
- obtenir des statistiques simples sur une colonne,
- exposer le schéma via une ressource MCP.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("data-query-builder")

# --- Setup (DB + helpers) ---
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
DATA_ROOT = os.path.realpath(os.getenv("DATA_QUERY_ROOT", os.getcwd()))


def load_csv_to_table(conn: sqlite3.Connection, file_path: str, table_name: str) -> str:
    """Charger un CSV dans une table SQLite simple (toutes les colonnes en TEXT)."""
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return "CSV is empty"
        columns = {col: "TEXT" for col in rows[0].keys()}
        col_defs = ", ".join(f'"{col}" {typ}' for col, typ in columns.items())
        conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')
        placeholders = ", ".join("?" for _ in columns)
        for row in rows:
            conn.execute(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                list(row.values()),
            )
        conn.commit()
        return f"Loaded {len(rows)} rows into {table_name}"


def _list_tables() -> List[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [r["name"] for r in cur.fetchall()]


def _describe_schema() -> List[Dict[str, Any]]:
    schema: List[Dict[str, Any]] = []
    for table in _list_tables():
        cur = conn.execute(f'PRAGMA table_info("{table}")')
        columns = [
            {"name": r["name"], "type": r["type"] or "TEXT", "not_null": bool(r["notnull"])}
            for r in cur.fetchall()
        ]
        schema.append({"table": table, "columns": columns})
    return schema


FORBIDDEN_SQL_KEYWORDS = (
    "DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "REPLACE", "TRUNCATE",
    "CREATE", "DETACH", "VACUUM", "ATTACH", "PRAGMA",
)
FORBIDDEN_SQL_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in FORBIDDEN_SQL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def is_sql_read_only(sql: str) -> Tuple[bool, Optional[str]]:
    m = FORBIDDEN_SQL_RE.search(sql)
    if m:
        return False, m.group(1)
    return True, None


# --- Tools ---

@mcp.tool()
def load_csv(file_path: str, table_name: str) -> str:
    """Charger un fichier CSV dans une table SQLite en mémoire.

    Paramètres
    ----------
    file_path : str
        Chemin vers le fichier CSV lisible côté serveur.
    table_name : str
        Nom de la table à créer dans la base en mémoire.
    """

    try:
        # Capability fencing : normaliser le chemin et empêcher toute sortie de DATA_ROOT.
        if os.path.isabs(file_path):
            candidate = file_path
        else:
            candidate = os.path.join(DATA_ROOT, file_path)
        normalized_path = os.path.realpath(candidate)
        if not (normalized_path == DATA_ROOT or normalized_path.startswith(DATA_ROOT + os.sep)):
            return (
                "Erreur : accès refusé. Le fichier demandé est en dehors du répertoire autorisé. "
                "Utilisez un chemin à l'intérieur de DATA_QUERY_ROOT."
            )

        result = load_csv_to_table(conn, normalized_path, table_name)
    except FileNotFoundError:
        return f"Erreur : fichier introuvable ({file_path})."
    except Exception as e:  # pragma: no cover - renvoi d'erreur simple
        return f"Erreur lors du chargement du CSV : {e}"
    return result


@mcp.tool()
def describe_schema() -> List[Dict[str, Any]] | str:
    """Retourner le schéma courant de la base SQLite.

    Renvoie une liste de tables, chacune contenant ses colonnes et types, par exemple :
    [
      { "table": "users", "columns": [{"name": "id", "type": "TEXT", "not_null": False}, ...] },
      ...
    ]
    """

    try:
        return _describe_schema()
    except Exception as e:  # pragma: no cover - renvoi d'erreur simple
        return f"Erreur lors de la lecture du schéma : {e}"


@mcp.tool()
def list_tables() -> List[Dict[str, Any]] | str:
    """List all tables in the current database with their row counts.

    Returns a list of objects with "table" (table name) and "row_count" (number of rows).
    Useful to see which tables exist and how much data they contain.
    """

    try:
        tables = _list_tables()
        result: List[Dict[str, Any]] = []
        for table in tables:
            cur = conn.execute(f'SELECT COUNT(*) AS cnt FROM "{table}"')
            row = cur.fetchone()
            count = row["cnt"] if isinstance(row, sqlite3.Row) else row[0]
            result.append({"table": table, "row_count": count})
        return result
    except Exception as e:  # pragma: no cover
        return f"Erreur lors de la liste des tables : {e}"


@mcp.tool()
def run_query(sql: str) -> Dict[str, Any] | str:
    """Exécuter une requête SQL en lecture seule sur la base.

    Sécurité :
    - Rejette toute requête contenant DELETE, DROP, UPDATE, INSERT, ALTER, REPLACE,
      TRUNCATE, CREATE, DETACH, VACUUM, ATTACH, PRAGMA.
    - Seuls les SELECT sont autorisés (agrégations, filtrage, jointures).

    Paramètres
    ----------
    sql : str
        Requête SQL complète à exécuter.
    """

    ok, keyword = is_sql_read_only(sql)
    if not ok:
        return (
            f"Requête rejetée : le mot-clé « {keyword} » n'est pas autorisé. "
            "Seules les requêtes en lecture (SELECT) sont acceptées. "
            "Les opérations DROP, DELETE, UPDATE, INSERT, etc. sont interdites."
        )

    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
    except Exception as e:  # pragma: no cover - renvoi d'erreur simple
        return f"Erreur SQL : {e}"

    result_rows: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, sqlite3.Row):
            result_rows.append({k: r[k] for k in r.keys()})
        else:
            result_rows.append(dict(r))

    return {"row_count": len(result_rows), "rows": result_rows}


@mcp.tool()
def get_statistics(table_name: str, column: str) -> Dict[str, Any] | str:
    """Obtenir des statistiques simples sur une colonne d'une table.

    Calcule : count, min, max, mean (moyenne numérique si possible).

    Paramètres
    ----------
    table_name : str
        Nom de la table sur laquelle calculer les statistiques.
    column : str
        Nom de la colonne ciblée.
    """

    try:
        sql = (
            f'SELECT COUNT("{column}") AS count, '
            f'MIN("{column}") AS min, '
            f'MAX("{column}") AS max, '
            f'AVG(CAST("{column}" AS REAL)) AS mean '
            f'FROM "{table_name}"'
        )
        cur = conn.execute(sql)
        row = cur.fetchone()
        if row is None:
            return "Aucune donnée retournée pour cette colonne."
        return {
            "table": table_name,
            "column": column,
            "count": row["count"],
            "min": row["min"],
            "max": row["max"],
            "mean": row["mean"],
        }
    except Exception as e:  # pragma: no cover
        return f"Erreur lors du calcul des statistiques : {e}"


# --- Resources ---

@mcp.resource("db://schema")
def db_schema() -> str:
    """Ressource MCP exposant le schéma de la base au format JSON.

    Utile pour permettre au modèle d'inspecter les tables disponibles avant
    de construire des requêtes SQL complexes.
    """

    try:
        schema = _describe_schema()
        return json.dumps(schema, ensure_ascii=False, indent=2)
    except Exception as e:  # pragma: no cover
        return f"Erreur lors de la génération du schéma JSON : {e}"


# --- Prompts ---

@mcp.prompt()
def data_query_assistant() -> str:
    """Prompt système pour guider l'IA dans l'utilisation des outils de données."""
    return (
        "Vous êtes un assistant expert en analyse de données SQL. "
        "Votre rôle est d'aider l'utilisateur à explorer des fichiers CSV, "
        "à les charger dans une base de données SQLite temporaire et à effectuer des analyses.\n\n"
        "Directives :\n"
        "1. Commencez par explorer les fichiers disponibles si nécessaire.\n"
        "2. Utilisez 'load_csv' pour charger les données dans des tables nommées de manière pertinente.\n"
        "3. Utilisez 'describe_schema' ou 'list_tables' pour comprendre la structure des données chargées.\n"
        "4. Pour les analyses, privilégiez 'run_query' avec du SQL standard (SELECT uniquement).\n"
        "5. Vous pouvez utiliser 'get_statistics' pour un aperçu rapide d'une colonne numérique.\n"
        "6. Soyez précis dans vos requêtes et expliquez vos résultats de manière pédagogique.\n"
        "7. En cas d'erreur, vérifiez les noms de colonnes et les types via le schéma."
    )


# --- Start ---

if __name__ == "__main__":
    mcp.run()

