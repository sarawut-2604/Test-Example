import { useEffect, useState } from "react";
import { api, type Order } from "../api/client";

function formatBaht(n: number) {
  return `฿${n.toFixed(0)}`;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);
      setOrders(await api.listOrders());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function cancel(order: Order) {
    try {
      await api.cancelOrder(order.id);
      // Intentionally still reload — cancel itself works once BE is fixed.
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h1>Orders</h1>
          <p className="muted">Confirm, cancel, and inspect checkout history.</p>
        </div>
        <button type="button" className="btn ghost" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}

      {orders.length === 0 ? (
        <p className="empty">No orders yet. Place one from the cart.</p>
      ) : (
        <div className="order-list">
          {orders.map((order) => (
            <article key={order.id} className="order-card">
              <div className="order-top">
                <div>
                  <h2>{order.order_number}</h2>
                  <p className="muted">
                    {new Date(order.created_at).toLocaleString()} ·{" "}
                    <span className={`status ${order.status.toLowerCase()}`}>
                      {order.status}
                    </span>
                  </p>
                </div>
                <strong>{formatBaht(order.subtotal)}</strong>
              </div>
              <ul>
                {order.lines.map((line) => (
                  <li key={`${order.id}-${line.meal_id}`}>
                    {line.quantity}× {line.meal_name} — {formatBaht(line.line_total)}
                  </li>
                ))}
              </ul>
              {order.status === "CONFIRMED" && (
                <button
                  type="button"
                  className="btn ghost"
                  onClick={() => void cancel(order)}
                >
                  Cancel order
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
