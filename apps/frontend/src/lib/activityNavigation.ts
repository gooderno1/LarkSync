function paramsFromHash(hash: string): URLSearchParams {
  const query = hash.split("?", 2)[1] || "";
  return new URLSearchParams(query);
}

export function parseActivityLink(hash: string) {
  const params = paramsFromHash(hash);
  return {
    taskId: params.get("task_id"),
    runId: params.get("run_id"),
    eventId: params.get("event_id"),
  };
}

export function parseProblemLink(hash: string) {
  const params = paramsFromHash(hash);
  return {
    taskId: params.get("task_id"),
    runId: params.get("run_id"),
    problemId: params.get("problem_id"),
    category: params.get("type") === "conflict" ? "conflict" : params.get("category"),
  };
}
