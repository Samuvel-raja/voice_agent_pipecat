import React from "react";

export function TeachingPanel({ latest, events, streamConnected, streamError }) {
  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <div style={styles.title}>Live Teaching</div>
        <div style={styles.status}>
          <span
            style={{
              ...styles.dot,
              background: streamConnected ? "#31b96c" : "rgba(49,185,108,0.25)",
            }}
          />
          <span style={styles.statusText}>
            {streamConnected ? "Streaming" : "Not streaming"}
          </span>
        </div>
      </div>

      {streamError && <div style={styles.error}>{streamError}</div>}

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Latest</div>
        {latest ? (
          <>
            <div style={styles.meta}>
              <div style={styles.metaLeft}>
                <span style={styles.badge}>{latest.language || "code"}</span>
                {typeof latest.step === "number" && (
                  <span style={styles.badge}>Step {latest.step}</span>
                )}
                {latest.kind && <span style={styles.badge}>{latest.kind}</span>}
              </div>
              {latest.title && <div style={styles.metaTitle}>{latest.title}</div>}
            </div>

            {latest.explanation && <div style={styles.explanation}>{latest.explanation}</div>}

            <pre style={styles.codeBlock}>
              <code>{latest.code || ""}</code>
            </pre>
          </>
        ) : (
          <div style={styles.empty}>Waiting for teaching snippets…</div>
        )}
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>History</div>
        <div style={styles.history}>
          {(events || []).slice(0, 10).map((e, idx) => (
            <div key={idx} style={styles.historyItem}>
              <div style={styles.historyTop}>
                <span style={styles.historyBadge}>{e.language || "code"}</span>
                {e.kind && <span style={styles.historyBadge}>{e.kind}</span>}
                {typeof e.step === "number" && (
                  <span style={styles.historyBadge}>Step {e.step}</span>
                )}
                <span style={styles.historyTs}>
                  {e.ts ? new Date(e.ts * 1000).toLocaleTimeString() : ""}
                </span>
              </div>
              {e.title && <div style={styles.historyTitle}>{e.title}</div>}
              {e.explanation && <div style={styles.historyExplanation}>{e.explanation}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: {
    width: "100%",
    background: "rgba(0,0,0,0.25)",
    border: "1px solid rgba(49,185,108,0.18)",
    borderRadius: 16,
    padding: 14,
    color: "rgba(215,255,233,0.9)",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: { fontSize: 13, fontWeight: 700, letterSpacing: "0.02em" },
  status: { display: "flex", alignItems: "center", gap: 6 },
  dot: { width: 7, height: 7, borderRadius: 99 },
  statusText: { fontSize: 11, opacity: 0.7 },
  error: {
    fontSize: 12,
    color: "rgba(252,165,165,0.9)",
    background: "rgba(239,68,68,0.08)",
    border: "1px solid rgba(239,68,68,0.2)",
    borderRadius: 10,
    padding: "8px 10px",
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  sectionTitle: { fontSize: 12, fontWeight: 700, opacity: 0.8 },
  meta: { display: "flex", flexDirection: "column", gap: 6 },
  metaLeft: { display: "flex", gap: 6, flexWrap: "wrap" },
  metaTitle: { fontSize: 12, opacity: 0.9 },
  badge: {
    fontSize: 11,
    padding: "2px 8px",
    borderRadius: 999,
    background: "rgba(49,185,108,0.16)",
    border: "1px solid rgba(49,185,108,0.25)",
    color: "rgba(215,255,233,0.9)",
  },
  explanation: {
    fontSize: 12,
    opacity: 0.8,
    lineHeight: 1.45,
  },
  codeBlock: {
    margin: 0,
    maxHeight: 220,
    overflow: "auto",
    padding: 12,
    borderRadius: 12,
    background: "rgba(0,0,0,0.35)",
    border: "1px solid rgba(49,185,108,0.14)",
    fontSize: 12,
    lineHeight: 1.45,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
    whiteSpace: "pre",
  },
  empty: { fontSize: 12, opacity: 0.6 },
  history: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    maxHeight: 180,
    overflow: "auto",
    paddingRight: 4,
  },
  historyItem: {
    padding: 10,
    borderRadius: 12,
    border: "1px solid rgba(49,185,108,0.12)",
    background: "rgba(0,0,0,0.2)",
  },
  historyTop: { display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" },
  historyBadge: {
    fontSize: 10,
    padding: "2px 6px",
    borderRadius: 999,
    background: "rgba(49,185,108,0.12)",
    border: "1px solid rgba(49,185,108,0.2)",
    opacity: 0.9,
  },
  historyTs: { fontSize: 10, opacity: 0.5, marginLeft: "auto" },
  historyTitle: { fontSize: 12, marginTop: 6, opacity: 0.9 },
  historyExplanation: { fontSize: 12, marginTop: 6, opacity: 0.7, lineHeight: 1.4 },
};
