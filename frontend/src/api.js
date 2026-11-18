import axios from "axios";

// Token lưu ở localStorage (đơn giản cho đồ án; sản phẩm thật nên cân nhắc cookie HttpOnly)
export const tokens = {
  get: () => JSON.parse(localStorage.getItem("tokens") || "null"),
  set: (t) => localStorage.setItem("tokens", JSON.stringify(t)),
  clear: () => localStorage.removeItem("tokens"),
};

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const t = tokens.get();
  if (t) config.headers.Authorization = `Bearer ${t.access_token}`;
  return config;
});

// Gặp 401 (access token hết hạn): tự refresh MỘT lần rồi gọi lại request cũ.
// Nhiều request lỗi cùng lúc dùng chung một lần refresh (tránh dùng lại refresh token đã xoay vòng).
let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const { config, response } = err;
    const t = tokens.get();
    if (response?.status === 401 && t && !config._retry && !config.url.startsWith("/auth/")) {
      config._retry = true;
      refreshing ||= axios
        .post("/api/auth/refresh", { refresh_token: t.refresh_token })
        .then((r) => { tokens.set(r.data); })
        .catch((e) => { tokens.clear(); window.location.assign("/login"); throw e; })
        .finally(() => { refreshing = null; });
      await refreshing;
      return api(config);
    }
    return Promise.reject(err);
  }
);

export function errorText(e) {
  const d = e.response?.data?.detail;
  return Array.isArray(d) ? d.map((x) => x.msg).join("; ") : d || "Có lỗi xảy ra, thử lại sau";
}

export default api;
