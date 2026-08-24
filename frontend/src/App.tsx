import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import TicketList from './components/TicketList';
import KnowledgeBase from './components/KnowledgeBase';
import Analytics from './components/Analytics';
import Agents from './components/Agents';

function LoginScreen() {
  const { login, loading, error } = useApp();
  const [email, setEmail] = useState('admin@smart.support');
  const [password, setPassword] = useState('admin123');
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setSubmitting(true); setLocalError(null);
    try { await login(email, password); } catch (e) { setLocalError(e instanceof Error ? e.message : 'Sign-in failed'); } finally { setSubmitting(false); }
  };
  return <main className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
    <section className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">
      <p className="text-xs font-semibold tracking-[0.25em] text-cyan-400 uppercase">Support operations</p>
      <h1 className="mt-3 text-3xl font-bold text-white">SmartSupport AI</h1>
      <p className="mt-2 text-sm text-slate-400">Sign in to the real production workspace.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <label className="block text-sm font-medium text-slate-200">Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:ring-2 focus:ring-cyan-500" required /></label>
        <label className="block text-sm font-medium text-slate-200">Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:ring-2 focus:ring-cyan-500" required /></label>
        {(localError || error) && <p className="rounded-lg border border-red-800 bg-red-950 px-3 py-2 text-sm text-red-200">{localError || error}</p>}
        <button disabled={submitting || loading} className="w-full rounded-lg bg-cyan-500 px-4 py-2.5 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60">{submitting ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="mt-5 text-xs text-slate-500">Local seeded admin: admin@smart.support / admin123</p>
    </section>
  </main>;
}

function Workspace() {
  const { currentAgent, loading, error, refresh } = useApp();
  const [currentView, setCurrentView] = useState('dashboard');
  if (loading && !currentAgent) return <main className="min-h-screen grid place-items-center bg-slate-950 text-slate-200">Loading secure workspace…</main>;
  if (!currentAgent) return <LoginScreen />;
  const renderView = () => {
    switch (currentView) {
      case 'tickets': return <TicketList />;
      case 'knowledge-base': return <KnowledgeBase />;
      case 'analytics': return <Analytics />;
      case 'agents': return <Agents />;
      default: return <Dashboard />;
    }
  };
  return <Layout currentView={currentView} onViewChange={setCurrentView}>
    {error && <div className="mb-4 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"><span>{error}</span><button onClick={() => void refresh()} className="font-semibold underline">Retry</button></div>}
    {loading && <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-700">Refreshing live data…</div>}
    {renderView()}
  </Layout>;
}

export default function App() { return <AppProvider><Workspace /></AppProvider>; }
