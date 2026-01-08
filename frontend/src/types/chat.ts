export interface Citation {
  section: string;
  page: number;
  doc_version: string;
  chunk_id?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: 'high' | 'medium' | 'low';
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatRequest {
  session_id: string;
  user_query: string;
  doc_version?: string;
  stream?: boolean;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  confidence: 'high' | 'medium' | 'low';
}
