"""
What To Eat!! — Flask backend.

Implements the application functional design from the project report:
  * Fridge management  — view contents, buy / use ingredients, cook a recipe
  * Recipes            — ingredients per recipe, recommendation by inventory
  * Meal options       — browse by preference (cuisine / mood / eat-out)
  * Restaurants        — browse by preference, view menus with prices
  * RBAC               — admins manage ingredients/options/recipes;
                         general users manage only their own fridge

Run:
    pip install -r requirements.txt
    mysql -u root -p < database/schema.sql
    mysql -u root -p what_to_eat < database/seed.sql
    DB_USER=root DB_PASSWORD=secret python backend/app.py

Role based access: pass the caller's role in the `X-User-Role` header
(`admin` or `general`). Defaults to `general`.
"""

import os
from functools import wraps

from flask import Flask, g, jsonify, request
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "what_to_eat"),
}


# ----------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=()):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def execute(sql, params=()):
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


# ----------------------------------------------------------------------
# Simple role-based access control
# ----------------------------------------------------------------------

def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = request.headers.get("X-User-Role", "general")
            if role not in roles:
                return jsonify({"error": f"forbidden: requires role(s) {roles}"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ----------------------------------------------------------------------
# Fridge — check & edit contents
# ----------------------------------------------------------------------

@app.get("/api/fridge")
def fridge_contents():
    """All ingredients currently in the fridge, with quantities."""
    rows = query(
        """
        SELECT i.IngrdID AS ingredient_id, i.IngrdName AS name, f.Qty AS quantity
        FROM Fridge f JOIN Ingredient i ON f.IngrdID = i.IngrdID
        ORDER BY i.IngrdName
        """
    )
    return jsonify(rows)


@app.post("/api/fridge/buy")
def fridge_buy():
    """Add an ingredient (and quantity) to the fridge."""
    data = request.get_json(force=True)
    ingrd_id, qty = data["ingredient_id"], float(data["quantity"])
    if qty < 0:
        return jsonify({"error": "quantity must be non-negative"}), 400
    execute(
        """
        INSERT INTO Fridge (IngrdID, Qty) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE Qty = Qty + VALUES(Qty)
        """,
        (ingrd_id, qty),
    )
    return jsonify({"ingredient_id": ingrd_id, "added": qty}), 201


@app.post("/api/fridge/use")
def fridge_use():
    """Consume a quantity of an ingredient from the fridge."""
    data = request.get_json(force=True)
    ingrd_id, qty = data["ingredient_id"], float(data["quantity"])
    if qty < 0:
        return jsonify({"error": "quantity must be non-negative"}), 400
    row = query("SELECT Qty FROM Fridge WHERE IngrdID = %s", (ingrd_id,))
    if not row or row[0]["Qty"] < qty:
        return jsonify({"error": "not enough of this ingredient in the fridge"}), 400
    execute("UPDATE Fridge SET Qty = Qty - %s WHERE IngrdID = %s", (qty, ingrd_id))
    return jsonify({"ingredient_id": ingrd_id, "used": qty})


@app.post("/api/fridge/cook")
def fridge_cook():
    """Cook a recipe: deduct every required ingredient from the fridge.

    Fails (with 400) if any non-optional ingredient is short.
    """
    opt_id = request.get_json(force=True)["option_id"]
    recipe = query(
        """
        SELECT r.IngrdID, r.Qty AS needed, r.Optional,
               i.IngrdName, COALESCE(f.Qty, 0) AS have
        FROM Recipe r
        JOIN Ingredient i ON r.IngrdID = i.IngrdID
        LEFT JOIN Fridge f ON f.IngrdID = r.IngrdID
        WHERE r.OptID = %s
        """,
        (opt_id,),
    )
    if not recipe:
        return jsonify({"error": "unknown option_id"}), 404
    missing = [r for r in recipe if not r["Optional"] and r["have"] < r["needed"]]
    if missing:
        return jsonify({
            "error": "missing ingredients",
            "missing": [{"ingredient": r["IngrdName"],
                         "needed": float(r["needed"]),
                         "have": float(r["have"])} for r in missing],
        }), 400
    db = get_db()
    cur = db.cursor()
    for r in recipe:
        if r["have"] > 0:
            take = min(float(r["needed"]), float(r["have"]))
            cur.execute("UPDATE Fridge SET Qty = Qty - %s WHERE IngrdID = %s",
                        (take, r["IngrdID"]))
    db.commit()
    cur.close()
    return jsonify({"option_id": opt_id, "cooked": True})


# ----------------------------------------------------------------------
# Recipes & meal options
# ----------------------------------------------------------------------

@app.get("/api/recipes/<int:opt_id>")
def recipe_detail(opt_id):
    """Ingredients needed for one recipe, plus whether the fridge covers it."""
    rows = query(
        """
        SELECT i.IngrdID AS ingredient_id, i.IngrdName AS name,
               r.Qty AS quantity_needed, r.Optional AS optional,
               COALESCE(f.Qty, 0) AS in_fridge
        FROM Recipe r
        JOIN Ingredient i ON r.IngrdID = i.IngrdID
        LEFT JOIN Fridge f ON f.IngrdID = r.IngrdID
        WHERE r.OptID = %s
        """,
        (opt_id,),
    )
    if not rows:
        return jsonify({"error": "unknown option_id"}), 404
    can_make = all(r["optional"] or r["in_fridge"] >= r["quantity_needed"] for r in rows)
    return jsonify({"option_id": opt_id, "can_make": can_make, "ingredients": rows})


@app.get("/api/options")
def list_options():
    """Browse meal options, filterable by cuisine, mood, eat_out."""
    clauses, params = [], []
    if "cuisine" in request.args:
        clauses.append("CuisineType = %s"); params.append(request.args["cuisine"])
    if "mood" in request.args:
        clauses.append("Mood = %s"); params.append(request.args["mood"])
    if "eat_out" in request.args:
        clauses.append("EatOut = %s")
        params.append(request.args["eat_out"].lower() in ("1", "true", "yes"))
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = query(
        f"""SELECT OptID AS option_id, MealName AS name, EatOut AS eat_out,
                   CuisineType AS cuisine, Mood AS mood
            FROM `Option` {where} ORDER BY MealName""",
        tuple(params),
    )
    return jsonify(rows)


@app.post("/api/options/recommend")
def recommend_option():
    """Recommend cook-at-home meals ranked by % of ingredients on hand."""
    options = query(
        "SELECT OptID, MealName FROM `Option` WHERE EatOut = FALSE")
    ranked = []
    for o in options:
        recipe = query(
            """
            SELECT r.Qty AS needed, r.Optional, COALESCE(f.Qty, 0) AS have
            FROM Recipe r LEFT JOIN Fridge f ON f.IngrdID = r.IngrdID
            WHERE r.OptID = %s
            """,
            (o["OptID"],),
        )
        required = [r for r in recipe if not r["Optional"]]
        if not required:
            continue
        covered = sum(1 for r in required if r["have"] >= r["needed"])
        ranked.append({
            "option_id": o["OptID"],
            "name": o["MealName"],
            "coverage": round(covered / len(required), 2),
            "ready_to_cook": covered == len(required),
        })
    ranked.sort(key=lambda r: r["coverage"], reverse=True)
    return jsonify(ranked)


# ----------------------------------------------------------------------
# Restaurants & menus
# ----------------------------------------------------------------------

@app.get("/api/restaurants")
def list_restaurants():
    """Restaurants whose menus match the given cuisine / mood preference."""
    clauses, params = [], []
    if "cuisine" in request.args:
        clauses.append("o.CuisineType = %s"); params.append(request.args["cuisine"])
    if "mood" in request.args:
        clauses.append("o.Mood = %s"); params.append(request.args["mood"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = query(
        f"""SELECT DISTINCT r.RstrntID AS restaurant_id, r.RstrntName AS name
            FROM Restaurant r
            JOIN Menu m ON m.RstrntID = r.RstrntID
            JOIN `Option` o ON o.OptID = m.OptID {where}
            ORDER BY r.RstrntName""",
        tuple(params),
    )
    return jsonify(rows)


@app.get("/api/restaurants/<int:rstrnt_id>/menu")
def restaurant_menu(rstrnt_id):
    """Meal options a restaurant serves, with prices."""
    rows = query(
        """
        SELECT o.OptID AS option_id, o.MealName AS name,
               o.CuisineType AS cuisine, o.Mood AS mood, m.Price AS price
        FROM Menu m JOIN `Option` o ON o.OptID = m.OptID
        WHERE m.RstrntID = %s ORDER BY o.MealName
        """,
        (rstrnt_id,),
    )
    return jsonify(rows)


# ----------------------------------------------------------------------
# Admin — manage ingredients, options, recipes (admin role only)
# ----------------------------------------------------------------------

@app.post("/api/admin/ingredients")
@require_role("admin")
def admin_add_ingredient():
    name = request.get_json(force=True)["name"]
    new_id = execute("INSERT INTO Ingredient (IngrdName) VALUES (%s)", (name,))
    return jsonify({"ingredient_id": new_id, "name": name}), 201


@app.delete("/api/admin/ingredients/<int:ingrd_id>")
@require_role("admin")
def admin_delete_ingredient(ingrd_id):
    execute("DELETE FROM Ingredient WHERE IngrdID = %s", (ingrd_id,))
    return jsonify({"deleted": ingrd_id})


@app.post("/api/admin/options")
@require_role("admin")
def admin_add_option():
    d = request.get_json(force=True)
    new_id = execute(
        "INSERT INTO `Option` (MealName, EatOut, CuisineType, Mood)"
        " VALUES (%s, %s, %s, %s)",
        (d["name"], bool(d.get("eat_out", False)),
         d.get("cuisine"), d.get("mood")),
    )
    return jsonify({"option_id": new_id}), 201


@app.put("/api/admin/options/<int:opt_id>")
@require_role("admin")
def admin_update_option(opt_id):
    d = request.get_json(force=True)
    fields, params = [], []
    for col, key in [("MealName", "name"), ("EatOut", "eat_out"),
                     ("CuisineType", "cuisine"), ("Mood", "mood")]:
        if key in d:
            fields.append(f"{col} = %s"); params.append(d[key])
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    params.append(opt_id)
    execute(f"UPDATE `Option` SET {', '.join(fields)} WHERE OptID = %s",
            tuple(params))
    return jsonify({"updated": opt_id})


@app.delete("/api/admin/options/<int:opt_id>")
@require_role("admin")
def admin_delete_option(opt_id):
    execute("DELETE FROM `Option` WHERE OptID = %s", (opt_id,))
    return jsonify({"deleted": opt_id})


@app.post("/api/admin/recipes")
@require_role("admin")
def admin_add_recipe_row():
    d = request.get_json(force=True)
    if float(d["quantity"]) < 0:
        return jsonify({"error": "quantity must be non-negative"}), 400
    execute(
        "INSERT INTO Recipe (OptID, IngrdID, Qty, Optional) VALUES (%s, %s, %s, %s)",
        (d["option_id"], d["ingredient_id"], d["quantity"],
         bool(d.get("optional", False))),
    )
    return jsonify({"added": True}), 201


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
