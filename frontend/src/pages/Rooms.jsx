import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import { useAuth } from "../auth.jsx";

const money = (v) => Number(v).toLocaleString("vi-VN") + " đ";

export default function Rooms() {
  const { user } = useAuth();
  const [buildings, setBuildings] = useState([]);
  const [f, setF] = useState({ building_id: "", gender: "", max_price: "", available_only: true });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, page_size: 12 });
  const [note, setNote] = useState(null);

  useEffect(() => { api.get("/buildings").then((r) => setBuildings(r.data)); }, []);

  const load = () => {
    const params = { page, page_size: 12, available_only: f.available_only };
    ["building_id", "gender", "max_price"].forEach((k) => f[k] !== "" && (params[k] = f[k]));
    api.get("/rooms", { params }).then((r) => setData(r.data)).catch((e) => setNote({ err: true, text: errorText(e) }));
  };
  useEffect(load, [page, f]);

  const change = (k, v) => { setPage(1); setF({ ...f, [k]: v }); };

  const register = async (room) => {
    try {
      await api.post("/registrations", { room_id: room.id });
      setNote({ text: `Đã gửi đơn đăng ký phòng ${room.room_number}. Chờ cán bộ duyệt.` });
    } catch (e) {
      setNote({ err: true, text: errorText(e) });
    }
  };

  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <>
      <h2>Danh sách phòng</h2>
      <div className="filters">
        <select value={f.building_id} onChange={(e) => change("building_id", e.target.value)}>
          <option value="">Tất cả tòa</option>
          {buildings.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        <select value={f.gender} onChange={(e) => change("gender", e.target.value)}>
          <option value="">Mọi giới tính</option><option value="MALE">Nam</option><option value="FEMALE">Nữ</option>
        </select>
        <input type="number" min="0" placeholder="Giá tối đa / giường" value={f.max_price}
               onChange={(e) => change("max_price", e.target.value)} />
        <label className="inline">
          <input type="checkbox" checked={f.available_only} onChange={(e) => change("available_only", e.target.checked)} />
          Chỉ phòng còn chỗ
        </label>
      </div>
      {note && <p className={note.err ? "error" : "ok"}>{note.text}</p>}
      <div className="grid">
        {data.items.map((r) => (
          <article className="card" key={r.id}>
            <h3>{r.building_name} - {r.room_number}</h3>
            <p>{r.gender_type === "MALE" ? "Nam" : "Nữ"} · Tầng {r.floor}</p>
            <p>Còn <strong>{r.available_beds}</strong>/{r.max_beds} giường</p>
            <p>{money(r.price_per_bed)} / giường</p>
            {user?.role === "STUDENT" && r.available_beds > 0 && <button onClick={() => register(r)}>Đăng ký</button>}
          </article>
        ))}
        {data.items.length === 0 && <p>Không có phòng phù hợp.</p>}
      </div>
      <div className="pager">
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Trước</button>
        <span>Trang {page}/{pages}</span>
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>Sau</button>
      </div>
    </>
  );
}
