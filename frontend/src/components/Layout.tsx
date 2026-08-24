import { useEffect, type ReactNode, useRef, useState } from 'react';
import { LayoutDashboard, Ticket, BookOpen, BarChart3, Users, Menu, X, LogOut, RefreshCw, Bell, CheckCheck } from 'lucide-react';
import { useApp } from '../context/AppContext';

interface LayoutProps { children: ReactNode; currentView: string; onViewChange: (view: string) => void; }
export default function Layout({ children, currentView, onViewChange }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const { currentAgent, permissions, logout, refresh, loading, notifications, markNotificationRead, markAllNotificationsRead } = useApp();
  const unreadCount = notifications.filter(n => !n.readAt).length;
  useEffect(() => {
    const onClick = (e: MouseEvent) => { if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);
  const navigation = [
    { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard, permission: 'tickets.read' },
    { id: 'tickets', name: 'Tickets', icon: Ticket, permission: 'tickets.read' },
    { id: 'knowledge-base', name: 'Knowledge Base', icon: BookOpen, permission: 'kb.read' },
    { id: 'analytics', name: 'Analytics', icon: BarChart3, permission: 'analytics.read' },
    { id: 'agents', name: 'Agents', icon: Users, permission: 'agents.read' },
  ].filter(item => permissions.includes(item.permission));
  const initials = currentAgent?.fullName.split(' ').map(n => n[0]).join('').slice(0, 2) || '?';
  return <div className="min-h-screen bg-gray-50 flex">
    <aside className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-white border-r border-gray-200 transition-all duration-300 flex flex-col`}>
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200"><h1 className={`${sidebarOpen ? 'block' : 'hidden'} text-xl font-bold text-gray-900`}>SmartSupport AI</h1><button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 rounded-lg hover:bg-gray-100">{sidebarOpen ? <X size={20}/> : <Menu size={20}/>}</button></div>
      <nav className="flex-1 p-4 space-y-2">{navigation.map(item => { const Icon = item.icon; const active = currentView === item.id; return <button key={item.id} onClick={() => onViewChange(item.id)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${active ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-100'}`}><Icon size={20}/>{sidebarOpen && <span className="font-medium">{item.name}</span>}</button>; })}</nav>
      <div className="p-4 border-t border-gray-200"><div className={`${sidebarOpen ? 'flex items-center gap-3' : 'flex flex-col items-center gap-2'}`}><div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold">{initials}</div>{sidebarOpen && <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-gray-900">{currentAgent?.fullName}</p><p className="text-xs text-gray-500 capitalize">{currentAgent?.role.replace('_', ' ')}</p></div>}<button title="Refresh" disabled={loading} onClick={() => void refresh()} className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50"><RefreshCw size={16} className={loading ? 'animate-spin' : ''}/></button><button title="Sign out" onClick={logout} className="p-2 rounded-lg text-gray-500 hover:bg-red-50 hover:text-red-600"><LogOut size={16}/></button></div></div>
    </aside>
    <main className="flex-1 flex flex-col min-w-0"><header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6"><h2 className="text-lg font-semibold text-gray-900">{navigation.find(n => n.id === currentView)?.name || 'Dashboard'}</h2>
      <div className="flex items-center gap-4">
        <div className="relative" ref={notifRef}>
          <button onClick={() => setNotifOpen(o => !o)} className="relative p-2 rounded-lg hover:bg-gray-100 text-gray-700" aria-label="Notifications">
            <Bell size={20}/>
            {unreadCount > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center">{unreadCount > 99 ? '99+' : unreadCount}</span>}
          </button>
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-auto bg-white border border-gray-200 rounded-xl shadow-lg z-50">
              <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
                <p className="text-sm font-semibold text-gray-900">Notifications</p>
                {unreadCount > 0 && <button onClick={() => void markAllNotificationsRead()} className="text-xs text-blue-600 hover:underline flex items-center gap-1"><CheckCheck size={14}/> Mark all read</button>}
              </div>
              {notifications.length === 0 ? <p className="p-4 text-sm text-gray-500 text-center">No notifications yet.</p>
                : notifications.map(n => <button key={n.id} onClick={() => { void markNotificationRead(n.id); if (n.link) onViewChange('tickets'); }} className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 ${n.readAt ? 'opacity-60' : ''}`}>
                    <div className="flex items-start gap-2"><span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${n.readAt ? 'bg-transparent' : 'bg-blue-500'}`}/><div className="min-w-0"><p className="text-sm font-medium text-gray-900">{n.title}</p>{n.message && <p className="text-xs text-gray-500 line-clamp-2">{n.message}</p>}<time className="text-[10px] text-gray-400">{new Date(n.createdAt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</time></div></div>
                  </button>)}
            </div>
          )}
        </div>
        <p className="text-sm text-gray-600">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</p>
      </div>
    </header><div className="flex-1 overflow-auto p-6">{children}</div></main>
  </div>;
}
