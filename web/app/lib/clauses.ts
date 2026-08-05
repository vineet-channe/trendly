/**
 * Pull clause IDs out of a tool output for the collapsed trace summary.
 * Covers check_eligibility.verdicts[].clause_ids and search_policy.results[].id.
 */

function walk(node: unknown, found: Set<string>): void {
  if (node == null || typeof node !== "object") return;

  if (Array.isArray(node)) {
    for (const item of node) walk(item, found);
    return;
  }

  const obj = node as Record<string, unknown>;

  if (Array.isArray(obj.clause_ids)) {
    for (const id of obj.clause_ids) {
      if (typeof id === "string" && id.length > 0) found.add(id);
    }
  }

  if (typeof obj.id === "string" && /^\d+(\.\d+)?$/.test(obj.id)) {
    found.add(obj.id);
  }

  for (const value of Object.values(obj)) walk(value, found);
}

export function extractClauseIds(output: unknown): string[] {
  const found = new Set<string>();
  walk(output, found);
  return Array.from(found).sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true }),
  );
}

export function clausesFromTrace(
  trace: { output: Record<string, unknown> }[],
): string[] {
  const found = new Set<string>();
  for (const entry of trace) {
    for (const id of extractClauseIds(entry.output)) found.add(id);
  }
  return Array.from(found).sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true }),
  );
}
