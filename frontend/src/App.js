import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import '@pipecat-ai/voice-ui-kit/styles';

import { useEffect, useRef, useState, useCallback } from 'react';
import { ThemeProvider } from '@pipecat-ai/voice-ui-kit';
import { Plasma } from '@pipecat-ai/voice-ui-kit/webgl';

import { connectSession, disconnectBot } from './api/botApi';
import { createWebRTCConnection } from './services/webrtc/createWebRTCConnection';
import { TeachingPanel } from './components/TeachingPanel';
import { useTeachingStream } from './hooks/useTeachingStream';

const PLASMA_CONFIG = {
  intensity: 2.4,
  radius: 1.55,
  effectScale: 0.72,
  ringCount: 7,
  ringVisibility: 0.88,
  ringDistance: 0.038,
  ringBounce: 0.38,
  ringThickness: 12,
  ringVariance: 0.58,
  ringAmplitude: 0.14,
  ringSpeed: 2.4,
  ringSegments: 9,
  colorCycleSpeed: 0.65,
  plasmaSpeed: 1.7,
  useCustomColors: true,
  color1: '#31b96c',
  color2: '#d7ffe9',
  color3: '#062012',
  backgroundColor: 'transparent',
  glowFalloff: 2.4,
  glowThreshold: 0.016,
  audioEnabled: true,
  audioSensitivity: 1.8,
  audioSmoothing: 0.82,
  frequencyBands: 32,
  bassResponse: 1.8,
  midResponse: 1.3,
  trebleResponse: 1.0,
  plasmaVolumeReactivity: 3.2,
  volumeThreshold: 0.08,
};

export default function App() {
  const plasmaRef = useRef(null);
  const audioRef = useRef(null);
  const webrtcRef = useRef(null);

  const [audioTrack, setAudioTrack] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [activeMode, setActiveMode] = useState(null);

  const [teachTopic, setTeachTopic] = useState('Implement a queue using two stacks');
  const [teachLanguage, setTeachLanguage] = useState('Python');

  const teaching = useTeachingStream(sessionId);

  useEffect(() => {
    return () => {
      try { webrtcRef.current?.stop?.(); } catch {}
      webrtcRef.current = null;
      if (audioRef.current) audioRef.current.srcObject = null;
    };
  }, []);

  const startInterview = useCallback(async (mode) => {
    setBusy(true);
    setError(null);
    try {
      setActiveMode(mode);
      const mockCandidate = {
        name: 'Priya Nair',
        email: 'priya@example.com',
        years_experience: 6,
        role_applied: 'Senior Backend Engineer',
      };

      const mockCompany = {
        name: 'Finmo',
        industry: 'Fintech / Payments Infrastructure',
        role_title: 'Senior Backend Engineer',
        jd_summary:
          'Finmo builds real-time cross-border payment rails. This role owns core transaction processing services, reliability, and incident response.',
        focus_areas: ['Distributed systems', 'API design', 'Observability', 'Payments pipelines'],
        tech_stack: ['Python', 'PostgreSQL', 'Kafka', 'Redis', 'Docker/Kubernetes'],
      };

      const mockQuestionsByMode = {
        general: [
          'Tell me about yourself and what you are working on right now?',
          'What kind of work environment helps you do your best work?',
          'Tell me about a time you handled a difficult stakeholder situation.',
          'What are you looking for in your next role?',
        ],
        technical: [
          'Walk me through a backend system you designed end-to-end for scale and reliability.',
          'How do you design idempotency and retries for payment APIs?',
          'Tell me about a production incident you handled and what you changed afterward.',
          'How do you approach database schema changes with zero downtime?',
        ],
        final: [
          'What are the most important signals you look for when hiring engineers?',
          'Tell me about a decision you made that had long-term architectural impact.',
          'How do you handle ambiguity when requirements are incomplete?',
          'What would you change about your leadership style as you grow?',
        ],
        teach_coding: [],
      };

      const metadata =
        mode === 'teach_coding'
          ? { topic: teachTopic, language: teachLanguage, duration_minutes: 30 }
          : {
              duration_minutes:
                mode === 'general' ? 15 : mode === 'technical' ? 25 : mode === 'final' ? 20 : 20,
            };

      const sessionRes = await connectSession({
        mode,
        candidate_name: mockCandidate.name,
        candidate: mockCandidate,
        company: mode === 'general' ? null : mockCompany,
        questions: mockQuestionsByMode[mode] || [],
        metadata,
      });

      const sessionId = sessionRes.session_id;
      if (!sessionId) throw new Error('No session_id returned from server');
      setSessionId(sessionId);

      const conn = await createWebRTCConnection({
        onLog: () => {},
        onError: (e) => setError(String(e?.message || e)),
        onRemoteStream: (stream) => {
          if (audioRef.current) audioRef.current.srcObject = stream;
          setAudioTrack(stream?.getAudioTracks?.()?.[0] || null);
        },
        sessionId,
      });
      webrtcRef.current = conn;
      await conn.start();
      setIsConnected(true);
    } catch (e) {
      setError(String(e?.message || e));
      try { await webrtcRef.current?.stop?.(); } catch {}
      webrtcRef.current = null;
      setSessionId(null);
      setActiveMode(null);
      setIsConnected(false);
      setAudioTrack(null);
      if (audioRef.current) audioRef.current.srcObject = null;
    } finally {
      setBusy(false);
    }
  }, [teachLanguage, teachTopic]);

  const disconnect = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      try { await webrtcRef.current?.stop?.(); } catch {}
      webrtcRef.current = null;
      setIsConnected(false);
      setAudioTrack(null);
      if (audioRef.current) audioRef.current.srcObject = null;
      if (sessionId) {
        await disconnectBot(sessionId);
      }
      setSessionId(null);
      setActiveMode(null);
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }, [sessionId]);

  return (
    <ThemeProvider>
      <div style={styles.root}>

        {/* Ambient background glow */}
        <div style={styles.ambientGlow} />

        <div style={styles.card}>
          {/* Plasma stage */}
          <div style={styles.plasmaStage}>

            <div style={styles.plasmaInnerGlow} />
            <Plasma
              ref={plasmaRef}
              initialConfig={PLASMA_CONFIG}
              audioTrack={audioTrack}
              width={460}
              height={260}
              // style={styles.plasmaCanvas}
            />

            {/* Status pill */}
            <div style={styles.statusPill}>
              <div style={{
                ...styles.statusDot,
                background: isConnected ? '#31b96c' : 'rgba(49,185,108,0.3)',
                boxShadow: isConnected ? '0 0 8px rgba(49,185,108,0.9)' : 'none',
              }} />
              <span style={styles.statusText}>
                {busy ? 'Connecting…' : isConnected ? 'Live' : 'Standby'}
              </span>
            </div>

            {/* Bottom gradient fade */}
            <div style={styles.stageFade} />
          </div>

          {/* Panel */}
          <div style={styles.panel}>
            <div style={styles.panelHeader}>

              <div>
                <div style={styles.appName}>Voice Assistant</div>
                <div style={styles.appSub}>Plasma Audio Interface</div>
              </div>
              <div style={styles.indicators}>
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    style={{
                      ...styles.indicator,
                      background: isConnected
                        ? `rgba(49,185,108,${0.4 + i * 0.2})`
                        : 'rgba(49,185,108,0.12)',
                      boxShadow: isConnected
                        ? `0 0 ${6 + i * 3}px rgba(49,185,108,0.6)`
                        : 'none',
                      transition: `all 0.4s ease ${i * 0.1}s`,
                    }}
                  />
                ))}
              </div>
            </div>

            <div style={styles.divider} />

            {/* Teach-coding inputs */}
            <div style={styles.teachBox}>
              <div style={styles.teachTitle}>Teach Coding Setup</div>
              <input
                value={teachTopic}
                onChange={(e) => setTeachTopic(e.target.value)}
                placeholder="Coding problem / prompt"
                disabled={busy || isConnected}
                style={styles.input}
              />
              <input
                value={teachLanguage}
                onChange={(e) => setTeachLanguage(e.target.value)}
                placeholder="Language (e.g. Python, JavaScript)"
                disabled={busy || isConnected}
                style={styles.input}
              />
            </div>

            <div style={styles.modeRow}>

              <button
                onClick={() => startInterview('general')}
                disabled={busy}
                style={{
                  ...styles.modeBtn,
                  ...styles.modeBtnActive,
                  opacity: busy ? 0.45 : 1,
                  cursor: busy ? 'not-allowed' : 'pointer',
                }}
              >
                General Interview
              </button>
              <button
                onClick={() => startInterview('technical')}
                disabled={busy}
                style={{
                  ...styles.modeBtn,
                  ...styles.modeBtnActive,
                  opacity: busy ? 0.45 : 1,
                  cursor: busy ? 'not-allowed' : 'pointer',
                }}
              >
                Technical Interview
              </button>
              <button
                onClick={() => startInterview('final')}
                disabled={busy}
                style={{
                  ...styles.modeBtn,
                  ...styles.modeBtnActive,
                  opacity: busy ? 0.45 : 1,
                  cursor: busy ? 'not-allowed' : 'pointer',
                }}
              >
                Final Interview
              </button>
              <button
                onClick={() => startInterview('teach_coding')}
                disabled={busy}
                style={{
                  ...styles.modeBtn,
                  ...styles.modeBtnActive,
                  opacity: busy ? 0.45 : 1,
                  cursor: busy ? 'not-allowed' : 'pointer',
                }}
              >
                Teach Coding
              </button>
            </div>

            <div style={styles.btnRow}>
              <button
                onClick={disconnect}
                disabled={busy || !isConnected}
                style={{
                  ...styles.btn,
                  ...styles.btnDisconnect,
                  opacity: busy || !isConnected ? 0.35 : 1,
                  cursor: busy || !isConnected ? 'not-allowed' : 'pointer',
                }}
              >
                Disconnect
              </button>
            </div>

            {/* Error message */}
            {error && (
              <div style={styles.errorBox}>
                <span style={styles.errorDot}>●</span>
                {error}
              </div>
            )}

            {isConnected && activeMode === 'teach_coding' && sessionId && (
              <TeachingPanel
                latest={teaching.latest}
                events={teaching.events}
                streamConnected={teaching.connected}
                streamError={teaching.error}
              />
            )}
          </div>
        </div>

        <audio ref={audioRef} autoPlay playsInline />
      </div>
    </ThemeProvider>
  );
}

const styles = {
  root: {
    width: '100%',
    height: '100dvh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#060f0a',
    fontFamily: "'Geist Variable', system-ui, sans-serif",
    position: 'relative',
    overflow: 'hidden',
  },
  ambientGlow: {
    position: 'absolute',
    top: '-20%',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '140%',
    height: '60%',
    background: 'radial-gradient(ellipse at center, rgba(49,185,108,0.07) 0%, transparent 65%)',
    pointerEvents: 'none',
  },
  card: {
    width: '100%',
    maxWidth: 460,
    background: 'rgba(6,18,11,0.88)',
    border: '1px solid rgba(49,185,108,0.2)',
    borderRadius: 24,
    overflow: 'hidden',
    backdropFilter: 'blur(32px)',
    boxShadow: [
      '0 0 0 1px rgba(49,185,108,0.05)',
      '0 32px 80px rgba(0,0,0,0.75)',
      '0 0 60px rgba(49,185,108,0.04) inset',
    ].join(', '),
  },
  plasmaStage: {
    position: 'relative',
    height: 260,
    background: '#040d08',
    overflow: 'hidden',
  },
  plasmaInnerGlow: {
    position: 'absolute',
    inset: 0,
    background: 'radial-gradient(ellipse 70% 60% at 50% 45%, rgba(49,185,108,0.08), transparent 70%)',
    pointerEvents: 'none',
    zIndex: 1,
  },
  plasmaCanvas: {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
  },
  stageFade: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 56,
    background: 'linear-gradient(to top, rgba(6,18,11,0.9) 0%, transparent 100%)',
    pointerEvents: 'none',
    zIndex: 2,
  },
  statusPill: {
    position: 'absolute',
    top: 14,
    right: 14,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '5px 12px',
    borderRadius: 100,
    background: 'rgba(0,0,0,0.6)',
    border: '1px solid rgba(49,185,108,0.2)',
    zIndex: 3,
    backdropFilter: 'blur(8px)',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    transition: 'background 0.4s, box-shadow 0.4s',
  },
  statusText: {
    fontSize: 11,
    fontWeight: 500,
    color: 'rgba(215,255,233,0.65)',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
  panel: {
    padding: '22px 24px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 18,
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  appName: {
    fontSize: 16,
    fontWeight: 600,
    color: '#d7ffe9',
    letterSpacing: '-0.02em',
    marginBottom: 2,
  },
  appSub: {
    fontSize: 12,
    color: 'rgba(215,255,233,0.35)',
    letterSpacing: '0.01em',
  },
  indicators: {
    display: 'flex',
    gap: 6,
    alignItems: 'center',
  },
  indicator: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    border: '1px solid rgba(49,185,108,0.25)',
  },
  divider: {
    height: 1,
    background: 'rgba(49,185,108,0.1)',
  },
  modeRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
  },
  modeBtn: {
    height: 36,
    borderRadius: 12,
    border: '1px solid rgba(49,185,108,0.18)',
    background: 'rgba(0,0,0,0.35)',
    color: 'rgba(215,255,233,0.7)',
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: '0.01em',
  },
  modeBtnActive: {
    background: 'rgba(49,185,108,0.18)',
    border: '1px solid rgba(49,185,108,0.35)',
    color: '#d7ffe9',
    boxShadow: '0 0 0 1px rgba(49,185,108,0.06) inset, 0 10px 22px rgba(49,185,108,0.08)',
  },
  btnRow: {
    display: 'flex',
    gap: 10,
  },
  btn: {
    flex: 1,
    height: 44,
    borderRadius: 12,
    fontSize: 13,
    fontWeight: 600,
    border: 'none',
    letterSpacing: '0.01em',
    transition: 'transform 0.15s, opacity 0.2s, box-shadow 0.2s',
  },
  btnConnect: {
    background: 'linear-gradient(135deg, #27a35d 0%, #1c8548 100%)',
    color: '#d7ffe9',
    boxShadow: '0 4px 20px rgba(49,185,108,0.28), 0 1px 0 rgba(255,255,255,0.07) inset',
  },
  btnDisconnect: {
    background: 'rgba(239,68,68,0.1)',
    color: 'rgba(252,165,165,0.85)',
    border: '1px solid rgba(239,68,68,0.2)',
  },
  errorBox: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    fontSize: 12,
    color: 'rgba(252,165,165,0.85)',
    background: 'rgba(239,68,68,0.07)',
    border: '1px solid rgba(239,68,68,0.18)',
    borderRadius: 10,
    padding: '10px 14px',
    lineHeight: 1.5,
  },
  errorDot: {
    fontSize: 8,
    color: 'rgba(239,68,68,0.7)',
    marginTop: 3,
    flexShrink: 0,
  },
  teachBox: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    padding: 12,
    borderRadius: 14,
    background: 'rgba(0,0,0,0.25)',
    border: '1px solid rgba(49,185,108,0.14)',
  },
  teachTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: 'rgba(215,255,233,0.8)',
    letterSpacing: '0.01em',
  },
  input: {
    height: 36,
    borderRadius: 12,
    border: '1px solid rgba(49,185,108,0.18)',
    background: 'rgba(0,0,0,0.35)',
    color: 'rgba(215,255,233,0.85)',
    padding: '0 12px',
    outline: 'none',
    fontSize: 12,
  },
};