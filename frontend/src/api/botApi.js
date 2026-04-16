import { API_ROUTES } from "./routes";
import { requestJson } from "./http";

export async function connectSession(sessionConfig) {
  return requestJson(API_ROUTES.connectSession, {
    method: "POST",
    body: JSON.stringify(sessionConfig),
  });
}

export async function disconnectBot(sessionId) {
  return requestJson(`${API_ROUTES.disconnect}?session_id=${sessionId}`, {
    method: "POST",
  });
}
