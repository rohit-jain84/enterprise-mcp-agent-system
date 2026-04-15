export interface Session {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  status: 'active' | 'completed' | 'archived';
  summary?: string;
  tags?: string[];
}

export interface SessionCreate {
  title?: string;
  tags?: string[];
}
