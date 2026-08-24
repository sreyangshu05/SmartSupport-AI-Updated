import { useState } from 'react';
import { Bot, Link2, Send, Sparkles, Tag, TrendingUp, X } from 'lucide-react';
import { useApp } from '../context/AppContext';
import type { AIClassification, KBSuggestion, SimilarTicket, Ticket, TicketPriority, TicketStatus } from '../types';

const slaBadge = (sla?: string) => sla === 'green' ? 'bg-green-100 text-green-700' : sla === 'warning' ? 'bg-yellow-100 text-yellow-700' : sla === 'breached' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-400';

export default function TicketDetailModal({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const { categories, agents, updateTicket, addResponse, generateDraft, generateSummary, classifyTicket, getSimilarTickets, getKBSuggestions } = useApp();
  const [status, setStatus] = useState<TicketStatus>(ticket.status);
  const [priority, setPriority] = useState<TicketPriority>(ticket.priority);
  const [categoryId, setCategoryId] = useState(ticket.categoryId || '');
  const [assignedTo, setAssignedTo] = useState(ticket.assignedTo || '');
  const [reply, setReply] = useState('');
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState<string | undefined>(ticket.summary);
  const [classification, setClassification] = useState<AIClassification | null>(null);
  const [similar, setSimilar] = useState<SimilarTicket[]>([]);
  const [suggestions, setSuggestions] = useState<KBSuggestion[]>([]);
  const [aiLoading, setAiLoading] = useState(false);

  const save = async () => { setBusy(true); setNotice(null); try { await updateTicket(ticket.id, { status, priority, categoryId, assignedTo }); setNotice('Saved to the backend.'); } catch (e) { setNotice(e instanceof Error ? e.message : 'Save failed'); } finally { setBusy(false); } };
  const send = async () => { if (!reply.trim()) return; setBusy(true); setNotice(null); try { await addResponse(ticket.id, reply); setReply(''); setNotice('Reply sent and recorded.'); } catch (e) { setNotice(e instanceof Error ? e.message : 'Reply failed'); } finally { setBusy(false); } };
  const draft = async () => { setBusy(true); setNotice(null); try { setReply(await generateDraft(ticket.id)); setNotice('AI draft generated. Review before sending.'); } catch (e) { setNotice('AI draft unavailable. Configure the provider to enable it.'); } finally { setBusy(false); } };

  const aiHeap = async () => {
    setAiLoading(true); setNotice(null);
    try {
      const [s, c, sim, kb] = await Promise.all([
        generateSummary(ticket.id).catch(() => ''),
        classifyTicket(ticket.id).catch(() => null),
        getSimilarTickets(ticket.id).catch(() => []),
        getKBSuggestions(ticket.id).catch(() => []),
      ]);
      if (s) setSummary(s);
      if (c) setClassification(c);
      setSimilar(sim);
      setSuggestions(kb);
      setNotice('AI analysis refreshed (summary, classification, similar tickets, KB suggestions).');
    } catch { /* individual calls already swallowed */ } finally { setAiLoading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-xl bg-white shadow-2xl">
        <header className="sticky top-0 flex items-center justify-between border-b bg-white px-6 py-4">
          <div><h2 className="font-mono text-lg font-semibold">{ticket.ticketNumber}</h2><p className="text-sm text-gray-500">{ticket.createdBy}</p></div>
          <div className="flex items-center gap-3">
            <button onClick={() => void aiHeap()} disabled={aiLoading} className="flex items-center gap-1.5 rounded-lg border border-purple-300 px-3 py-1.5 text-sm font-medium text-purple-700 hover:bg-purple-50 disabled:opacity-60"><Sparkles size={15}/>{aiLoading ? 'Analyzing…' : 'AI analyze'}</button>
            <button onClick={onClose} className="rounded p-2 hover:bg-gray-100"><X size={20}/></button>
          </div>
        </header>
        <div className="grid gap-6 p-6 lg:grid-cols-3">
          <section className="space-y-6 lg:col-span-2">
            <div>
              <h3 className="text-xl font-semibold">{ticket.subject}</h3>
              {summary && <p className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800"><Bot className="mr-2 inline" size={16}/>{summary}</p>}
              {classification && (
                <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 text-xs text-purple-700">
                  <Tag size={13}/> Suggested category: {classification.category?.name || '—'}
                  {classification.confidence != null && <span className="ml-1 rounded-full bg-purple-200 px-2 py-0.5">{(classification.confidence * 100).toFixed(0)}% conf</span>}
                  {classification.lowConfidence && <span className="ml-1 text-purple-400">(low confidence)</span>}
                </div>
              )}
              <p className="mt-4 whitespace-pre-wrap text-gray-700">{ticket.description}</p>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-3 flex items-center justify-between"><h4 className="font-semibold">Reply to customer</h4><button onClick={() => void draft()} disabled={busy} className="rounded-lg border border-purple-300 px-3 py-1.5 text-sm font-medium text-purple-700 hover:bg-purple-50">Generate AI draft</button></div>
              <textarea value={reply} onChange={e => setReply(e.target.value)} rows={6} placeholder="Write a customer-facing reply…" className="w-full rounded-lg border px-3 py-2"/>
              <button onClick={() => void send()} disabled={busy || !reply.trim()} className="mt-3 flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-60"><Send size={16}/>Send reply</button>
            </div>

            {(similar.length > 0 || suggestions.length > 0) && (
              <div className="grid gap-4 sm:grid-cols-2">
                {similar.length > 0 && <div className="rounded-lg border p-4"><h4 className="mb-3 flex items-center gap-1.5 font-semibold"><TrendingUp size={16}/> Similar tickets</h4><ul className="space-y-2">{similar.map((s, i) => <li key={i} className="rounded border p-2"><p className="truncate text-sm font-medium text-gray-900"><span className="font-mono text-xs text-gray-400">{s.ticket.ticketNumber}</span> {s.ticket.subject}</p><p className="text-xs text-gray-500">{(s.similarityScore * 100).toFixed(0)}% match</p></li>)}</ul></div>}
                {suggestions.length > 0 && <div className="rounded-lg border p-4"><h4 className="mb-3 flex items-center gap-1.5 font-semibold"><Link2 size={16}/> KB suggestions</h4><ul className="space-y-2">{suggestions.map((s, i) => <li key={i} className="rounded border p-2"><p className="truncate text-sm font-medium text-gray-900">{s.article.title}</p>{s.article.summary && <p className="line-clamp-2 text-xs text-gray-500">{s.article.summary}</p>}<p className="text-xs text-gray-400">{(s.relevanceScore * 100).toFixed(0)}% relevant</p></li>)}</ul></div>}
              </div>
            )}

            {ticket.responses?.length ? <div><h4 className="mb-3 font-semibold">Conversation</h4><div className="space-y-3">{ticket.responses.map(r => <article key={r.id} className={`rounded-lg border p-3 ${r.isInternal ? 'bg-amber-50' : 'bg-gray-50'}`}><div className="mb-1 text-xs text-gray-500">{r.isInternal ? 'Internal note' : r.authorName || 'Agent'} · {new Date(r.createdAt).toLocaleString()}</div><p className="whitespace-pre-wrap text-sm">{r.content}</p></article>)}</div></div> : null}
          </section>

          <aside className="rounded-lg bg-gray-50 p-4">
            <h4 className="mb-4 font-semibold">Ticket details</h4>
            <div className="space-y-4">
              {ticket.slaStatus && <div className="rounded-lg border bg-white p-3"><div className="flex items-center justify-between"><span className="text-xs font-medium uppercase text-gray-500">SLA</span><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${slaBadge(ticket.slaStatus)}`}>{ticket.slaStatus.charAt(0).toUpperCase() + ticket.slaStatus.slice(1)}</span></div>{ticket.slaDueAt && <p className="mt-1 text-xs text-gray-500">Due {new Date(ticket.slaDueAt).toLocaleString()}</p>}</div>}
              <label className="block text-sm font-medium">Status<select value={status} onChange={e => setStatus(e.target.value as TicketStatus)} className="mt-1 w-full rounded-lg border px-3 py-2"><option value="open">Open</option><option value="in_progress">In progress</option><option value="waiting_for_customer">Waiting for customer</option><option value="waiting_for_internal">Waiting for internal</option><option value="resolved">Resolved</option><option value="closed">Closed</option></select></label>
              <label className="block text-sm font-medium">Priority<select value={priority} onChange={e => setPriority(e.target.value as TicketPriority)} className="mt-1 w-full rounded-lg border px-3 py-2"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
              <label className="block text-sm font-medium">Category<select value={categoryId} onChange={e => setCategoryId(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2"><option value="">None</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
              <label className="block text-sm font-medium">Assign<select value={assignedTo} onChange={e => setAssignedTo(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2"><option value="">Unassigned</option>{agents.filter(a => a.isActive).map(a => <option key={a.id} value={a.id}>{a.fullName}</option>)}</select></label>
              <button onClick={() => void save()} disabled={busy} className="w-full rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-60">Save changes</button>
              {notice && <p className={`text-sm ${notice.includes('failed') || notice.includes('unavailable') ? 'text-red-600' : 'text-green-700'}`}>{notice}</p>}
              <dl className="space-y-2 border-t pt-4 text-xs text-gray-500"><div><dt>Created</dt><dd className="text-gray-700">{new Date(ticket.createdAt).toLocaleString()}</dd></div><div><dt>Last updated</dt><dd className="text-gray-700">{new Date(ticket.updatedAt).toLocaleString()}</dd></div></dl>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
