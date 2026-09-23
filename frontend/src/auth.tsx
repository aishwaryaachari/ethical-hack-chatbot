import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getUsers } from './api';

export interface DemoUser { user_id: string; email: string; role: string; tenant_id: string; }
export interface Tenant { tenant_id: string; }

interface AuthCtx {
  user: DemoUser | null;
  users: DemoUser[];
  tenants: Tenant[];
  usersFailed: boolean;
  login: (userId: string) => void;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({ user: null, users: [], tenants: [], usersFailed: false, login: () => {}, logout: () => {} });
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  // No fallbacks: accounts come only from the backend.
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [usersFailed, setUsersFailed] = useState(false);
  const [user, setUser] = useState<DemoUser | null>(() => {
    try { return JSON.parse(localStorage.getItem('lab_user') || 'null'); } catch { return null; }
  });

  useEffect(() => {
    getUsers()
      .then(d => { setUsers(d.users || []); setTenants(d.tenants || []); })
      .catch(() => setUsersFailed(true));
  }, []);

  const login = (userId: string) => {
    const u = users.find(x => x.user_id === userId);
    if (u) { setUser(u); localStorage.setItem('lab_user', JSON.stringify(u)); }
  };
  const logout = () => { setUser(null); localStorage.removeItem('lab_user'); };

  return <Ctx.Provider value={{ user, users, tenants, usersFailed, login, logout }}>{children}</Ctx.Provider>;
}
