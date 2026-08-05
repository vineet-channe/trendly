/** Minimal reply formatting — bold only, no HTML from the model. */

export function formatReply(text: string): { html: string } {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const withBold = escaped.replace(
    /\*\*([^*]+)\*\*/g,
    "<strong>$1</strong>",
  );
  return { html: withBold };
}
