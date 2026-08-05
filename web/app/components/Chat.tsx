"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { sendMessage } from "../lib/api";
import type { ChatMessage, SessionStateView } from "../lib/types";
import Composer from "./Composer";
import EmptyState from "./EmptyState";
import MessageBubble from "./MessageBubble";
import StatusStrip from "./StatusStrip";

const SESSION_KEY = "trendly_session_id";

function newSessionId(): string {
  return crypto.randomUUID();
}

function readOrCreateSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const id = newSessionId();
  sessionStorage.setItem(SESSION_KEY, id);
  return id;
}

/** sessionStorage has no change events; reset bumps this to re-subscribe. */
let sessionVersion = 0;
const sessionListeners = new Set<() => void>();

function subscribeSession(onStoreChange: () => void): () => void {
  sessionListeners.add(onStoreChange);
  return () => {
    sessionListeners.delete(onStoreChange);
  };
}

function bumpSessionStore(): void {
  sessionVersion += 1;
  for (const listener of sessionListeners) listener();
}

function getSessionSnapshot(): string {
  void sessionVersion;
  return readOrCreateSessionId();
}

export default function Chat() {
  const sessionId = useSyncExternalStore(
    subscribeSession,
    getSessionSnapshot,
    () => "",
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState<SessionStateView | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  function resetSession() {
    sessionStorage.setItem(SESSION_KEY, newSessionId());
    setMessages([]);
    setState(null);
    setError(null);
    bumpSessionStore();
  }

  async function handleSend(text: string) {
    if (!sessionId || pending) return;
    setError(null);
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: text },
    ]);
    setPending(true);
    try {
      const res = await sendMessage(sessionId, text);
      setState(res.state);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.reply,
          trace: res.trace,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex h-dvh flex-col">
      <header className="shrink-0 border-b border-[var(--border)]/80 bg-[var(--paper)]/75 px-4 py-3.5 backdrop-blur-sm">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-3">
          <div>
            <h1 className="font-display text-xl font-medium tracking-tight text-[var(--ink)]">
              Trendly
            </h1>
            <p className="text-xs text-[var(--muted)]">Support assistant</p>
          </div>
          <button
            type="button"
            onClick={resetSession}
            className="rounded-md border border-transparent px-2.5 py-1.5 text-xs text-[var(--muted)] transition-colors hover:border-[var(--border)] hover:text-[var(--ink)]"
          >
            New conversation
          </button>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col overflow-hidden px-4">
        <div className="flex-1 space-y-4 overflow-y-auto py-5">
          {messages.length === 0 && !pending && (
            <EmptyState onPick={handleSend} />
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {pending && (
            <div className="message-enter text-sm text-[var(--muted)]">
              Looking that up…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <StatusStrip state={state} error={error} />
        <div className="shrink-0 pb-5 pt-1">
          <Composer disabled={pending || !sessionId} onSend={handleSend} />
        </div>
      </div>
    </div>
  );
}
