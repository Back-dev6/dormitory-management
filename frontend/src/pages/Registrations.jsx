import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import { isStaff, useAuth } from "../auth.jsx";

const STATUS = { PENDING: "Chờ duyệt", APPROVED: "Đã duyệt", REJECTED: "Từ chối", CANCELLED: "Đã hủy" };

export default function Registrations() {
  const { user } = useAuth();
  const staff = isStaff(user);
  const [items, setItems] = useState([]);
  const [note, setNote] = useState(null);

  const load = () => {
    const req = staff ? api.get("/registrations", { params: { status: "PENDING", page_size: 50 } })
                      : api.get("/registrations/me");
    req.then((r) => setItems(staff ? r.data.items : r.data))
       .catch((e) => setNote({ err: true, text: errorText(e) }));
  };
  useEffect(load, []);

  const act = async (id, action, body) => {
    try {
      await api.post(`/registrations/${id}/${action}`, body);
      setNote({ text: "Thao tác thành công." });
    } catch (e) {
      setNote({ err: true, text: errorText(e) });
    }
    load();
  };
  const reject = (id) => {
    const reason = window.prompt("Lý do từ chối (tối thiểu 3 ký tự):");
    if (reason) act(id, "reject", { reason });
  };

  return (
    <>
      <h2>{staff ? "Đơn đang chờ duyệt" : "Đơn đăng ký của tôi"}</h2>
      {note && <p className={note.err ? "error" : "ok"}>{note.text}</p>}
      <div className="grid">
        {items.map((r) => (
          <article className="card" key={r.id}>
            <h3>{r.building_name} - {r.room_number}</h3>
            {staff && <p>{r.student_name} ({r.student_code})</p>}
            <p>Trạng thái: <strong>{STATUS[r.status]}</strong></p>
            {r.reject_reason && <p className="error">Lý do: {r.reject_reason}</p>}
            {r.status === "PENDING" && (staff ? (
              <div className="row">
                <button onClick={() => act(r.id, "approve", {})}>Duyệt</button>
                <button className="danger" onClick={() => reject(r.id)}>Từ chối</button>
              </div>
            ) : <button className="danger" onClick={() => act(r.id, "cancel")}>Hủy đơn</button>)}
          </article>
        ))}
        {items.length === 0 && <p>Chưa có đơn nào.</p>}
      </div>
    </>
  );
}
