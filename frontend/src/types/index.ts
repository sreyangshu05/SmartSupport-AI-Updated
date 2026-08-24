export type TicketStatus = 'open' | 'in_progress' | 'waiting_for_customer' | 'waiting_for_internal' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';
export type AgentRole = 'admin' | 'senior_agent' | 'agent';

export interface Agent {
  id: string;
  email: string;
  fullName: string;
  role: AgentRole;
  isActive: boolean;
  createdAt: string;
  lastActiveAt?: string;
  openTicketCount?: number;
}

export interface TicketCategory { id: string; name: string; description?: string; color: string; }
export interface TicketResponse { id: string; ticketId: string; content: string; isInternal: boolean; responseType?: string; authorName?: string; createdAt: string; }
export interface TicketEvent { id: string; eventType: string; oldValue?: string; newValue?: string; createdAt: string; }

export type SLABreachStatus = 'green' | 'warning' | 'breached';

export interface Ticket {
  id: string;
  ticketNumber: string;
  subject: string;
  description: string;
  summary?: string;
  status: TicketStatus;
  priority: TicketPriority;
  categoryId?: string;
  category?: TicketCategory;
  assignedTo?: string;
  assignedAgent?: Agent;
  createdBy: string;
  customerName?: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  closedAt?: string;
  slaStatus?: SLABreachStatus;
  slaDueAt?: string;
  responses?: TicketResponse[];
  events?: TicketEvent[];
  tags?: string[];
  kbSuggestions?: KBSuggestion[];
}

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  message?: string;
  link?: string;
  readAt?: string;
  createdAt: string;
}

export interface SimilarTicket {
  ticket: Ticket;
  similarityScore: number;
}

export interface AIClassification {
  category?: { id: string; name: string };
  categoryId?: string;
  confidence: number;
  lowConfidence: boolean;
  reasoning?: string;
}

export interface KBArticle {
  id: string;
  title: string;
  content: string;
  summary?: string;
  categoryId?: string;
  category?: TicketCategory;
  tags?: string[];
  viewCount: number;
  helpfulCount: number;
  usageCount: number;
  isPublished: boolean;
  status: string;
  createdBy?: string;
  createdByAgent?: Agent;
  createdAt: string;
  updatedAt: string;
  currentVersion?: number;
}

export interface KBArticleRef { id: string; title: string; summary?: string; }
export interface KBSuggestion { article: KBArticleRef; relevanceScore: number; reason?: string; }
export interface TicketCluster { id: string; name: string; description?: string; ticketCount: number; firstSeen?: string; lastSeen?: string; isTrending: boolean; }
export interface AgentAnalytics { id: string; agentId: string; date: string; ticketsCreated: number; ticketsResolved: number; avgResponseTimeMinutes?: number; avgResolutionTimeMinutes?: number; totalResponses: number; kbArticlesCreated: number; }
export interface AnalyticsOverview { totalTickets: number; openTickets: number; inProgressTickets: number; resolvedTickets: number; avgResolutionMinutes?: number; avgFirstResponseMinutes?: number; ticketsByStatus: Record<string, number>; ticketsByPriority: Record<string, number>; ticketsByCategory: Record<string, number>; }
