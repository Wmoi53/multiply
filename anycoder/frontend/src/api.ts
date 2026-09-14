export interface ModelsResponse {
  models: string[];
  languages: string[];
}

export async function fetchModels(): Promise<ModelsResponse> {
  const res = await fetch("/api/models");
  if (!res.ok) throw new Error(`GET /api/models failed: ${res.status}`);
  return res.json();
}

interface GenerateOptions {
  prompt: string;
  model: string;
  language: string;
  hfToken: string;
  onToken: (token: string) => void;
  onError: (message: string) => void;
  onDone: () => void;
  signal?: AbortSignal;
}

/**
 * Streams generated code from POST /api/generate, which emits Server-Sent
 * Events. `fetch` (not EventSource) is used because EventSource can't send
 * a POST body; SSE framing ("data: {...}\n\n") is parsed manually below.
 */
export async function streamGenerate(opts: GenerateOptions): Promise<void> {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: opts.prompt,
      model: opts.model,
      language: opts.language,
      hf_token: opts.hfToken || null,
    }),
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    opts.onError(detail.detail ?? `HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const line = rawEvent.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;

      const payload = JSON.parse(line.slice("data: ".length));
      if (payload.error) {
        opts.onError(payload.error);
      } else if (payload.done) {
        opts.onDone();
      } else if (payload.token) {
        opts.onToken(payload.token);
      }
    }
  }
}

export async function deploy(code: string, spaceName: string, language: string, hfToken: string): Promise<string> {
  const res = await fetch("/api/deploy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, space_name: spaceName, language, hf_token: hfToken || null }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return data.space_url;
}
