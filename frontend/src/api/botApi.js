import { API_ROUTES } from "./routes";
import { requestJson } from "./http";

export async function getStatus() {
  return requestJson(API_ROUTES.status, { method: "GET" });
}

export async function connectBot() {
  return requestJson(API_ROUTES.connect, { method: "POST" });
}

export async function disconnectBot() {
  return requestJson(API_ROUTES.disconnect, { method: "POST" });
}
