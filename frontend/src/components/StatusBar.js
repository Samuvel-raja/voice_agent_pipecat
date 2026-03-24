export function StatusBar({ running, pid, listening }) {
  return (
    <div className="status">
      <span className={running ? "dot on" : "dot"} />
      <span>
        {running ? `Running${pid ? ` (pid ${pid})` : ""}` : "Disconnected"}
      </span>
      <span style={{ marginLeft: "auto", opacity: 0.8 }}>
        {listening ? "Listening" : ""}
      </span>
    </div>
  );
}
