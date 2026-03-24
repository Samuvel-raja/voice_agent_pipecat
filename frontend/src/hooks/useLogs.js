import { useCallback, useState } from "react";

export function useLogs(initial = ["Ready."]) {
  const [logs, setLogs] = useState(initial);

  const addLog = useCallback((m) => {
    setLogs((l) => [...l, m]);
  }, []);

  const addError = useCallback((m) => {
    setLogs((l) => [...l, `ERROR: ${m}`]);
  }, []);

  const clear = useCallback(() => {
    setLogs([]);
  }, []);

  return { logs, addLog, addError, clear };
}
