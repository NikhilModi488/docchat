export interface Citation {
  doc_id: string;
  filename: string;
  page: number;
  score: number;
  chunk_id: string;
  preview: string;
}

export interface Chunk {
  doc_id: string;
  chunk_id: string;
  filename: string;
  page: number;
  score: number;
  content: string;
}

export interface RagasScore {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
}

export interface TokenUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  language?: string;
  citations?: Citation[];
  chunks?: Chunk[];
  recommendation_questions?: string[];
  ragas_score?: RagasScore;
  token_usage?: TokenUsage;
  response_time?: number;
  created_at?: string;
  streaming?: boolean;
  feedback?: "up" | "down" | null;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  pages: number;
  chunk_count: number;
  status: string;
  error?: string;
  upload_time?: string;
}

export interface Analytics {
  total_documents: number;
  total_chunks: number;
  total_conversations: number;
  average_response_time: number;
  average_ragas: RagasScore;
  token_usage: TokenUsage;
  top_questions: { question: string; count: number }[];
  feedback: { up: number; down: number };
}

export interface HealthInfo {
  status: string;
  ollama_available: boolean;
  models: string[];
  default_model: string;
  embedding_model: string;
  chunks_indexed: number;
  require_auth: boolean;
}
