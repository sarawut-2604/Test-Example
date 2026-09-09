# NOTES — การแก้บั๊กและวิธีตรวจสอบ (ภาษาไทย)

โจทย์ coding challenge ระบบตลาดอาหารส่วนเกิน (surplus-food marketplace)
บั๊กที่จงใจใส่ไว้ทั้ง 6 จุด (BE‑1…BE‑4, FE‑1, FE‑2) ถูกค้นหา แก้ไข และทดสอบครบแล้ว
ไฟล์นี้อธิบายการแก้แต่ละจุด (โค้ดเดิม → แก้เป็น) พร้อมขั้นตอนตรวจสอบทั้งแบบ **curl** และแบบ **UI**

## สภาพแวดล้อมที่ใช้

| ส่วนประกอบ | เวอร์ชัน / หมายเหตุ |
|-----------|----------------------|
| Python | 3.14.0 (virtualenv อยู่ที่ `BE/.venv`) |
| ไลบรารี backend | FastAPI 0.141.1, uvicorn 0.52.4, pydantic 2.13.5 |
| Node / npm | v24.11.1 / 11.6.4 |
| Frontend | React 19 + Vite 6 |

การรันระบบ:

```bash
# Backend  (จากโฟลเดอร์ BE/)
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
#   → http://127.0.0.1:8000  ·  เอกสาร API ที่ /docs

# Frontend (จากโฟลเดอร์ FE/)
npm run dev
#   → http://localhost:5173   (ใช้ "localhost" ไม่ใช่ 127.0.0.1 เพราะ Vite bind ที่ ::1)
```

เรียก `POST /v1/th/dev/reset` เพื่อคืนค่า seed data ก่อนทดสอบทุกครั้ง

---

## สรุปการแก้ไข

| รหัส | ไฟล์ | สาเหตุที่แท้จริง | สิ่งที่แก้ (เดิม → ใหม่) |
|------|------|------------------|--------------------------|
| BE‑1 | `BE/app/services/order.py` | `lines[0].model_dump()` คืนคีย์แบบ snake_case แต่โค้ดอ่าน `first_line["mealId"]` → `KeyError` → HTTP 500 | `lines[0].model_dump()` / `first_line["mealId"]` → `lines[0]` / `first_line.meal_id` |
| BE‑2 | `BE/app/services/cart.py` | ตะกร้าใช้ราคาเต็มเป็นราคาต่อหน่วย | `unit_price = meal.original_price` → `meal.discounted_price` |
| BE‑3 | `BE/app/services/order.py` | ตอน cancel คืนสต็อกแบบ fix ค่าไว้ที่ 1 ต่อบรรทัด | `quantity=1` → `quantity=line.quantity` |
| BE‑4 | `BE/app/services/cart.py` | เพิ่มจำนวนสินค้าในตะกร้ากลับ "คืน" สต็อกแทนที่จะ "จอง" เพิ่ม | เมื่อ `delta > 0`: `event_type=StockEventType.INCREMENT` → `StockEventType.DECREMENT` |
| FE‑1 | `FE/src/pages/MealsPage.tsx` | ราคา "You pay" แสดงราคาเต็ม | `<strong className="pay">{formatBaht(meal.original_price)}</strong>` → `{formatBaht(meal.discounted_price)}` |
| FE‑2 | `FE/src/api/client.ts` | ส่ง query param ผิดชื่อ | `` `?meal=${...}` `` → `` `?meal_id=${...}` `` |

---

## BE‑1 — checkout แล้ว exception

**อาการเดิม:** เมื่อมีของในตะกร้า `POST /v1/th/orders` ตอบ **500**
(`KeyError: 'mealId'` ในฟังก์ชัน `create_from_cart`) — เพราะ `OrderLine` ไม่มี alias ชื่อ
`mealId` ดังนั้น `model_dump()` จึงคืนคีย์เป็น `meal_id`

**โค้ดเดิม** (`BE/app/services/order.py` — `create_from_cart`):

```python
# Attach store metadata for receipt / downstream notifications.
first_line = lines[0].model_dump()
meal = self.db.meals[first_line["mealId"]]      # ← KeyError: 'mealId' → HTTP 500
_ = meal.store_id
```

**แก้เป็น:**

```python
# Attach store metadata for receipt / downstream notifications.
first_line = lines[0]
meal = self.db.meals[first_line.meal_id]        # อ่านจากฟิลด์ของ pydantic model ตรง ๆ
_ = meal.store_id
```

> ส่วนที่เหลือของ `create_from_cart()` ถูกต้องอยู่แล้ว (สร้างออเดอร์สถานะ `CONFIRMED`
> แล้วเรียก `self.cart.clear(user_id, release_stock=False)`) มีแค่บรรทัดนี้ที่ทำให้ 500

### ตรวจสอบ — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":2}"

# คาดหวัง HTTP 201, order.status = "CONFIRMED"
curl -s -w "\nHTTP %{http_code}\n" -X POST http://127.0.0.1:8000/v1/th/orders

curl -s http://127.0.0.1:8000/v1/th/cart      # items: []  , item_count: 0
curl -s http://127.0.0.1:8000/v1/th/meals     # meal_1 stock_available: 8  (ไม่เด้งกลับเป็น 10)
curl -s "http://127.0.0.1:8000/v1/th/stock-events?meal_id=meal_1"
# มี event เดียว: DECREMENT 2 "reserve on add-to-cart" — ไม่มีการตัดสต็อกซ้ำ ไม่มีการคืนสต็อก
```

### ตรวจสอบ — UI

1. หน้า **Meals** → กด *Add to cart* ที่ *Surplus Biriyani Bowl*
2. หน้า **Cart** → กด *Place order*
3. คาดหวัง: ไม่มีแถบ error, ออเดอร์ขึ้นสถานะ `CONFIRMED`, ตะกร้าว่าง
4. กลับหน้า **Meals** → สต็อก **ไม่** เพิ่มกลับ

---

## BE‑2 — บั๊กเชิงตรรกะเรื่องราคา

**อาการเดิม:** `unit_price` / `line_total` / `subtotal` ในตะกร้าคำนวณจาก `original_price`
ทั้งที่ลูกค้าต้องจ่าย `discounted_price` (เช่น `meal_1 ×2` ได้ยอด `360` แทนที่จะเป็น `158`)

**โค้ดเดิม** (`BE/app/services/cart.py` — `get_cart`):

```python
for meal_id, quantity in raw.items():
    meal = self.meals.get_meal(meal_id)
    unit_price = meal.original_price            # ← ใช้ราคาเต็ม
    line_total = unit_price * quantity
```

**แก้เป็น:**

```python
for meal_id, quantity in raw.items():
    meal = self.meals.get_meal(meal_id)
    # Customers pay the surplus discounted price, not the original.
    unit_price = meal.discounted_price          # ← ใช้ราคาส่วนลด
    line_total = unit_price * quantity
```

### ตรวจสอบ — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":2}"
# คาดหวัง: unit_price 79, line_total 158, subtotal 158
```

### ตรวจสอบ — UI

1. หน้า **Meals** → กด *Add to cart* ที่ *Surplus Biriyani Bowl* 2 ครั้ง (จำนวน 2)
2. หน้า **Cart** → บรรทัดแสดงราคาต่อหน่วย `฿79`, รวมบรรทัด `฿158`, ยอดรวม `฿158`

---

## BE‑3 — บั๊กสต็อกตอนยกเลิกออเดอร์

**อาการเดิม:** ตอน cancel วนทุกบรรทัดของออเดอร์แต่คืนสต็อกแค่ `quantity=1` เสมอ
ดังนั้นออเดอร์ 3 ชิ้นจะคืนกลับแค่ 1 ชิ้น (สต็อก `meal_2` กลับเป็น `3` แทนที่จะเป็น `5`)

**โค้ดเดิม** (`BE/app/services/order.py` — `cancel`):

```python
# Restore reserved/sold stock back to the meal.
for line in order.lines:
    self.stock.apply(
        meal_id=line.meal_id,
        quantity=1,                             # ← คืนแค่ 1 เสมอ ไม่สนจำนวนจริง
        event_type=StockEventType.INCREMENT,
        event_source=StockEventSource.SYSTEM,
        reference_id=order.id,
        note=f"restore on cancel {order.order_number}",
    )
```

**แก้เป็น:**

```python
# Restore reserved/sold stock back to the meal.
for line in order.lines:
    self.stock.apply(
        meal_id=line.meal_id,
        quantity=line.quantity,                 # ← คืนตามจำนวนจริงของบรรทัด
        event_type=StockEventType.INCREMENT,
        event_source=StockEventSource.SYSTEM,
        reference_id=order.id,
        note=f"restore on cancel {order.order_number}",
    )
```

### ตรวจสอบ — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_2\",\"quantity\":3}"

OID=$(curl -s -X POST http://127.0.0.1:8000/v1/th/orders \
  | python -c "import sys,json;print(json.load(sys.stdin)['order']['id'])")

curl -s http://127.0.0.1:8000/v1/th/meals      # meal_2 stock_available: 2

curl -s -X POST "http://127.0.0.1:8000/v1/th/orders/$OID/cancel"

curl -s http://127.0.0.1:8000/v1/th/meals      # meal_2 stock_available: 5  (คืนครบ)
```

### ตรวจสอบ — UI

1. หน้า **Meals** → เพิ่ม *Chicken Rice Box* ×3 (กด 3 ครั้ง) สต็อกแสดง `2`
2. หน้า **Cart** → กด *Place order*
3. หน้า **Orders** → กด *Cancel* ที่ออเดอร์นั้น
4. หน้า **Meals** → สต็อก *Chicken Rice Box* กลับมาเป็น `5`

---

## BE‑4 — บั๊กสต็อกตอนเพิ่มจำนวนสินค้าในตะกร้า

**อาการเดิม:** การเพิ่มจำนวนของบรรทัดในตะกร้า (`delta > 0`) เรียก `stock.apply(..., INCREMENT)`
ซึ่งเป็นการ *คืน* สต็อก แทนที่จะ *จอง* เพิ่ม การเพิ่ม `meal_1` จาก 1 → 3 จึงทำให้สต็อกเพิ่มเป็น `11`
(ที่ถูกคือ `7`)

**โค้ดเดิม** (`BE/app/services/cart.py` — `update_item`):

```python
if delta > 0:
    self.stock.apply(
        meal_id=meal_id,
        quantity=delta,
        event_type=StockEventType.INCREMENT,    # ← ผิด: เพิ่มจำนวน = ต้องจองสต็อกเพิ่ม
        event_source=StockEventSource.USER,
        reference_id=f"cart:{user_id}",
        note="reserve on cart increase",
    )
elif delta < 0:
    self.stock.apply(
        ...
        event_type=StockEventType.INCREMENT,    # (กรณีลดจำนวน = คืนสต็อก ถูกอยู่แล้ว)
        note="release on cart decrease",
    )
```

**แก้เป็น:**

```python
if delta > 0:
    # Increasing the cart line reserves additional units.
    self.stock.apply(
        meal_id=meal_id,
        quantity=delta,
        event_type=StockEventType.DECREMENT,    # ← จองสต็อกเพิ่มตามส่วนต่าง
        event_source=StockEventSource.USER,
        reference_id=f"cart:{user_id}",
        note="reserve on cart increase",
    )
elif delta < 0:
    self.stock.apply(
        ...
        event_type=StockEventType.INCREMENT,    # คงเดิม: ลดจำนวน = คืนสต็อก
        note="release on cart decrease",
    )
```

### ตรวจสอบ — curl

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset

curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":1}"
curl -s http://127.0.0.1:8000/v1/th/meals       # meal_1 stock_available: 9

curl -s -X PATCH http://127.0.0.1:8000/v1/th/cart/items/meal_1 \
  -H "Content-Type: application/json" -d "{\"quantity\":3}"
curl -s http://127.0.0.1:8000/v1/th/meals       # meal_1 stock_available: 7

curl -s "http://127.0.0.1:8000/v1/th/stock-events?meal_id=meal_1"
# มี DECREMENT 2 รายการ: qty 1 "reserve on add-to-cart", qty 2 "reserve on cart increase"
```

### ตรวจสอบ — UI

1. หน้า **Meals** → เพิ่ม *Surplus Biriyani Bowl* ×1 สต็อกแสดง `9`
2. หน้า **Cart** → เปลี่ยนจำนวนเป็น `3`
3. หน้า **Meals** → สต็อกแสดง `7` (ไม่ใช่ `11`)
4. หน้า **Stock events** → มีแถว `DECREMENT` ของ `meal_1` 2 แถว (qty 1 แล้วตามด้วย qty 2)

---

## FE‑1 — ราคา "You pay" ผิด

**อาการเดิม:** `MealsPage.tsx` แสดง `meal.original_price` เป็นราคาที่ต้องจ่าย
ทำให้ราคาขีดฆ่ากับราคาที่จ่ายเป็นตัวเลขเดียวกัน

**โค้ดเดิม** (`FE/src/pages/MealsPage.tsx`):

```tsx
<div className="meal-price">
  <span className="strike">{formatBaht(meal.original_price)}</span>
  <strong className="pay">{formatBaht(meal.original_price)}</strong>   {/* ← ราคาเต็ม */}
```

**แก้เป็น:**

```tsx
<div className="meal-price">
  <span className="strike">{formatBaht(meal.original_price)}</span>
  <strong className="pay">{formatBaht(meal.discounted_price)}</strong> {/* ← ราคาส่วนลด */}
```

### ตรวจสอบ — UI

เปิดหน้า **Meals** (http://localhost:5173) แต่ละการ์ดแสดงราคาเต็มขีดฆ่า
และราคาส่วนลดเป็นตัวหนา (ราคาที่ต้องจ่าย):

| เมนู | ราคาขีดฆ่า | ราคาที่จ่าย |
|------|-----------|-------------|
| Surplus Biriyani Bowl | ฿180 | **฿79** |
| Chicken Rice Box | ฿120 | **฿55** |
| Assorted Pastry Pack | ฿250 | **฿99** |

### ตรวจสอบ — curl (ข้อมูลเบื้องหลัง)

```bash
curl -s http://127.0.0.1:8000/v1/th/meals
# meal_1: original_price 180, discounted_price 79 → UI ช่อง "pay" ต้องเป็น 79
```

---

## FE‑2 — ฟิลเตอร์ stock events ไม่กรอง

**อาการเดิม:** `client.ts` สร้าง query string เป็น `?meal=<id>` แต่พารามิเตอร์ของ
FastAPI route (`BE/app/api/stock.py`) ชื่อ `meal_id` ระบบจึงเพิกเฉยต่อฟิลเตอร์และคืน event ทั้งหมด

**โค้ดเดิม** (`FE/src/api/client.ts` — `listStockEvents`):

```ts
listStockEvents: (meal_id?: string) => {
  const q = meal_id ? `?meal=${encodeURIComponent(meal_id)}` : "";   // ← ชื่อพารามิเตอร์ผิด
  return request<StockEvent[]>(`/stock-events${q}`);
},
```

**แก้เป็น:**

```ts
listStockEvents: (meal_id?: string) => {
  const q = meal_id ? `?meal_id=${encodeURIComponent(meal_id)}` : ""; // ← ตรงกับ backend
  return request<StockEvent[]>(`/stock-events${q}`);
},
```

### ตรวจสอบ — curl (สัญญา API)

```bash
curl -s -X POST http://127.0.0.1:8000/v1/th/dev/reset
curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_1\",\"quantity\":1}"
curl -s -X POST http://127.0.0.1:8000/v1/th/cart/items \
  -H "Content-Type: application/json" -d "{\"meal_id\":\"meal_2\",\"quantity\":2}"

curl -s "http://127.0.0.1:8000/v1/th/stock-events"                 # 2 events (meal_1, meal_2)
curl -s "http://127.0.0.1:8000/v1/th/stock-events?meal_id=meal_1"  # 1 event เฉพาะ meal_1
```

### ตรวจสอบ — UI

1. หน้า **Stock events** — สร้าง event ก่อน (เพิ่ม meal_1 และ meal_2 ลงตะกร้า)
2. พิมพ์ `meal_1` ในช่อง *Filter by meal_id* → กด *Apply filter*
3. เหลือเฉพาะแถว `meal_1` กด *Clear* → แถวทั้งหมดกลับมา

---

## ผลการทดสอบ (ที่สังเกตได้จริง)

| จุดตรวจ | ก่อนแก้ | หลังแก้ |
|---------|---------|---------|
| BE‑1 `POST /orders` | HTTP 500 | **HTTP 201**, สถานะ `CONFIRMED`, ตะกร้าว่าง, สต็อกคงเป็น 8 |
| BE‑2 `meal_1 ×2` ยอดรวม | 360 | **158** (ต่อหน่วย 79) |
| BE‑3 cancel `meal_2 ×3` | สต็อก 2 → 3 | สต็อก 2 → **5** |
| BE‑4 ตะกร้า `meal_1` 1→3 | สต็อก 11 | สต็อก **7**, มี DECREMENT 2 รายการ |
| FE‑1 "You pay" | ฿180 | **฿79** (฿180 ขีดฆ่า) |
| FE‑2 ฟิลเตอร์ `?meal_id=meal_1` | ทุก event | **เฉพาะ event ของ meal_1** |

> ฝั่ง backend ทดสอบแบบ end‑to‑end ด้วย curl กับ server ที่รันใหม่
> FE‑1 ยืนยันด้วยสายตาในเบราว์เซอร์ ส่วน FE‑2 ยืนยันผ่านสัญญา API และการแก้โค้ด
> client แค่บรรทัดเดียว (`tsc --noEmit` ผ่าน)
