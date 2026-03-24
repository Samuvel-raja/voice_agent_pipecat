import { useRef, useState } from "react";
import "./App.css";

import { connectBot, disconnectBot, getStatus } from "./api/botApi";
import { createWebRTCConnection } from "./services/webrtc/createWebRTCConnection";
import { Controls } from "./components/Controls";
import { StatusBar } from "./components/StatusBar";
import { AudioPlayer } from "./components/AudioPlayer";
import { LogPanel } from "./components/LogPanel";
import { useLogs } from "./hooks/useLogs";
import { useSpeechRecognition } from "./hooks/useSpeechRecognition";

function App() {
  const [status, setStatus] = useState({ running: false, pid: null });
  const [busy, setBusy] = useState(false);
  const { logs, addLog, addError } = useLogs(["Ready."]);
  const audioRef = useRef(null);
  const webrtcRef = useRef(null);
  const speech = useSpeechRecognition({
    onFinalText: (text) => addLog(`You said: ${text}`),
    onError: (e) => addError(`Speech recognition error: ${e}`),
  });

  async function refreshStatus() {
    try {
      const s = await getStatus();
      setStatus({ running: !!s.running, pid: s.pid ?? null });
    } catch {
      // ignore
    }
  }

  async function startSession() {
    setBusy(true);
    addLog("Requesting session from server...");
    try {
      const data = await connectBot();

      addLog(
        data.already_running
          ? `Already running (pid ${data.pid})`
          : `Started (pid ${data.pid}) with ${data.transport} transport`
      );

      setStatus({ running: true, pid: data.pid ?? null });

      addLog("Starting WebRTC (mic + remote audio)...");
      const conn = await createWebRTCConnection({
        onLog: addLog,
        onError: addError,
        onRemoteStream: (stream) => {
          if (audioRef.current) {
            audioRef.current.srcObject = stream;
          }
        },
      });

      webrtcRef.current = conn;
      await conn.start();
      addLog("WebRTC connected.");

      speech.start();
      if (speech.listening) {
        addLog("Speech recognition started.");
      }
    } catch (e) {
      addError(String(e?.message || e));
      try {
        await webrtcRef.current?.stop();
      } catch {
        // ignore
      }
      webrtcRef.current = null;
      speech.stop();
    } finally {
      setBusy(false);
      refreshStatus();
    }
  }

  async function stopSession() {
    setBusy(true);
    addLog("Stopping session...");
    try {
      speech.stop();

      try {
        await webrtcRef.current?.stop();
      } catch {
        // ignore
      }
      webrtcRef.current = null;
      if (audioRef.current) audioRef.current.srcObject = null;

      const data = await disconnectBot();
      addLog(data.stopped ? "Stopped." : "Nothing running.");
    } catch (e) {
      addError(String(e?.message || e));
    } finally {
      setBusy(false);
      refreshStatus();
    }
  }

  return (
    <div className="App">
      <div className="card">
        <h1>Pipecat Voice (React)</h1>

        <StatusBar running={status.running} pid={status.pid} listening={speech.listening} />
        <Controls
          onStart={startSession}
          onStop={stopSession}
          onRefresh={refreshStatus}
          busy={busy}
          running={status.running}
        />
        <AudioPlayer audioRef={audioRef} />
        <LogPanel logs={logs} />
      </div>
    </div>
  );
}

export default App;
