import { API_ROUTES } from "./routes";
import { requestJson } from "./http";

export async function sendOffer(payload, sessionId) {
  return requestJson(`${API_ROUTES.webrtcOffer}?session_id=${sessionId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendIceCandidates(payload, sessionId) {
  return requestJson(`${API_ROUTES.webrtcOffer}?session_id=${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
