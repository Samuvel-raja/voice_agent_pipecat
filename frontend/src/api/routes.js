const BASE_URL = "http://localhost:7870";

export const API_ROUTES = {
  status: `${BASE_URL}/status`,
  connectSession: `${BASE_URL}/connect/session`,
  disconnect: `${BASE_URL}/disconnect`,
  webrtcOffer: `${BASE_URL}/webrtc/offer`,
  teachingStream: `${BASE_URL}/teaching/stream`,
};



