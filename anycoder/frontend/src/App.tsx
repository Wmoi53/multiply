import { useEffect, useRef, useState } from "react";
import { deploy, fetchModels, streamGenerate } from "./api";

const LANGUAGE_LABELS: Record<string, string> = {
  html: "HTML",
  react: "React",
  "python-gradio": "Python (Gradio)",
  "python-streamlit": "Python (Streamlit)",
};

export default function App() {
  const [models, setModels] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);
  const [prompt, setPrompt] = useState("A pomodoro timer with start/pause/reset");
  const [model, setModel] = useState("DeepSeek V3");
  const [language, setLanguage] = useState("html");
  const [hfToken, setHfToken] = useState(() => localStorage.getItem("hf_token") ?? "");
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<"idle" | "generating" | "done" | "error">("idle");
  const [error, setError] = useState("");
  const [spaceName, setSpaceName] = useState("my-anycoder-app");
  const [deployedUrl, setDeployedUrl] = useState("");
  const [deploying, setDeploying] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchModels()
      .then((res) => {
        setModels(res.models);
        setLanguages(res.languages);
      })
      .catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    localStorage.setItem("hf_token", hfToken);
  }, [hfToken]);

  async function handleGenerate() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setCode("");
    setError("");
    setDeployedUrl("");
    setStatus("generating");

    await streamGenerate({
      prompt,
      model,
      language,
      hfToken,
      signal: controller.signal,
      onToken: (token) => setCode((prev) => prev + token),
      onError: (message) => {
        setError(message);
        setStatus("error");
      },
      onDone: () => setStatus("done"),
    });
  }

  async function handleDeploy() {
    setDeploying(true);
    setError("");
    try {
      const url = await deploy(code, spaceName, language, hfToken);
      setDeployedUrl(url);
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setDeploying(false);
    }
  }

  const isHtmlPreviewable = language === "html" && code.length > 0;

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>AnyCoder-lite</h1>
        <p style={styles.subtitle}>
          Minimal clone of{" "}
          <a href="https://huggingface.co/spaces/akhaliq/anycoder" target="_blank" rel="noreferrer">
            akhaliq/anycoder
          </a>{" "}
          — describe an app, stream code from a Hugging Face model, deploy it as a Space.
        </p>
      </header>

      <main style={styles.main}>
        <section style={styles.panel}>
          <label style={styles.label}>
            HF token (dev mode — stays in your browser's localStorage, sent per-request)
            <input
              type="password"
              value={hfToken}
              onChange={(e) => setHfToken(e.target.value)}
              placeholder="hf_xxx (optional if the server has HF_TOKEN set)"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Model
            <select value={model} onChange={(e) => setModel(e.target.value)} style={styles.input}>
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <label style={styles.label}>
            Output format
            <select value={language} onChange={(e) => setLanguage(e.target.value)} style={styles.input}>
              {languages.map((lang) => (
                <option key={lang} value={lang}>
                  {LANGUAGE_LABELS[lang] ?? lang}
                </option>
              ))}
            </select>
          </label>

          <label style={styles.label}>
            Describe the app you want
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={5}
              style={{ ...styles.input, resize: "vertical" as const }}
            />
          </label>

          <button
            onClick={handleGenerate}
            disabled={status === "generating" || !prompt.trim()}
            style={styles.primaryButton}
          >
            {status === "generating" ? "Generating…" : "Generate"}
          </button>

          {code && status !== "generating" && (
            <div style={styles.deployRow}>
              <input
                value={spaceName}
                onChange={(e) => setSpaceName(e.target.value)}
                placeholder="space-name"
                style={styles.input}
              />
              <button onClick={handleDeploy} disabled={deploying} style={styles.secondaryButton}>
                {deploying ? "Deploying…" : "Deploy to Space"}
              </button>
            </div>
          )}

          {deployedUrl && (
            <p style={styles.success}>
              Deployed:{" "}
              <a href={deployedUrl} target="_blank" rel="noreferrer">
                {deployedUrl}
              </a>
            </p>
          )}
          {error && <p style={styles.errorText}>{error}</p>}
        </section>

        <section style={styles.outputPanel}>
          <div style={styles.outputHeader}>
            <span>{LANGUAGE_LABELS[language] ?? language} output</span>
            {code && (
              <button onClick={() => navigator.clipboard.writeText(code)} style={styles.copyButton}>
                Copy
              </button>
            )}
          </div>
          <pre style={styles.codeBlock}>
            <code>{code || "// generated code will stream in here"}</code>
          </pre>
          {isHtmlPreviewable && (
            <>
              <div style={styles.outputHeader}>Live preview</div>
              <iframe title="preview" srcDoc={code} style={styles.preview} sandbox="allow-scripts" />
            </>
          )}
        </section>
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { fontFamily: "system-ui, sans-serif", maxWidth: 1100, margin: "0 auto", padding: "24px 16px", color: "#1a1a1a" },
  header: { marginBottom: 24 },
  title: { fontSize: 28, margin: 0 },
  subtitle: { color: "#555", marginTop: 4 },
  main: { display: "grid", gridTemplateColumns: "minmax(280px, 380px) 1fr", gap: 24 },
  panel: { display: "flex", flexDirection: "column", gap: 14 },
  label: { display: "flex", flexDirection: "column", gap: 4, fontSize: 13, fontWeight: 600, color: "#333" },
  input: { padding: "8px 10px", fontSize: 14, borderRadius: 8, border: "1px solid #ccc", fontFamily: "inherit" },
  primaryButton: {
    padding: "10px 16px",
    fontSize: 15,
    fontWeight: 600,
    borderRadius: 8,
    border: "none",
    background: "#4f46e5",
    color: "#fff",
    cursor: "pointer",
  },
  secondaryButton: {
    padding: "8px 14px",
    fontSize: 14,
    borderRadius: 8,
    border: "1px solid #4f46e5",
    background: "#fff",
    color: "#4f46e5",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  deployRow: { display: "flex", gap: 8 },
  copyButton: {
    padding: "4px 10px",
    fontSize: 12,
    borderRadius: 6,
    border: "1px solid #ccc",
    background: "#f5f5f5",
    cursor: "pointer",
  },
  success: { color: "#166534", fontSize: 13 },
  errorText: { color: "#b91c1c", fontSize: 13, whiteSpace: "pre-wrap" },
  outputPanel: { display: "flex", flexDirection: "column", gap: 8, minWidth: 0 },
  outputHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 13,
    fontWeight: 600,
    color: "#333",
  },
  codeBlock: {
    background: "#0f172a",
    color: "#e2e8f0",
    padding: 16,
    borderRadius: 8,
    overflow: "auto",
    maxHeight: 400,
    fontSize: 13,
    margin: 0,
  },
  preview: { width: "100%", height: 400, border: "1px solid #ccc", borderRadius: 8, background: "#fff" },
};
