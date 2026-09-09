/** API client for the FastAPI backend (via Vite proxy). */

const REGION = "th";
const BASE = `/v1/${REGION}`;

export type Meal = {
  id: string;
  store_id: string;
  name: string;
  description: string;
  original_price: number;
  discounted_price: number;
  stock_available: number;
  is_published: boolean;
};

export type CartItem = {
  meal_id: string;
  quantity: number;
  unit_price: number;
  meal_name: string;
  line_total: number;
};

export type Cart = {
  user_id: string;
  items: CartItem[];
  item_count: number;
  subtotal: number;
};

export type OrderLine = {
  meal_id: string;
  meal_name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
};

export type Order = {
  id: string;
  order_number: string;
  user_id: string;
  status: "PENDING" | "CONFIRMED" | "COMPLETED" | "CANCELLED";
  lines: OrderLine[];
  subtotal: number;
  created_at: string;
  updated_at: string;
};

export type StockEvent = {
  id: string;
  meal_id: string;
  store_id: string;
  event_type: "INCREMENT" | "DECREMENT";
  event_source: "USER" | "MERCHANT" | "SYSTEM";
  quantity: number;
  stock_before: number;
  stock_after: number;
  reference_id: string | null;
  note: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = await res.json();
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  listMeals: (publishedOnly = true) =>
    request<Meal[]>(`/meals?published_only=${publishedOnly}`),

  addToCart: (meal_id: string, quantity = 1) =>
    request<Cart>("/cart/items", {
      method: "POST",
      body: JSON.stringify({ meal_id, quantity }),
    }),

  getCart: () => request<Cart>("/cart"),

  updateCartItem: (meal_id: string, quantity: number) =>
    request<Cart>(`/cart/items/${meal_id}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    }),

  clearCart: () => request<Cart>("/cart", { method: "DELETE" }),

  listOrders: () => request<Order[]>("/orders"),

  createOrder: () => request<{ order: Order; message: string }>("/orders", { method: "POST" }),

  cancelOrder: (order_id: string) =>
    request<Order>(`/orders/${order_id}/cancel`, { method: "POST" }),

  completeOrder: (order_id: string) =>
    request<Order>(`/orders/${order_id}/complete`, { method: "POST" }),

  listStockEvents: (meal_id?: string) => {
    const q = meal_id ? `?meal_id=${encodeURIComponent(meal_id)}` : "";
    return request<StockEvent[]>(`/stock-events${q}`);
  },

  reset: () => request<{ ok: boolean }>("/dev/reset", { method: "POST" }),
};
