# What To Eat!!

Deciding what to eat is a daily time-sink: forgotten fridge contents, no
recipe ideas, and endless restaurant scrolling. **What To Eat** is a
full-stack app that fixes all three — track what's in your fridge, get recipe
suggestions matched to your inventory and taste, and browse curated
restaurant menus when you'd rather eat out.

Group 10, UIUC database course — Sylvey Lin, Ming-Lun Chen, Yi-Han Huang,
Zih-Yi Cao.

## Architecture

```
database/schema.sql   MySQL 8 schema — 7 tables, BCNF-normalized
database/seed.sql     Sample data so the app runs out of the box
backend/app.py        Flask 3 REST API (JSON)
reports/What_To_Eat.pdf  Original design report (E-R, schema, security)
```

## Database design

Six normalized tables plus a `Users` table for role-based access control:

| Table | Role |
|---|---|
| `Ingredient` | Ingredient catalog (`AUTO_INCREMENT` PK) |
| `Option` | Meal choices: name, cuisine, mood, eat-in vs eat-out |
| `Restaurant` | Restaurant directory |
| `Fridge` | User's current inventory → quantity per ingredient |
| `Recipe` | Which ingredients (and how much) each meal needs; flags optional ones |
| `Menu` | Which restaurants serve which meals, at what price |
| `Users` | `admin` / `general` roles |

Integrity enforced in the schema, not just the app:
- **Entity integrity** — `AUTO_INCREMENT` primary keys everywhere.
- **Referential integrity** — foreign keys with `ON DELETE CASCADE` / `RESTRICT`
  (e.g. you can't stock a fridge with an ingredient that doesn't exist).
- **User-defined integrity** — `CHECK (Qty >= 0)` on quantities and prices.
- **BCNF** — every determinant is a candidate key; no partial or transitive
  dependencies.

## API

**Fridge**
- `GET /api/fridge` — current contents
- `POST /api/fridge/buy` `{ingredient_id, quantity}` — stock up
- `POST /api/fridge/use` `{ingredient_id, quantity}` — consume
- `POST /api/fridge/cook` `{option_id}` — cook a recipe; deducts ingredients
  atomically, fails with a clear error if anything's missing

**Recipes & options**
- `GET /api/recipes/<option_id>` — ingredients needed + whether you can make it
- `GET /api/options?cuisine=…&mood=…&eat_out=…` — browse by preference
- `POST /api/options/recommend` — ranks cook-at-home meals by % of ingredients
  already in your fridge

**Restaurants**
- `GET /api/restaurants?cuisine=…&mood=…` — places matching your preference
- `GET /api/restaurants/<id>/menu` — what they serve, at what price

**Admin** (pass `X-User-Role: admin` header)
- `POST /api/admin/ingredients`, `DELETE /api/admin/ingredients/<id>`
- `POST /api/admin/options`, `PUT /api/admin/options/<id>`,
  `DELETE /api/admin/options/<id>`
- `POST /api/admin/recipes`

## Run it

```bash
pip install -r requirements.txt
mysql -u root -p < database/schema.sql
mysql -u root -p what_to_eat < database/seed.sql
DB_USER=root DB_PASSWORD=yourpassword python backend/app.py
```

Then, e.g.:

```bash
curl localhost:5000/api/fridge
curl -X POST localhost:5000/api/options/recommend
curl "localhost:5000/api/restaurants?mood=fun"
```
