# NOTES — Bug fixes & verification (English)

Surplus-food marketplace coding challenge. All 6 intentional bugs (BE‑1…BE‑4, FE‑1, FE‑2)
were located, fixed, and verified. This file explains each fix (**before → after** code)
and gives step‑by‑step verification for both **curl** and the **UI**.

## Environment used

| Component | Version / note |
|-----------|----------------|
| Python | 3.14.0 (venv at `BE/.venv`) |
| Backend deps | FastAPI 0.141.1, uvicorn 0.52.4, pydantic 2.13.5 |
| Node / npm | v24.11.1 / 11.6.4 |
| Frontend | React 19 + Vite 6 |

Run the stack:

```bash
# Backend  (from BE/)
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
#   → http://127.0.0.1:8000  ·  docs at /docs

# Frontend (from FE/)
npm run dev
#   → http://localhost:5173   (use "localhost", not 127.0.0.1 — Vite binds ::1)
```

`POST /v1/th/dev/reset` restores seed data before each test.

---

## Summary of fixes

| ID | File | Root cause | Change (before → after) |
|----|------|-----------|--------------------------|
| BE‑1 | `BE/app/services/order.py` | `lines[0].model_dump()` returns snake_case keys; code read `first_line["mealId"]` → `KeyError` → HTTP 500 | `lines[0].model_dump()` / `first_line["mealId"]` → `lines[0]` / `first_line.meal_id` |
| BE‑2 | `BE/app/services/cart.py` | Cart priced lines from the original price | `unit_price = meal.original_price` → `meal.discounted_price` |
| BE‑3 | `BE/app/services/order.py` | Cancel restocked a hard‑coded `1` per line | `quantity=1` → `quantity=line.quantity` |
| BE‑4 | `BE/app/services/cart.py` | Increasing a cart line *released* stock instead of reserving | on `delta > 0`: `event_type=StockEventType.INCREMENT` → `StockEventType.DECREMENT` |
| FE‑1 | `FE/src/pages/MealsPage.tsx` | "You pay" rendered the original price | `<strong className="pay">{formatBaht(meal.original_price)}</strong>` → `{formatBaht(meal.discounted_price)}` |
| FE‑2 | `FE/src/api/client.ts` | Wrong query‑param name | `` `?meal=${...}` `` → `` `?meal_id=${...}` `` |

---

## BE‑1 — Exception on checkout

**Was:** with items in the cart, `POST /v1/th/orders` returned **500**
(`KeyError: 'mealId'` in `create_from_cart`) — `OrderLine` has no alias `mealId`, so
`model_dump()` returns the key `meal_id`.

**Before** (`BE/app/services/order.py` — `create_from_cart`):

```python
# Attach store metadata for receipt / downstream notifications.
first_line = lines[0].model_dump()
meal = self.db.meals[first_line["mealId"]]      # ← KeyError: 'mealId' → HTTP 500
_ = meal.store_id
```

**After:**

```python
# Attach store metadata for receipt / downstream notifications.
first_line = lines[0]
meal = self.db.meals[first_line.meal_id]        # read the pydantic model field directly
_ = meal.store_id
```

> The rest of `create_from_cart()` was already correct (creates a `CONFIRMED` order,
> then calls `self.cart.clear(user_id, release_stock=False)`) — only this line 500'd.

### Verify — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":2}"

# expect HTTP 201, order.status = "CONFIRMED"
curl -s -w "\nHTTP %{http_code}\n" -X POST http://127.0.0.1:8000/v1/th/orders

curl -s http://127.0.0.1:8000/v1/th/cart      # items: []  , item_count: 0
curl -s http://127.0.0.1:8000/v1/th/meals     # meal_1 stock_available: 8  (NOT back to 10)
curl -s "http://127.0.0.1:8000/v1/th/stock-events?meal_id=meal_1"
# exactly one event: DECREMENT 2 "reserve on add-to-cart" — no second decrement, no release
```

### Verify — UI

1. **Meals** → *Add to cart* on *Surplus Biriyani Bowl*.
2. **Cart** → *Place order*.
3. Expect: no error banner; order appears with status `CONFIRMED`; cart is empty.
4. **Meals** → stock did **not** increase back.

---

## BE‑2 — Logical pricing bug

**Was:** cart `unit_price` / `line_total` / `subtotal` were computed from `original_price`,
though customers pay `discounted_price` (`meal_1 ×2` gave `360` instead of `158`).

**Before** (`BE/app/services/cart.py` — `get_cart`):

```python
for meal_id, quantity in raw.items():
    meal = self.meals.get_meal(meal_id)
    unit_price = meal.original_price            # ← full price
    line_total = unit_price * quantity
```

**After:**

```python
for meal_id, quantity in raw.items():
    meal = self.meals.get_meal(meal_id)
    # Customers pay the surplus discounted price, not the original.
    unit_price = meal.discounted_price          # ← discounted price
    line_total = unit_price * quantity
```

### Verify — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":2}"
# expect: unit_price 79, line_total 158, subtotal 158
```

### Verify — UI

1. **Meals** → *Add to cart* on *Surplus Biriyani Bowl* twice (qty 2).
2. **Cart** → line shows `฿79` unit, `฿158` line total, subtotal `฿158`.

---

## BE‑3 — Inventory bug on cancel

**Was:** cancel iterated every order line but restocked a fixed `quantity=1`, so a
3‑unit order only returned 1 unit (`meal_2` stock came back as `3`, not `5`).

**Before** (`BE/app/services/order.py` — `cancel`):

```python
# Restore reserved/sold stock back to the meal.
for line in order.lines:
    self.stock.apply(
        meal_id=line.meal_id,
        quantity=1,                             # ← always 1, ignores the real quantity
        event_type=StockEventType.INCREMENT,
        event_source=StockEventSource.SYSTEM,
        reference_id=order.id,
        note=f"restore on cancel {order.order_number}",
    )
```

**After:**

```python
# Restore reserved/sold stock back to the meal.
for line in order.lines:
    self.stock.apply(
        meal_id=line.meal_id,
        quantity=line.quantity,                 # ← restore the line's real quantity
        event_type=StockEventType.INCREMENT,
        event_source=StockEventSource.SYSTEM,
        reference_id=order.id,
        note=f"restore on cancel {order.order_number}",
    )
```

### Verify — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_2\",\"quantity\":3}"

OID=$(curl -s -X POST http://127.0.0.1:8000/v1/th/orders \
  | python -c "import sys,json;print(json.load(sys.stdin)['order']['id'])")

curl -s http://127.0.0.1:8000/v1/th/meals      # meal_2 stock_available: 2

curl -s -X POST "http://127.0.0.1:8000/v1/th/orders/$OID/cancel"

curl -s http://127.0.0.1:8000/v1/th/meals      # meal_2 stock_available: 5  (fully restored)
```

### Verify — UI

1. **Meals** → add *Chicken Rice Box* ×3 (add three times). Stock shows `2`.
2. **Cart** → *Place order*.
3. **Orders** → *Cancel* that order.
4. **Meals** → *Chicken Rice Box* stock is back to `5`.

---

## BE‑4 — Inventory bug on cart quantity increase

**Was:** raising a cart line's quantity (`delta > 0`) called `stock.apply(..., INCREMENT)`,
which *released* stock instead of *reserving* more. Increasing `meal_1` 1 → 3 pushed
stock to `11` (correct is `7`).

**Before** (`BE/app/services/cart.py` — `update_item`):

```python
if delta > 0:
    self.stock.apply(
        meal_id=meal_id,
        quantity=delta,
        event_type=StockEventType.INCREMENT,    # ← wrong: increasing qty must reserve stock
        event_source=StockEventSource.USER,
        reference_id=f"cart:{user_id}",
        note="reserve on cart increase",
    )
elif delta < 0:
    self.stock.apply(
        ...
        event_type=StockEventType.INCREMENT,    # (decreasing qty = release; already correct)
        note="release on cart decrease",
    )
```

**After:**

```python
if delta > 0:
    # Increasing the cart line reserves additional units.
    self.stock.apply(
        meal_id=meal_id,
        quantity=delta,
        event_type=StockEventType.DECREMENT,    # ← reserve the extra units
        event_source=StockEventSource.USER,
        reference_id=f"cart:{user_id}",
        note="reserve on cart increase",
    )
elif delta < 0:
    self.stock.apply(
        ...
        event_type=StockEventType.INCREMENT,    # unchanged: decreasing qty = release
        note="release on cart decrease",
    )
```

### Verify — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":1}"
curl -s http://127.0.0.1:8000/v1/th/meals       # meal_1 stock_available: 9

curl -s -X PATCH http://127.0.0.1:8000/v1/th/cart/items/meal_1 \
  -H "Content-Type: application/json" -d "{\"quantity\":3}"
curl -s http://127.0.0.1:8000/v1/th/meals       # meal_1 stock_available: 7

curl -s "http://127.0.0.1:8000/v1/th/stock-events?meal_id=meal_1"
# two DECREMENT events: qty 1 "reserve on add-to-cart", qty 2 "reserve on cart increase"
```

### Verify — UI

1. **Meals** → add *Surplus Biriyani Bowl* ×1. Stock shows `9`.
2. **Cart** → change its quantity to `3`.
3. **Meals** → stock now shows `7` (not `11`).
4. **Stock events** → two `DECREMENT` rows for `meal_1` (qty 1, then qty 2).

---

## FE‑1 — Wrong "You pay" price

**Was:** `MealsPage.tsx` printed `meal.original_price` for the pay amount, so the
struck‑through price and the pay price were identical.

**Before** (`FE/src/pages/MealsPage.tsx`):

```tsx
<div className="meal-price">
  <span className="strike">{formatBaht(meal.original_price)}</span>
  <strong className="pay">{formatBaht(meal.original_price)}</strong>   {/* ← full price */}
```

**After:**

```tsx
<div className="meal-price">
  <span className="strike">{formatBaht(meal.original_price)}</span>
  <strong className="pay">{formatBaht(meal.discounted_price)}</strong> {/* ← discounted */}
```

### Verify — UI

Open **Meals** (http://localhost:5173). Each card shows the original price struck
through and the discounted price as the bold "pay" amount:

| Meal | Struck | You pay |
|------|--------|---------|
| Surplus Biriyani Bowl | ฿180 | **฿79** |
| Chicken Rice Box | ฿120 | **฿55** |
| Assorted Pastry Pack | ฿250 | **฿99** |

### Verify — curl (data behind it)

```bash
curl -s http://127.0.0.1:8000/v1/th/meals
# meal_1: original_price 180, discounted_price 79 → UI "pay" must read 79
```

---

## FE‑2 — Stock events filter returns everything

**Was:** `client.ts` built the query string as `?meal=<id>`; the FastAPI route
parameter (`BE/app/api/stock.py`) is `meal_id`, so the filter was silently ignored and
every event came back.

**Before** (`FE/src/api/client.ts` — `listStockEvents`):

```ts
listStockEvents: (meal_id?: string) => {
  const q = meal_id ? `?meal=${encodeURIComponent(meal_id)}` : "";   // ← wrong param name
  return request<StockEvent[]>(`/stock-events${q}`);
},
```

**After:**

```ts
listStockEvents: (meal_id?: string) => {
  const q = meal_id ? `?meal_id=${encodeURIComponent(meal_id)}` : ""; // ← matches backend
  return request<StockEvent[]>(`/stock-events${q}`);
},
```

### Verify — curl (API contract)

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset
curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":1}"
curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_2\",\"quantity\":2}"

curl -s "http://127.0.0.1:8000/v1/th/stock-events"              # 2 events (meal_1, meal_2)
curl -s "http://127.0.0.1:8000/v1/th/stock-events?meal_id=meal_1"  # 1 event, meal_1 only
```

### Verify — UI

1. **Stock events** — generate a few events first (add meal_1 and meal_2 to cart).
2. Type `meal_1` in the *Filter by meal_id* box → *Apply filter*.
3. Only `meal_1` rows remain. *Clear* → all rows return.

---

## Test results (observed)

| Check | Before | After |
|-------|--------|-------|
| BE‑1 `POST /orders` | HTTP 500 | **HTTP 201**, status `CONFIRMED`, cart emptied, stock stays 8 |
| BE‑2 `meal_1 ×2` subtotal | 360 | **158** (unit 79) |
| BE‑3 cancel `meal_2 ×3` | stock 2 → 3 | stock 2 → **5** |
| BE‑4 cart `meal_1` 1→3 | stock 11 | stock **7**, two DECREMENT events |
| FE‑1 "You pay" | ฿180 | **฿79** (฿180 struck) |
| FE‑2 filter `?meal_id=meal_1` | all events | **only meal_1** events |

> Backend checks were run end‑to‑end with curl against a fresh server.
> FE‑1 was confirmed visually in the browser. FE‑2 was confirmed via the API
> contract and the one‑line client change (`tsc --noEmit` passes).
