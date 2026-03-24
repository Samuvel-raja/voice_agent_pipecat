export async function createWebRTCConnection({
  onLog,
  onError,
  onRemoteStream,
}) {
  let pc = null;
  let localStream = null;
  let pcId = null;
  let pendingCandidates = [];
  let flushCandidatesTimer = null;

  const log = (m) => onLog && onLog(m);
  const err = (m) => onError && onError(m);

  async function flushCandidates() {
    if (!pcId || pendingCandidates.length === 0) return;
    const candidates = pendingCandidates;
    pendingCandidates = [];

    const r = await fetch("/webrtc/offer", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pc_id: pcId, candidates }),
    });

    if (!r.ok) {
      const t = await r.text();
      throw new Error(`ICE PATCH failed: HTTP ${r.status} ${t}`);
    }
  }

  function scheduleFlushCandidates() {
    if (flushCandidatesTimer) return;
    flushCandidatesTimer = window.setTimeout(async () => {
      flushCandidatesTimer = null;
      try {
        await flushCandidates();
      } catch {
        // ignore
      }
    }, 250);
  }

  async function start() {
    log("Requesting microphone...");
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    log("Creating RTCPeerConnection...");
    pc = new RTCPeerConnection();

    pc.ontrack = (event) => {
      const [stream] = event.streams;
      if (stream) {
        log("Remote audio stream received.");
        onRemoteStream && onRemoteStream(stream);
      }
    };

    pc.onicecandidate = (event) => {
      if (!event.candidate) return;
      pendingCandidates.push({
        candidate: event.candidate.candidate,
        sdp_mid: event.candidate.sdpMid || "0",
        sdp_mline_index: event.candidate.sdpMLineIndex || 0,
      });
      scheduleFlushCandidates();
    };

    for (const track of localStream.getTracks()) {
      pc.addTrack(track, localStream);
    }

    const offer = await pc.createOffer({ offerToReceiveAudio: true });
    await pc.setLocalDescription(offer);

    log("Sending SDP offer...");
    const resp = await fetch("/webrtc/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sdp: offer.sdp,
        type: offer.type,
        pc_id: null,
        restart_pc: null,
        request_data: null,
      }),
    });

    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`Offer failed: HTTP ${resp.status} ${t}`);
    }

    const answer = await resp.json();
    pcId = answer.pc_id || answer.pcId || pcId;

    if (!answer?.sdp || !answer?.type) {
      throw new Error("Offer response missing answer sdp/type");
    }

    log(`Received answer${pcId ? ` (pc_id ${pcId})` : ""}.`);
    await pc.setRemoteDescription({ type: answer.type, sdp: answer.sdp });

    await flushCandidates();
  }

  async function stop() {
    try {
      if (flushCandidatesTimer) {
        window.clearTimeout(flushCandidatesTimer);
        flushCandidatesTimer = null;
      }
      pendingCandidates = [];
      pcId = null;

      if (pc) {
        try {
          pc.close();
        } catch {
          // ignore
        }
        pc = null;
      }

      if (localStream) {
        for (const t of localStream.getTracks()) t.stop();
        localStream = null;
      }
    } catch (e) {
      err(String(e));
    }
  }

  return { start, stop };
}
