const API = "http://localhost:8000/api/v1";
export const anticollector = {
  register: (phone: string, os: string) => fetch(`${API}/anticollector/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, device_os: os }) }).then(r => r.json()),
  getBlockedNumbers: () => fetch(`${API}/anticollector/blocked-numbers`).then(r => r.json()),
  reportNumber: (phone: string) => fetch(`${API}/anticollector/report-number`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone_number: phone }) }).then(r => r.json()),
  analyzeSMS: (sender: string, text: string) => fetch(`${API}/anticollector/analyze-sms`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sender, text }) }).then(r => r.json()),
  getLegalTips: () => fetch(`${API}/anticollector/legal-tips`).then(r => r.json()),
};
