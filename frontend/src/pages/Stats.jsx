import { useEffect, useState } from "react";
import api, { errorText } from "../api.js";
import { download } from "../download.js";

export default function Stats() {
  const [rep, setRep] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get("/statistics/occupancy").then((r) => setRep(r.data)).catch((e) => setErr(errorText(e)));
  }, []);
  if (err) return <p className="error">{err}</p>;
  if (!rep) return <p>Đang tải...</p>;
  const row = (name, o) => (
    <tr key={name}>
      <td>{name}</td><td>{o.total_rooms}</td><td>{o.total_beds}</td><td>{o.occupied_beds}</td><td>{o.available_beds}</td>
      <td><div className="bar"><div style={{ width: `${o.occupancy_rate}%` }} /></div> {o.occupancy_rate}%</td>
    </tr>
  );
  return (
    <>
      <h2>Tỷ lệ lấp đầy theo tòa</h2>
      <button onClick={() => download("/statistics/occupancy/export", {}, "tyle_lapday.xlsx")}>Xuất Excel</button>
      <div className="scroll" style={{ marginTop: 12 }}>
        <table>
          <thead><tr><th>Tòa</th><th>Số phòng</th><th>Tổng giường</th><th>Đã ở</th><th>Còn trống</th><th>Tỷ lệ lấp đầy</th></tr></thead>
          <tbody>
            {rep.buildings.map((b) => row(b.building_name, b))}
            {row("TỔNG CỘNG", rep)}
          </tbody>
        </table>
      </div>
    </>
  );
}
