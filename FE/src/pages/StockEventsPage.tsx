import { useEffect, useState } from "react";
import { api, type StockEvent } from "../api/client";

export default function StockEventsPage() {
  const [events, setEvents] = useState<StockEvent[]>([]);
  const [mealFilter, setMealFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load(mealId?: string) {
    try {
      setError(null);
      setEvents(await api.listStockEvents(mealId || undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h1>Stock events</h1>
          <p className="muted">
            Audit trail of inventory mutations (cart reserve, cancel restore, merchant
            adjust).
          </p>
        </div>
        <button type="button" className="btn ghost" onClick={() => void load(mealFilter)}>
          Refresh
        </button>
      </div>

      <div className="filter-row">
        <input
          value={mealFilter}
          onChange={(e) => setMealFilter(e.target.value)}
          placeholder="Filter by meal_id (e.g. meal_1)"
        />
        <button type="button" className="btn primary" onClick={() => void load(mealFilter)}>
          Apply filter
        </button>
        <button
          type="button"
          className="btn ghost"
          onClick={() => {
            setMealFilter("");
            void load();
          }}
        >
          Clear
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}

      <table className="table">
        <thead>
          <tr>
            <th>When</th>
            <th>Meal</th>
            <th>Type</th>
            <th>Source</th>
            <th>Qty</th>
            <th>Before → After</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id}>
              <td>{new Date(ev.created_at).toLocaleString()}</td>
              <td>
                <code>{ev.meal_id}</code>
              </td>
              <td className={ev.event_type === "DECREMENT" ? "neg" : "pos"}>
                {ev.event_type}
              </td>
              <td>{ev.event_source}</td>
              <td>{ev.quantity}</td>
              <td>
                {ev.stock_before} → {ev.stock_after}
              </td>
              <td className="muted">{ev.note}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {events.length === 0 && <p className="empty">No stock events yet.</p>}
    </section>
  );
}
