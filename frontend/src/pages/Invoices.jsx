import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import { isStaff, useAuth } from "../auth.jsx";
import { download } from "../download.js";

const money = (v) => Number(v).toLocaleString("vi-VN") + " đ";
const now = new Date();

export default function Invoices() {
  const staff = isStaff(useAuth().user);
  const [items, setItems] = useState([]);
  const [f, setF] = useState({ month: now.getMonth() + 1, year: now.getFullYear() });
  const [rooms, setRooms] = useState([]);
  const [rd, setRd] = useState({ room_id: "", electric_new: "", water_new: "", electric_old: "", water_old: "" });
  const [note, setNote] = useState(null);
  const fail = (e) => setNote({ err: true, text: errorText(e) });

  const load = () => {
    const req = staff
      ? api.get("/invoices", { params: { ...f, page_size: 100 } }).then((r) => setItems(r.data.items))
      : api.get("/invoices/me").then((r) => setItems(r.data));
    req.catch(fail);
  };
  useEffect(() => { load(); }, [f]);
  useEffect(() => {
    if (staff) api.get("/rooms", { params: { page_size: 100 } }).then((r) => setRooms(r.data.items));
  }, []);

  const addReading = async (e) => {
    e.preventDefault();
    const body = { room_id: +rd.room_id, month: +f.month, year: +f.year,
                   electric_new: +rd.electric_new, water_new: +rd.water_new };
    if (rd.electric_old !== "") body.electric_old = +rd.electric_old;
    if (rd.water_old !== "") body.water_old = +rd.water_old;
    try {
      await api.post("/utilities/readings", body);
      setNote({ text: "Đã ghi chỉ số và tự sinh hóa đơn." });
      load();
    } catch (err) { fail(err); }
  };
  const pay = async (id) => {
    try { await api.post(`/invoices/${id}/pay`); load(); } catch (err) { fail(err); }
  };
  const exportXlsx = () =>
    download("/invoices/export", f, `hoadon_${f.year}_${f.month}.xlsx`).catch(() =>
      setNote({ err: true, text: "Không tải được file Excel" }));

  return (
    <>
      <h2>{staff ? "Hóa đơn điện nước" : "Hóa đơn của phòng tôi"}</h2>
      {note && <p className={note.err ? "error" : "ok"}>{note.text}</p>}
      {staff && (
        <>
          <div className="form-row">
            <label>Tháng<input type="number" min="1" max="12" value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })} /></label>
            <label>Năm<input type="number" value={f.year} onChange={(e) => setF({ ...f, year: e.target.value })} /></label>
            <button onClick={exportXlsx}>Xuất Excel</button>
          </div>
          <form className="card form-row" onSubmit={addReading}>
            <label>Phòng
              <select value={rd.room_id} onChange={(e) => setRd({ ...rd, room_id: e.target.value })} required>
                <option value="">-- chọn --</option>
                {rooms.map((r) => <option key={r.id} value={r.id}>{r.building_name} - {r.room_number}</option>)}
              </select>
            </label>
            <label>Điện mới<input type="number" min="0" value={rd.electric_new} onChange={(e) => setRd({ ...rd, electric_new: e.target.value })} required /></label>
            <label>Nước mới<input type="number" min="0" value={rd.water_new} onChange={(e) => setRd({ ...rd, water_new: e.target.value })} required /></label>
            <label>Điện cũ (lần đầu)<input type="number" min="0" value={rd.electric_old} onChange={(e) => setRd({ ...rd, electric_old: e.target.value })} /></label>
            <label>Nước cũ (lần đầu)<input type="number" min="0" value={rd.water_old} onChange={(e) => setRd({ ...rd, water_old: e.target.value })} /></label>
            <button>Ghi chỉ số tháng {f.month}/{f.year}</button>
          </form>
        </>
      )}
      <div className="scroll">
        <table>
          <thead><tr><th>Phòng</th><th>Kỳ</th><th>Điện (kWh)</th><th>Nước (m3)</th><th>Tiền phòng</th><th>Tổng</th><th>Hạn</th><th>Trạng thái</th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td>{i.building_name} - {i.room_number}</td>
                <td>{i.month}/{i.year}</td>
                <td>{i.electric_usage} ({money(i.electric_amount)})</td>
                <td>{i.water_usage} ({money(i.water_amount)})</td>
                <td>{money(i.room_fee)}</td>
                <td><strong>{money(i.total)}</strong></td>
                <td>{i.due_date}</td>
                <td>{i.status === "PAID" ? "Đã thanh toán" : staff ? <button onClick={() => pay(i.id)}>Đánh dấu đã thu</button> : "Chưa thanh toán"}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan="8">Chưa có hóa đơn.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
