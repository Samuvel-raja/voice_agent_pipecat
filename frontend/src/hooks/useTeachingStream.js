import { useEffect, useRef, useState } from "react";
import { API_ROUTES } from "../api/routes";

export function useTeachingStream(sessionId) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  const esRef = useRef(null);

  useEffect(() => {
    setEvents([]);
    setConnected(false);
    setError(null);

    if (!sessionId) return;

    const url = `${API_ROUTES.teachingStream}?session_id=${encodeURIComponent(sessionId)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
    };

    es.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        setEvents((prev) => [payload, ...prev].slice(0, 200));
      } catch (e) {
        // ignore malformed messages
      }
    };

    es.onerror = () => {
      setError("Teaching stream disconnected");
      setConnected(false);
    };

    return () => {
      try {
        es.close();
      } catch {}
      esRef.current = null;
    };
  }, [sessionId]);

  return {
    events,
    latest: events[0] || null,
    connected,
    error,
  };
}
