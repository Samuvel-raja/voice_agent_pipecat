export function LogPanel({ logs }) {
  return (
    <div className="log">
      {logs.slice(-200).map((l, i) => (
        <div key={i}>{l}</div>
      ))}
    </div>
  );
}
