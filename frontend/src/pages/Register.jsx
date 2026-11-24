import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import api, { errorText } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Register() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "", full_name: "", student_code: "", gender: "MALE", phone: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { ...f };
      if (!body.phone) delete body.phone;
      await api.post("/auth/register", body);   // vai trò luôn là STUDENT do backend quyết định
      await login(f.email, f.password);
      nav("/");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card narrow">
      <h2>Đăng ký sinh viên</h2>
      <form onSubmit={submit}>
        <label>Họ và tên<input value={f.full_name} onChange={set("full_name")} required minLength={2} /></label>
        <label>Mã sinh viên<input value={f.student_code} onChange={set("student_code")} required minLength={3} /></label>
        <label>Giới tính
          <select value={f.gender} onChange={set("gender")}><option value="MALE">Nam</option><option value="FEMALE">Nữ</option></select>
        </label>
        <label>Email<input type="email" value={f.email} onChange={set("email")} required /></label>
        <label>Số điện thoại (không bắt buộc)<input value={f.phone} onChange={set("phone")} /></label>
        <label>Mật khẩu (từ 8 ký tự, có chữ và số)<input type="password" value={f.password} onChange={set("password")} required minLength={8} /></label>
        {error && <p className="error">{error}</p>}
        <button disabled={busy}>{busy ? "Đang đăng ký..." : "Đăng ký"}</button>
      </form>
      <p>Đã có tài khoản? <Link to="/login">Đăng nhập</Link></p>
    </section>
  );
}
