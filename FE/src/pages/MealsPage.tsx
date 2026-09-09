import { useEffect, useState } from "react";
import { api, type Meal } from "../api/client";

function formatBaht(n: number) {
  return `฿${n.toFixed(0)}`;
}

export default function MealsPage() {
  const [meals, setMeals] = useState<Meal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);
      setMeals(await api.listMeals(true));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function add(meal: Meal) {
    setBusyId(meal.id);
    setToast(null);
    try {
      await api.addToCart(meal.id, 1);
      setToast(`Added “${meal.name}” to cart`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h1>Surplus meals</h1>
          <p className="muted">Browse rescued food near closing time and add to cart.</p>
        </div>
        <button type="button" className="btn ghost" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}
      {toast && <div className="banner ok">{toast}</div>}

      <div className="meal-list">
        {meals.map((meal) => (
          <article key={meal.id} className="meal-row">
            <div className="meal-copy">
              <h2>{meal.name}</h2>
              <p className="muted">{meal.description}</p>
              <p className="stock">Stock left: {meal.stock_available}</p>
            </div>
            <div className="meal-price">
              <span className="strike">{formatBaht(meal.original_price)}</span>
              <strong className="pay">{formatBaht(meal.discounted_price)}</strong>
              <button
                type="button"
                className="btn primary"
                disabled={busyId === meal.id || meal.stock_available < 1}
                onClick={() => void add(meal)}
              >
                {busyId === meal.id ? "Adding…" : "Add to cart"}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
