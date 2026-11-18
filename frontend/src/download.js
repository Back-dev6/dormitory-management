import api from "./api.js";

// Tải file có xác thực (Excel...): gọi API bằng axios rồi lưu blob thành file
export async function download(url, params, filename) {
  const r = await api.get(url, { params, responseType: "blob" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(r.data);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
