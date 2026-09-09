import { NavLink, Route, Routes } from "react-router-dom";
import MealsPage from "./pages/MealsPage";
import CartPage from "./pages/CartPage";
import OrdersPage from "./pages/OrdersPage";
import StockEventsPage from "./pages/StockEventsPage";

const links = [
  { to: "/", label: "Meals" },
  { to: "/cart", label: "Cart" },
  { to: "/orders", label: "Orders" },
  { to: "/stock-events", label: "Stock events" },
];

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <p className="brand-name">Surplus Food</p>
            <p className="brand-sub">Coding challenge</p>
          </div>
        </div>
        <nav className="nav">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<MealsPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/stock-events" element={<StockEventsPage />} />
        </Routes>
      </main>
    </div>
  );
}
