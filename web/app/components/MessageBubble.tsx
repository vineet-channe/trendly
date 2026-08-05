"use client";

import { formatReply } from "../lib/format";
import type { ChatMessage } from "../lib/types";
import TracePanel from "./TracePanel";

type Props = {
  message: ChatMessage;
};

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const { html } = formatReply(message.content);

  return (
    <div
      className={`message-enter flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] sm:max-w-[75%] ${
          isUser
            ? "rounded-2xl rounded-br-md bg-[var(--accent)] px-4 py-2.5 text-white"
            : "rounded-2xl rounded-bl-md bg-white/90 px-4 py-2.5 text-[var(--ink)] shadow-sm ring-1 ring-[var(--border)]"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
            {message.content}
          </p>
        ) : (
          <p
            className="whitespace-pre-wrap text-[15px] leading-relaxed [&_strong]:font-semibold"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
        {!isUser && message.trace && message.trace.length > 0 && (
          <TracePanel trace={message.trace} />
        )}
      </div>
    </div>
  );
}
