const state = { sessionStarted: false };

function addMessage(text, role = 'teacher') {
  const box = document.createElement('div');
  box.className = `message ${role}`;
  box.textContent = text;
  document.getElementById('messages').appendChild(box);
}

async function startSession(event) {
  event.preventDefault();
  const topic = document.getElementById('topic').value;
  const level = document.getElementById('level').value;
  const response = await fetch('/api/session/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, level })
  });
  const data = await response.json();
  addMessage(data.message || 'Session started.', 'teacher');
  if (data.task) addMessage(data.task, 'teacher');
  if (data.starter_code) document.getElementById('code').value = data.starter_code;
  state.sessionStarted = true;
}

async function submitCode() {
  const code = document.getElementById('code').value;
  if (!code.trim()) return;
  const response = await fetch('/api/session/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  });
  const data = await response.json();
  addMessage(code, 'student');
  addMessage(data.message || 'Feedback received.', 'teacher');
  if (data.task) addMessage(data.task, 'teacher');
  if (data.starter_code) document.getElementById('code').value = data.starter_code;
}

async function sendSignal(signal) {
  const response = await fetch('/api/session/signal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signal })
  });
  const data = await response.json();
  addMessage(`Signal: ${signal}`, 'student');
  addMessage(data.message || 'Signal received.', 'teacher');
}

document.getElementById('setup-form').addEventListener('submit', startSession);
document.getElementById('submit-btn').addEventListener('click', submitCode);
document.querySelectorAll('[data-signal]').forEach((btn) => btn.addEventListener('click', () => sendSignal(btn.dataset.signal)));
