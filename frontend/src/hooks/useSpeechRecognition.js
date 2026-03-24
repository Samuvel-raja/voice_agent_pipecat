import { useCallback, useRef, useState } from "react";

export function useSpeechRecognition({ onFinalText, onError, lang = "en-US" }) {
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);

  const start = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition || null;

    if (!SpeechRecognition) {
      onError && onError("Speech recognition not supported in this browser.");
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang;

    rec.onresult = (event) => {
      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const res = event.results[i];
        if (res.isFinal) {
          finalText += res[0]?.transcript || "";
        }
      }
      const text = finalText.trim();
      if (text) onFinalText && onFinalText(text);
    };

    rec.onerror = (e) => {
      onError && onError(e?.error || "unknown");
    };

    rec.onend = () => {
      setListening(false);
    };

    recRef.current = rec;

    try {
      rec.start();
      setListening(true);
    } catch {
      recRef.current = null;
      setListening(false);
    }
  }, [lang, onError, onFinalText]);

  const stop = useCallback(() => {
    try {
      recRef.current?.stop();
    } catch {
      // ignore
    }
    recRef.current = null;
    setListening(false);
  }, []);

  return { listening, start, stop };
}
