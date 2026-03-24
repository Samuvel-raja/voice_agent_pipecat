import { API_ROUTES } from "./routes";
import { requestJson } from "./http";

export async function sendOffer(payload) {
  return requestJson(API_ROUTES.webrtcOffer, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendIceCandidates(payload) {
  return requestJson(API_ROUTES.webrtcOffer, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
