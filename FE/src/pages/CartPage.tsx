import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Cart } from "../api/client";

function formatBaht(n: number) {
  return `฿${n.toFixed(0)}`;
}

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setError(null);
      setCart(await api.getCart());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function checkout() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.createOrder();
      alert(`${result.message}\nOrder ${result.order.order_number}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function setQty(mealId: string, quantity: number) {
    try {
      setCart(await api.updateCartItem(mealId, quantity));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h1>Cart</h1>
          <p className="muted">Reserved units hold stock until checkout or release.</p>
        </div>
        <Link className="btn ghost" to="/">
          Keep browsing
        </Link>
      </div>

      {error && <div className="banner error">{error}</div>}

      {!cart || cart.items.length === 0 ? (
        <p className="empty">Cart is empty.</p>
      ) : (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>Meal</th>
                <th>Qty</th>
                <th>Unit</th>
                <th>Line</th>
              </tr>
            </thead>
            <tbody>
              {cart.items.map((item) => (
                <tr key={item.meal_id}>
                  <td>{item.meal_name}</td>
                  <td>
                    <div className="qty">
                      <button
                        type="button"
                        className="btn tiny"
                        onClick={() => void setQty(item.meal_id, item.quantity - 1)}
                      >
                        −
                      </button>
                      <span>{item.quantity}</span>
                      <button
                        type="button"
                        className="btn tiny"
                        onClick={() => void setQty(item.meal_id, item.quantity + 1)}
                      >
                        +
                      </button>
                    </div>
                  </td>
                  <td>{formatBaht(item.unit_price)}</td>
                  <td>{formatBaht(item.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="cart-foot">
            <p>
              Subtotal <strong>{formatBaht(cart.subtotal)}</strong>
            </p>
            <div className="row-actions">
              <button
                type="button"
                className="btn ghost"
                onClick={() => void api.clearCart().then(setCart)}
              >
                Clear cart
              </button>
              <button
                type="button"
                className="btn primary"
                disabled={busy}
                onClick={() => void checkout()}
              >
                {busy ? "Placing…" : "Place order"}
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
