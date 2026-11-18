import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import { isStaff, useAuth } from "../auth.jsx";

const ST = { OPEN: "Mới", IN_PROGRESS: "Đang xử lý", RESOLVED: "Đã xử lý" };

export default function Incidents() {
  const staff = isStaff(useAuth().user);
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: "", description: "" });
  const [file, setFile] = useState(null);
  const [note, setNote] = useState(null);
  const fail = (e) => setNote({ err: true, text: errorText(e) });

  const load = () => {
    const req = staff
      ? api.get("/incidents", { params: { page_size: 50 } }).then((r) => setItems(r.data.items))
      : api.get("/incidents/me").then((r) => setItems(r.data));
    req.catch(fail);
  };
  useEffect(() => { load(); }, []);

  const send = async (e) => {
    e.preventDefault();
    const fd = new FormData();
    fd.append("title", form.title);
    fd.append("description", form.description);
    if (file) fd.append("image", file);
    try {
      await api.post("/incidents", fd);
      setNote({ text: "Đã gửi phản ánh." });
      setForm({ title: "", description: "" });
      setFile(null);
      e.target.reset();
      load();
    } catch (err) { fail(err); }
  };
  const setStatus = async (id, status) => {
    try { await api.patch(`/incidents/${id}/status`, { status }); load(); } catch (err) { fail(err); }
  };
  // Ảnh cần token nên tải bằng axios rồi mở dưới dạng blob (không dùng thẻ img trực tiếp)
  const view = async (url) => {
    try {
      const r = await api.get(url.replace(/^\/api/, ""), { responseType: "blob" });
      window.open(URL.createObjectURL(r.data), "_blank");
    } catch (err) { fail(err); }
  };

  return (
    <>
      <h2>{staff ? "Phản ánh sự cố" : "Sự cố của tôi"}</h2>
      {note && <p className={note.err ? "error" : "ok"}>{note.text}</p>}
      {!staff && (
        <form className="card" onSubmit={send}>
          <label>Tiêu đề<input value={form.title} minLength={3} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></label>
          <label>Mô tả<textarea rows="3" value={form.description} minLength={3} onChange={(e) => setForm({ ...form, description: e.target.value })} required /></label>
          <label>Ảnh (JPG/PNG/WEBP, tối đa 5 MB)<input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0] || null)} /></label>
          <button>Gửi phản ánh</button>
        </form>
      )}
      <div className="grid" style={{ marginTop: 12 }}>
        {items.map((i) => (
          <article className="card" key={i.id}>
            <h3>{i.title}</h3>
            <p>{i.building_name} - {i.room_number}{staff && ` · ${i.student_name}`}</p>
            <p>{i.description}</p>
            <p>Trạng thái: <strong>{ST[i.status]}</strong></p>
            <div className="row">
              {i.image_url && <button onClick={() => view(i.image_url)}>Xem ảnh</button>}
              {staff && i.status === "OPEN" && <button onClick={() => setStatus(i.id, "IN_PROGRESS")}>Bắt đầu xử lý</button>}
              {staff && i.status !== "RESOLVED" && <button onClick={() => setStatus(i.id, "RESOLVED")}>Hoàn tất</button>}
            </div>
          </article>
        ))}
        {items.length === 0 && <p>Chưa có phản ánh nào.</p>}
      </div>
    </>
  );
}
