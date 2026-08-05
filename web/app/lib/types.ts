/** Mirrors FastAPI ChatResponse / SessionStateView (SRS §5.1). */

export type TraceEntry = {
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
};

export type SessionStateView = {
  verified: boolean;
  active_order: string | null;
  escalated: boolean;
};

export type ChatResponse = {
  session_id: string;
  reply: string;
  state: SessionStateView;
  trace: TraceEntry[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  trace?: TraceEntry[];
};
