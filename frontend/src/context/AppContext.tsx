import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, ApiError, login as loginRequest } from '../lib/api';
import type { AIClassification, Agent, AgentAnalytics, AgentRole, AnalyticsOverview, AppNotification, KBArticle, KBSuggestion, SimilarTicket, Ticket, TicketCategory, TicketCluster, TicketPriority } from '../types';

interface CurrentUserApi { id: string; email: string; full_name: string; role: AgentRole; is_active: boolean; permissions: string[]; }
interface AppContextType {
  currentAgent: Agent | null;
  permissions: string[];
  agents: Agent[];
  categories: TicketCategory[];
  tickets: Ticket[];
  kbArticles: KBArticle[];
  clusters: TicketCluster[];
  analytics: AgentAnalytics[];
  overview: AnalyticsOverview | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  addTicket: (ticket: { subject: string; description: string; priority: TicketPriority; categoryId?: string; assignedTo?: string; createdBy: string; customerName?: string }) => Promise<void>;
  updateTicket: (id: string, updates: Partial<Ticket>) => Promise<void>;
  addResponse: (ticketId: string, content: string, isInternal?: boolean) => Promise<void>;
  generateDraft: (ticketId: string) => Promise<string>;
  addKBArticle: (article: { title: string; content: string; summary?: string; categoryId?: string; tags?: string[]; isPublished?: boolean }) => Promise<void>;
  updateKBArticle: (id: string, updates: Partial<KBArticle>) => Promise<void>;
  deleteKBArticle: (id: string) => Promise<void>;
  notifications: AppNotification[];
  markNotificationRead: (id: string) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;
  generateSummary: (ticketId: string) => Promise<string>;
  classifyTicket: (ticketId: string) => Promise<AIClassification>;
  getSimilarTickets: (ticketId: string) => Promise<SimilarTicket[]>;
  getKBSuggestions: (ticketId: string) => Promise<KBSuggestion[]>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);
const TOKEN_KEY = 'smartsupport_token';

function mapAgent(raw: any): Agent {
  return { id: raw.id, email: raw.email, fullName: raw.full_name, role: raw.role, isActive: raw.is_active, lastActiveAt: raw.last_active_at, createdAt: raw.created_at || '', openTicketCount: raw.open_ticket_count || 0 };
}
function mapTicket(raw: any, agents: Agent[] = [], categories: TicketCategory[] = []): Ticket {
  const assigned = raw.assigned_agent ? mapAgent({ ...raw.assigned_agent, is_active: true }) : agents.find(a => a.id === raw.assigned_to);
  const category = raw.category || categories.find(c => c.id === raw.category_id);
  return {
    id: raw.id, ticketNumber: raw.ticket_number, subject: raw.subject, description: raw.description, summary: raw.summary || undefined,
    status: raw.status, priority: raw.priority, categoryId: raw.category?.id || raw.category_id || undefined, category,
    assignedTo: raw.assigned_agent?.id || raw.assigned_to || undefined, assignedAgent: assigned,
    createdBy: raw.created_by_email, customerName: raw.customer?.full_name || undefined,
    createdAt: raw.created_at, updatedAt: raw.updated_at, resolvedAt: raw.resolved_at || undefined, closedAt: raw.closed_at || undefined,
    slaStatus: raw.sla_status || undefined, slaDueAt: raw.sla_due_at || undefined,
    tags: raw.tags || [],
    responses: raw.responses?.map((r: any) => ({ id: r.id, ticketId: r.ticket_id, content: r.content, isInternal: r.is_internal, responseType: r.response_type, authorName: r.author_name, createdAt: r.created_at })),
    events: raw.events?.map((e: any) => ({ id: e.id, eventType: e.event_type, oldValue: e.old_value, newValue: e.new_value, createdAt: e.created_at })),
  };
}
function mapArticle(raw: any, categories: TicketCategory[] = []): KBArticle {
  const category = categories.find(c => c.id === raw.category_id) || (raw.category ? categories.find(c => c.name === raw.category) : undefined);
  return { id: raw.id, title: raw.title, content: raw.content, summary: raw.summary || undefined, status: raw.status, isPublished: raw.status === 'published', tags: raw.tags || [], viewCount: raw.view_count || 0, helpfulCount: raw.helpful_count || 0, usageCount: raw.usage_count || 0, categoryId: raw.category_id || undefined, category, createdBy: raw.author_id, createdAt: raw.created_at, updatedAt: raw.updated_at, currentVersion: raw.current_version };
}
function mapOverview(raw: any): AnalyticsOverview { return { totalTickets: raw.total_tickets, openTickets: raw.open_tickets, inProgressTickets: raw.in_progress_tickets, resolvedTickets: raw.resolved_tickets, avgResolutionMinutes: raw.avg_resolution_minutes ?? undefined, avgFirstResponseMinutes: raw.avg_first_response_minutes ?? undefined, ticketsByStatus: raw.tickets_by_status || {}, ticketsByPriority: raw.tickets_by_priority || {}, ticketsByCategory: raw.tickets_by_category || {} }; }

export function AppProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [categories, setCategories] = useState<TicketCategory[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [kbArticles, setKBArticles] = useState<KBArticle[]>([]);
  const [clusters, setClusters] = useState<TicketCluster[]>([]);
  const [analytics, setAnalytics] = useState<AgentAnalytics[]>([]);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      const me = await api<CurrentUserApi>('/auth/me', {}, token);
      const [rawAgents, rawCategories, rawTickets, rawArticles, rawOverview, rawPerformance, rawClusters, rawNotifications] = await Promise.all([
        api<any[]>('/agents', {}, token), api<TicketCategory[]>('/categories', {}, token), api<any>('/tickets?page_size=100', {}, token), api<any>('/kb/articles?page_size=100', {}, token), api<any>('/analytics/overview', {}, token), api<any[]>('/analytics/agents', {}, token), api<any[]>('/clusters', {}, token), api<any[]>('/notifications', {}, token),
      ]);
      const nextAgents = rawAgents.map(mapAgent);
      const nextCategories = rawCategories;
      setCurrentAgent({ id: me.id, email: me.email, fullName: me.full_name, role: me.role, isActive: me.is_active, createdAt: '' });
      setPermissions(me.permissions || []);
      setAgents(nextAgents); setCategories(nextCategories);
      setTickets((rawTickets.items || []).map((x: any) => mapTicket(x, nextAgents, nextCategories)));
      setKBArticles((rawArticles.items || []).map((x: any) => mapArticle(x, nextCategories)));
      setOverview(mapOverview(rawOverview));
      setAnalytics(rawPerformance.map((x: any, index: number) => ({ id: x.agent_id || String(index), agentId: x.agent_id, date: '', ticketsCreated: x.tickets_created || 0, ticketsResolved: x.tickets_resolved || 0, avgResponseTimeMinutes: x.avg_first_response_minutes || 0, avgResolutionTimeMinutes: x.avg_resolution_minutes || 0, totalResponses: x.total_responses || 0, kbArticlesCreated: 0 })));
      setClusters(rawClusters.map((x: any) => ({ id: x.id, name: x.name, description: `Confidence: ${Math.round((x.confidence || 0) * 100)}%`, ticketCount: x.ticket_count, firstSeen: x.first_seen, lastSeen: x.last_seen, isTrending: x.is_trending })));
      setNotifications((rawNotifications || []).map((x: any) => ({ id: x.id, type: x.type, title: x.title, message: x.message || undefined, link: x.link || undefined, readAt: x.read_at || undefined, createdAt: x.created_at })));
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unable to load workspace';
      setError(message);
      if (e instanceof ApiError && e.status === 401) { localStorage.removeItem(TOKEN_KEY); setToken(null); setCurrentAgent(null); }
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    if (!token) return;
    let aborted = false;
    const source = new EventSource(`${import.meta.env.VITE_API_BASE_URL || '/api'}/notifications/stream?token=${encodeURIComponent(token)}`);
    source.onmessage = () => {
      if (!aborted) void refresh();
    };
    source.onerror = () => {
      source.close();
    };
    return () => {
      aborted = true;
      source.close();
    };
  }, [token, refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginRequest(email, password);
    localStorage.setItem(TOKEN_KEY, result.access_token); setToken(result.access_token);
  }, []);
  const logout = useCallback(() => { localStorage.removeItem(TOKEN_KEY); setToken(null); setCurrentAgent(null); setPermissions([]); setTickets([]); setNotifications([]); }, []);

  const addTicket = useCallback(async (draft: any) => {
    if (!token) return;
    const created = await api<any>('/tickets', { method: 'POST', body: JSON.stringify({ subject: draft.subject, description: draft.description, priority: draft.priority, category_id: draft.categoryId || null, customer_email: draft.createdBy, customer_name: draft.customerName || null, tags: [] }) }, token);
    if (draft.assignedTo) await api(`/tickets/${created.id}`, { method: 'PATCH', body: JSON.stringify({ assigned_to: draft.assignedTo }) }, token);
    await refresh();
  }, [token, refresh]);

  const updateTicket = useCallback(async (id: string, updates: Partial<Ticket>) => {
    if (!token) return;
    const body: any = {};
    if (updates.subject !== undefined) body.subject = updates.subject;
    if (updates.description !== undefined) body.description = updates.description;
    if (updates.status !== undefined) body.status = updates.status;
    if (updates.priority !== undefined) body.priority = updates.priority;
    if (updates.categoryId !== undefined) body.category_id = updates.categoryId || null;
    if (updates.assignedTo !== undefined) body.assigned_to = updates.assignedTo || null;
    await api(`/tickets/${id}`, { method: 'PATCH', body: JSON.stringify(body) }, token);
    await refresh();
  }, [token, refresh]);

  const addResponse = useCallback(async (ticketId: string, content: string, isInternal = false) => {
    if (!token) return;
    await api(`/tickets/${ticketId}/responses`, { method: 'POST', body: JSON.stringify({ content, is_internal: isInternal }) }, token);
    await refresh();
  }, [token, refresh]);

  const generateDraft = useCallback(async (ticketId: string) => {
    if (!token) throw new Error('Please sign in again');
    const result = await api<any>(`/tickets/${ticketId}/ai/draft`, { method: 'POST' }, token);
    return result.draft;
  }, [token]);

  const markNotificationRead = useCallback(async (id: string) => {
    if (!token) return;
    await api(`/notifications/${id}/read`, { method: 'PATCH' }, token);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, readAt: new Date().toISOString() } : n));
  }, [token]);

  const markAllNotificationsRead = useCallback(async () => {
    if (!token) return;
    const unread = notifications.filter(n => !n.readAt);
    await Promise.all(unread.map(n => api(`/notifications/${n.id}/read`, { method: 'PATCH' }, token).catch(() => null)));
    setNotifications(prev => prev.map(n => ({ ...n, readAt: n.readAt || new Date().toISOString() })));
  }, [token, notifications]);

  const generateSummary = useCallback(async (ticketId: string): Promise<string> => {
    if (!token) throw new Error('Please sign in again');
    const result = await api<any>(`/tickets/${ticketId}/ai/summary`, { method: 'POST' }, token);
    return result.summary ?? result.content ?? '';
  }, [token]);

  const classifyTicket = useCallback(async (ticketId: string): Promise<AIClassification> => {
    if (!token) throw new Error('Please sign in again');
    const result = await api<any>(`/tickets/${ticketId}/ai/classify`, { method: 'POST' }, token);
    return { category: result.category ? { id: result.category.id, name: result.category.name } : undefined, categoryId: result.category_id, confidence: result.confidence, lowConfidence: result.low_confidence, reasoning: result.reasoning };
  }, [token]);

  const getSimilarTickets = useCallback(async (ticketId: string): Promise<SimilarTicket[]> => {
    if (!token) return [];
    const result = await api<any[]>(`/tickets/${ticketId}/similar`, {}, token);
    return (result || []).map((x: any) => ({ ticket: mapTicket(x.ticket), similarityScore: x.similarity_score ?? 0 }));
  }, [token]);

  const getKBSuggestions = useCallback(async (ticketId: string): Promise<KBSuggestion[]> => {
    if (!token) return [];
    const result = await api<any[]>(`/tickets/${ticketId}/kb-suggestions`, {}, token);
    return (result || []).map((x: any) => ({ article: x.article || { id: '', title: '' }, relevanceScore: x.relevance_score ?? 0, reason: x.reason || undefined }));
  }, [token]);

  const addKBArticle = useCallback(async (draft: any) => {
    if (!token) return;
    const article = await api<any>('/kb/articles', { method: 'POST', body: JSON.stringify({ title: draft.title, content: draft.content, summary: draft.summary || null, category_id: draft.categoryId || null, tags: draft.tags || [] }) }, token);
    if (draft.isPublished) {
      await api(`/kb/articles/${article.id}/status?status=review`, { method: 'POST' }, token);
      await api(`/kb/articles/${article.id}/status?status=approved`, { method: 'POST' }, token);
      await api(`/kb/articles/${article.id}/publish`, { method: 'POST' }, token);
    }
    await refresh();
  }, [token, refresh]);

  const updateKBArticle = useCallback(async (id: string, updates: Partial<KBArticle>) => {
    if (!token) return;
    const body: any = {};
    if (updates.title !== undefined) body.title = updates.title;
    if (updates.content !== undefined) body.content = updates.content;
    if (updates.summary !== undefined) body.summary = updates.summary || null;
    if (updates.categoryId !== undefined) body.category_id = updates.categoryId || null;
    if (updates.tags !== undefined) body.tags = updates.tags;
    await api(`/kb/articles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }, token);
    if (updates.isPublished) {
      const current = kbArticles.find(a => a.id === id);
      if (current && !current.isPublished) {
        await api(`/kb/articles/${id}/status?status=review`, { method: 'POST' }, token);
        await api(`/kb/articles/${id}/status?status=approved`, { method: 'POST' }, token);
        await api(`/kb/articles/${id}/publish`, { method: 'POST' }, token);
      }
    }
    await refresh();
  }, [token, refresh, kbArticles]);

  const deleteKBArticle = useCallback(async (id: string) => { if (!token) return; await api(`/kb/articles/${id}`, { method: 'DELETE' }, token); await refresh(); }, [token, refresh]);

  const value = useMemo(() => ({ currentAgent, permissions, agents, categories, tickets, kbArticles, clusters, analytics, overview, notifications, loading, error, login, logout, refresh, addTicket, updateTicket, addResponse, generateDraft, addKBArticle, updateKBArticle, deleteKBArticle, markNotificationRead, markAllNotificationsRead, generateSummary, classifyTicket, getSimilarTickets, getKBSuggestions }), [currentAgent, permissions, agents, categories, tickets, kbArticles, clusters, analytics, overview, notifications, loading, error, login, logout, refresh, addTicket, updateTicket, addResponse, generateDraft, addKBArticle, updateKBArticle, deleteKBArticle, markNotificationRead, markAllNotificationsRead, generateSummary, classifyTicket, getSimilarTickets, getKBSuggestions]);
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() { const context = useContext(AppContext); if (!context) throw new Error('useApp must be used within AppProvider'); return context; }
