import { Link, Navigate, Route, Routes } from "react-router-dom";
import { isStaff, useAuth } from "./auth.jsx";
import Login from "./pages/Login.jsx";
import Rooms from "./pages/Rooms.jsx";
import Registrations from "./pages/Registrations.jsx";
import Invoices from "./pages/Invoices.jsx";
import Incidents from "./pages/Incidents.jsx";
import Stats from "./pages/Stats.jsx";
import Register from "./pages/Register.jsx";
import "./extra.css";

function RequireAuth({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const { user, logout } = useAuth();
  const staff = isStaff(user);
  return (
    <>
      <header className="nav">
        <strong>KTX Sinh viên</strong>
        <nav>
          <Link to="/">Phòng</Link>
          {user && <Link to="/registrations">{staff ? "Duyệt đơn" : "Đơn của tôi"}</Link>}
          {user && <Link to="/invoices">Hóa đơn</Link>}
          {user && <Link to="/incidents">Sự cố</Link>}
          {staff && <Link to="/stats">Thống kê</Link>}
        </nav>
        <span className="spacer" />
        {user ? (
          <>
            <span className="who">{user.full_name} ({user.role})</span>
            <button onClick={logout}>Đăng xuất</button>
          </>
        ) : (
          <><Link to="/login">Đăng nhập</Link><Link to="/register">Đăng ký</Link></>
        )}
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Rooms />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/registrations" element={<RequireAuth><Registrations /></RequireAuth>} />
          <Route path="/invoices" element={<RequireAuth><Invoices /></RequireAuth>} />
          <Route path="/incidents" element={<RequireAuth><Incidents /></RequireAuth>} />
          <Route path="/stats" element={<RequireAuth>{staff ? <Stats /> : <Navigate to="/" replace />}</RequireAuth>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
