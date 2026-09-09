# Coding Challenge

Surplus-food marketplace with a FastAPI backend and a React frontend. The repo has intentional bugs — find them, fix them, then write a short approach note for each task.

| Folder | Stack |
|--------|--------|
| `BE/` | Python 3.11+, FastAPI |
| `FE/` | React + TypeScript + Vite |

**Domain**

- **Meal** — `original_price`, `discounted_price`, `stock_available`
- **Cart** — adding an item reserves stock (DECREMENT). Clearing without checkout releases it.
- **Order** — checkout converts the cart. Stock was already reserved, so checkout must not decrement again.
- **Stock event** — INCREMENT / DECREMENT audit trail

API base path: `/v1/th/...`

---

## Setup

### Backend

```bash
cd BE
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Docs: http://127.0.0.1:8000/docs
- Reset seed data: `POST /v1/th/dev/reset`

### Frontend

```bash
cd FE
npm install
npm run dev
```

Open http://127.0.0.1:5173 (proxies `/v1` to port 8000).

---

## Seed data

| Meal ID | Name | Original | Discounted | Stock |
|---------|------|----------|------------|-------|
| `meal_1` | Surplus Biriyani Bowl | ฿180 | ฿79 | 10 |
| `meal_2` | Chicken Rice Box | ฿120 | ฿55 | 5 |
| `meal_3` | Assorted Pastry Pack | ฿250 | ฿99 | 8 |
| `meal_4` | Sandwich Surprise | unpublished | — | 3 |

Demo user: `user_demo_1`

---

## Tasks

### Backend

#### BE-1 — Exception on checkout

With items in the cart, `POST /v1/th/orders` (or **Place order**) returns **500**.

Fix checkout so it succeeds, empties the cart, and does **not** release reserved stock back to the meal.

#### BE-2 — Logical pricing bug

Customers should pay `discounted_price`. Cart `unit_price` / `line_total` / `subtotal` must use that value.

Example: `meal_1` × 2 → subtotal should be `158`.

#### BE-3 — Logical inventory bug on cancel

Cancel sets status to `CANCELLED`, but stock is wrong afterward.

1. `POST /v1/th/dev/reset`
2. Add `meal_2` quantity **3**, place order
3. Stock for `meal_2` should be `2`
4. Cancel the order — stock should return to `5`

#### BE-4 — Logical inventory bug on cart quantity increase

Increasing quantity for an item already in the cart does not reserve additional stock correctly.

1. `POST /v1/th/dev/reset`
2. Add `meal_1` quantity **1** (stock should become `9`)
3. Update that cart line to quantity **3** (stock should become `7`)
4. Observe actual stock and stock events

### Frontend

#### FE-1 — Wrong “You pay” price

Meals page should show `discounted_price` as the pay amount (original stays struck through).

#### FE-2 — Stock events filter

Filtering by `meal_id` on Stock events still returns every event. Fix it.

---

## Write-up

Create `NOTES.md` and briefly explain how you approached each task (what you checked, what was wrong, what you changed).

---

## Curl examples

```bash
curl -s http://127.0.0.1:8000/v1/th/meals | python -m json.tool

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" \
  -d "{\"meal_id\":\"meal_1\",\"quantity\":2}" | python -m json.tool

curl -s -X POST http://127.0.0.1:8000/v1/th/orders | python -m json.tool

curl -s http://127.0.0.1:8000/v1/th/stock-events | python -m json.tool

curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset
```
