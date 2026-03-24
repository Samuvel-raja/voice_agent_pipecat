export function Controls({ onStart, onStop, onRefresh, busy, running }) {
  return (
    <div className="buttons">
      <button onClick={onStart} disabled={busy || running}>
        Start Session
      </button>
      <button onClick={onStop} disabled={busy || !running}>
        End Session
      </button>
      <button onClick={onRefresh} disabled={busy}>
        Refresh
      </button>
    </div>
  );
}
