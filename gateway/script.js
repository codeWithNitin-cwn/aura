// ═══════════════════════════════════════════
// AURA — script.js
// All interaction logic: voice, text, chat UI,
// orb states, modal, utilities
// ═══════════════════════════════════════════

// ── STATE ───────────────────────────────────
let mode          = 'text';
let isRecording   = false;
let isProcessing  = false;
let mediaRecorder = null;
let audioChunks   = [];
let msgCount      = 0;

// ── INIT ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('textInput').focus();
  animatePips();

  // Close features dropdown when clicking outside
  document.addEventListener('click', (e) => {
    const btn      = document.getElementById('featBtn');
    const dropdown = document.getElementById('featDropdown');
    if (btn && dropdown && !btn.contains(e.target) && !dropdown.contains(e.target)) {
      btn.classList.remove('open');
      dropdown.classList.remove('open');
      document.getElementById('featArrow').style.transform = '';
    }
  });
});

// ── ORB CLICK (tactile feedback) ───────────
function orbClick() {
  const orb = document.getElementById('orbSphere');
  orb.style.transform = 'scale(0.95)';
  setTimeout(() => { orb.style.transform = ''; }, 150);
}

// ── STATE PIPS CYCLE ────────────────────────
function animatePips() {
  let i = 0;
  setInterval(() => {
    document.querySelectorAll('.state-pip').forEach((pip, idx) => {
      pip.classList.toggle('active', idx === i);
    });
    i = (i + 1) % 5;
  }, 1800);
}

// ── MODE SWITCH (text ↔ voice) ─────────────
function switchMode(m) {
  mode = m;

  const textMode  = document.getElementById('textMode');
  const voiceMode = document.getElementById('voiceMode');

  document.getElementById('tabText').classList.toggle('active',  m === 'text');
  document.getElementById('tabVoice').classList.toggle('active', m === 'voice');

  if (m === 'text') {
    textMode.style.display  = 'flex';
    voiceMode.style.display = 'none';
    document.getElementById('textInput').focus();
  } else {
    textMode.style.display  = 'none';
    voiceMode.style.display = 'block';
  }
}

// ── TEXTAREA AUTO-RESIZE ────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

// ── ENTER TO SEND ───────────────────────────
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendText();
  }
}

// ── QUICK CHIP SHORTCUTS ────────────────────
function sendChip(text) {
  document.getElementById('textInput').value = text;
  sendText();
}

// ── SEND TEXT MESSAGE ────────────────────────
async function sendText() {
  const input = document.getElementById('textInput');
  const text  = input.value.trim();
  if (!text || isProcessing) return;

  // Clear field
  input.value        = '';
  input.style.height = 'auto';
  document.getElementById('sendBtn').disabled = true;

  addMessage('user', text, 'text');
  setOrbState('processing');
  const typingId = showTyping();
  isProcessing = true;

  try {
    const res  = await fetch('/process_text', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ text })
    });
    const data = await res.json();
    removeTyping(typingId);
    addMessage('aura', data.response || data.error || 'No response.', 'text');
    if (data.audio_url) playAudio(data.audio_url);
  } catch (err) {
    removeTyping(typingId);
    addMessage(
      'aura',
      `Connection error: ${err.message}\n\nMake sure the gateway is running on port 5000.`,
      'text'
    );
  }

  setOrbState('idle');
  isProcessing = false;
  document.getElementById('sendBtn').disabled = false;
  document.getElementById('textInput').focus();
}

// ── VOICE RECORDING ─────────────────────────
async function toggleRecording() {
  if (isProcessing) return;
  isRecording ? stopRecording() : await startRecording();
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks  = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.onstop = handleVoiceData;
    mediaRecorder.start(100);
    isRecording = true;

    // UI feedback
    document.getElementById('micBtn').classList.add('recording');
    document.getElementById('waveformFull').classList.add('active');
    document.getElementById('voiceStatus').textContent = 'Recording… click to stop';
    document.getElementById('voiceStatus').classList.add('active');
    document.getElementById('miniWave').classList.add('active');
    setOrbState('listening');

  } catch {
    addMessage('aura', '⚠ Microphone access denied. Please allow mic permissions in your browser.', 'voice');
  }
}

function stopRecording() {
  if (!mediaRecorder || !isRecording) return;

  mediaRecorder.stop();
  mediaRecorder.stream.getTracks().forEach(t => t.stop());
  isRecording = false;

  // Reset UI
  document.getElementById('micBtn').classList.remove('recording');
  document.getElementById('waveformFull').classList.remove('active');
  document.getElementById('voiceStatus').textContent = 'Processing…';
  document.getElementById('voiceStatus').classList.remove('active');
  document.getElementById('miniWave').classList.remove('active');
  setOrbState('processing');
}

async function handleVoiceData() {
  if (!audioChunks.length) {
    setOrbState('idle');
    document.getElementById('voiceStatus').textContent = 'Click to begin recording';
    return;
  }

  isProcessing = true;

  const blob     = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('audio', blob, 'voice.webm');

  const typingId = showTyping();

  try {
    const res  = await fetch('/process', { method: 'POST', body: formData });
    const data = await res.json();
    removeTyping(typingId);

    if (data.user_said) addMessage('user', data.user_said, 'voice');
    addMessage('aura', data.response || data.error || 'No response.', 'voice');
    if (data.audio_url) playAudio(data.audio_url);

  } catch (err) {
    removeTyping(typingId);
    addMessage('aura', `Connection error: ${err.message}`, 'voice');
  }

  isProcessing = false;
  setOrbState('idle');
  document.getElementById('voiceStatus').textContent = 'Click to begin recording';
}

// ── ORB STATE MANAGER ───────────────────────
// states: 'idle' | 'listening' | 'processing'
function setOrbState(state) {
  const sphere = document.getElementById('orbSphere');
  sphere.classList.remove('processing', 'listening');
  if (state !== 'idle') sphere.classList.add(state);
}

// ── ADD CHAT MESSAGE ─────────────────────────
function addMessage(role, text, inputMode) {
  // Remove empty state on first message
  const empty = document.getElementById('emptyState');
  if (empty) empty.remove();

  const chat = document.getElementById('chat');
  const div  = document.createElement('div');
  div.className = `msg ${role}`;

  const now        = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const avatar     = role === 'user' ? '◎'       : '⬡';
  const label      = role === 'user' ? 'You'      : 'AURA';
  const badgeClass = inputMode === 'voice' ? 'badge-voice' : 'badge-text';
  const badgeLabel = inputMode === 'voice' ? '🎙 voice'    : '⌨ text';

  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      <div class="msg-meta">
        <span class="msg-name">${label}</span>
        <span class="msg-mode-badge ${badgeClass}">${badgeLabel}</span>
        <span class="msg-time">${now}</span>
      </div>
      <div class="msg-bubble">${escapeHtml(text)}</div>
    </div>
  `;

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;

  // Increment message counter in sidebar
  msgCount++;
  const counter = document.getElementById('statMsgs');
  if (counter) counter.textContent = msgCount;
}

// ── TYPING INDICATOR ─────────────────────────
function showTyping() {
  // Remove empty state if still visible
  const empty = document.getElementById('emptyState');
  if (empty) empty.remove();

  const chat = document.getElementById('chat');
  const id   = 'typing-' + Date.now();
  const div  = document.createElement('div');

  div.id        = id;
  div.className = 'msg aura';
  div.innerHTML = `
    <div class="msg-avatar">⬡</div>
    <div class="msg-body">
      <div class="msg-meta"><span class="msg-name">AURA</span></div>
      <div class="typing-bubble">
        <div class="tdot"></div>
        <div class="tdot"></div>
        <div class="tdot"></div>
      </div>
    </div>
  `;

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── PLAY TTS AUDIO ───────────────────────────
function playAudio(url) {
  // Cache-bust so the browser doesn't serve stale audio
  const src   = url.includes('?') ? url : `${url}?t=${Date.now()}`;
  const audio = new Audio(src);
  audio.play().catch(() => {
    // Autoplay blocked — response is still shown as text
  });
}

// ── CONTACT MODAL ────────────────────────────
function openContact() {
  document.getElementById('contactModal').classList.add('open');
}

function closeContact(e) {
  // Close when clicking the backdrop or the ✕ button
  if (!e || e.target === document.getElementById('contactModal')) {
    document.getElementById('contactModal').classList.remove('open');
  }
}

// Escape key closes modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.getElementById('contactModal').classList.remove('open');
  }
});

// ── FEATURES DROPDOWN ───────────────────────
function toggleFeatures(e) {
  e.preventDefault();
  e.stopPropagation();
  const btn      = document.getElementById('featBtn');
  const dropdown = document.getElementById('featDropdown');
  const isOpen   = dropdown.classList.contains('open');

  btn.classList.toggle('open', !isOpen);
  dropdown.classList.toggle('open', !isOpen);
}

// ── TRY FEATURE (demo in chat) ───────────────
function tryFeature(featureName, userMsg, auraReply) {
  // Close the dropdown
  document.getElementById('featBtn').classList.remove('open');
  document.getElementById('featDropdown').classList.remove('open');

  // Put the demo command into the input and fire it as a chat message
  // Show user message
  addMessage('user', userMsg, 'text');
  setOrbState('processing');
  const typingId = showTyping();

  // Simulate response after short delay
  setTimeout(() => {
    removeTyping(typingId);
    // Strip HTML entities for display
    const decoded = auraReply
      .replace(/&quot;/g, '"')
      .replace(/&amp;/g, '&')
      .replace(/&#39;/g, "'");
    addMessage('aura', `[${featureName}] ${decoded}`, 'text');
    setOrbState('idle');
  }, 600);
}

// ── UTILITIES ────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/\n/g, '<br>');
}