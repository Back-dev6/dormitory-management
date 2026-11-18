import { createContext, useContext, useState } from "react";
import api, { tokens } from "./api.js";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);
export const isStaff = (u) => u && (u.role === "MANAGER" || u.role === "ADMIN");

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => tokens.get()?.user ?? null);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    tokens.set(data);
    setUser(data.user);
  };
  const logout = async () => {
    const t = tokens.get();
    if (t) await api.post("/auth/logout", { refresh_token: t.refresh_token }).catch(() => {});
    tokens.clear();
    setUser(null);
  };
  return <Ctx.Provider value={{ user, login, logout }}>{children}</Ctx.Provider>;
}
