// Mobile nav
document.getElementById('navToggle').addEventListener('click', () => {
  document.getElementById('navLinks').classList.toggle('open');
});

// ===== API CONFIG =====
const API_BASE = window.audioIntelAuth?.API_BASE || 'http://localhost:8000';

// ===== EMBEDDED BROWSER =====
let browserHistory = [];
let browserHistoryIndex = -1;

function openInBrowser(url) {
  const frame = document.getElementById('browserFrame');
  const welcome = document.getElementById('browserWelcome');
  const urlBar = document.getElementById('browserUrl');
  const viewport = document.getElementById('browserViewport');

  // Show loading
  let loader = document.createElement('div');
  loader.className = 'browser-loading';
  loader.id = 'browserLoader';
  loader.innerHTML = '<div class="browser-spinner"></div>';
  viewport.appendChild(loader);

  // Hide welcome, show frame
  if (welcome) welcome.style.display = 'none';
  frame.style.display = 'block';
  frame.src = url;
  urlBar.value = url;

  // Track history
  browserHistory = browserHistory.slice(0, browserHistoryIndex + 1);
  browserHistory.push(url);
  browserHistoryIndex = browserHistory.length - 1;

  // Remove loader when loaded
  frame.onload = () => {
    const l = document.getElementById('browserLoader');
    if (l) l.remove();
  };
  // Fallback remove after 5s
  setTimeout(() => {
    const l = document.getElementById('browserLoader');
    if (l) l.remove();
  }, 5000);
}

function navigateBrowser(url) {
  if (!url) return;
  if (!url.startsWith('http')) url = 'https://' + url;
  openInBrowser(url);
}

function browserBack() {
  if (browserHistoryIndex > 0) {
    browserHistoryIndex--;
    const url = browserHistory[browserHistoryIndex];
    document.getElementById('browserFrame').src = url;
    document.getElementById('browserUrl').value = url;
  }
}

function browserForward() {
  if (browserHistoryIndex < browserHistory.length - 1) {
    browserHistoryIndex++;
    const url = browserHistory[browserHistoryIndex];
    document.getElementById('browserFrame').src = url;
    document.getElementById('browserUrl').value = url;
  }
}

function browserReload() {
  const frame = document.getElementById('browserFrame');
  if (frame.src) frame.src = frame.src;
}

// ===== TYPE CHIPS =====
let activeType = 'all';
document.querySelectorAll('#typeChips .type-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#typeChips .type-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    activeType = chip.dataset.type;
  });
});

// ===== CONNECTIVITY CHIPS =====
let activeConnect = 'all';
document.querySelectorAll('#connectChips .type-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#connectChips .type-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    activeConnect = chip.dataset.connect;
  });
});

// ===== BUDGET SLIDER =====
function updateBudget(val) {
  const display = document.getElementById('budgetDisplay');
  const valueLabel = document.getElementById('budgetValue');
  if (+val >= 500) {
    valueLabel.textContent = '$500+';
    display.innerHTML = 'Up to <strong>$500+</strong>';
  } else {
    valueLabel.textContent = '$' + val;
    display.innerHTML = 'Up to <strong>$' + val + '</strong>';
  }
}

// ===== FILTER APPLY / RESET =====
function applyFilters() {
  const type = activeType === 'all' ? 'any type' : activeType;
  const connect = activeConnect === 'all' ? '' : activeConnect;
  const budget = document.getElementById('budgetSlider').value;
  const useCase = document.getElementById('useCaseFilter').value;
  const brand = document.getElementById('brandFilter').value;
  let msg = `I'm looking for ${connect ? connect + ' ' : ''}${type} headphones`;
  if (+budget < 500) msg += ` under $${budget}`;
  if (useCase !== 'general') msg += ` for ${useCase}`;
  if (brand !== 'all') msg += ` from ${brand}`;
  sendQuick(msg);
}

function resetFilters() {
  activeType = 'all';
  activeConnect = 'all';
  document.querySelectorAll('#typeChips .type-chip').forEach(c => c.classList.remove('active'));
  document.querySelector('#typeChips .type-chip[data-type="all"]').classList.add('active');
  document.querySelectorAll('#connectChips .type-chip').forEach(c => c.classList.remove('active'));
  document.querySelector('#connectChips .type-chip[data-connect="all"]').classList.add('active');
  document.getElementById('budgetSlider').value = 500;
  document.getElementById('budgetValue').textContent = '$500+';
  document.getElementById('budgetDisplay').innerHTML = 'Up to <strong>$500+</strong>';
  document.getElementById('useCaseFilter').value = 'general';
  document.getElementById('brandFilter').value = 'all';
}

// ===== GATHER CURRENT FILTERS =====
function getActiveFilters() {
  return {
    product_type: activeType,
    connectivity: activeConnect,
    budget: parseInt(document.getElementById('budgetSlider').value, 10),
    use_case: document.getElementById('useCaseFilter').value,
    brand: document.getElementById('brandFilter').value,
  };
}

// ===== CHAT RENDERING =====
const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;

function linkifyUrls(text) {
  return text.replace(urlRegex, (url) => {
    const short = url.length > 50 ? url.slice(0, 47) + '...' : url;
    return `<a class="product-link" onclick="event.preventDefault();openInBrowser('${url}')" href="#" title="Open in browser">${short}</a>`;
  });
}

/**
 * Render markdown-like formatting from the LLM response:
 *  - **bold** → <strong>
 *  - Bullet lists (- or •)
 *  - URLs → clickable links that open in browser pane
 */
function formatBotReply(text) {
  // Bold
  let result = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Linkify URLs
  result = linkifyUrls(result);
  // Simple bullet list formatting
  result = result.replace(/^[\-•]\s+/gm, '&bull; ');
  // Line breaks → <br>
  result = result.replace(/\n/g, '<br>');
  return result;
}

function addMessage(text, type) {
  const welcome = document.getElementById('chatWelcome');
  if (welcome) welcome.style.display = 'none';
  const container = document.getElementById('chatMessages');
  const avatar = type === 'bot' ? '🎧' : '👤';
  const div = document.createElement('div');
  div.className = `message ${type}`;
  const processedText = type === 'bot' ? formatBotReply(text) : linkifyUrls(text);
  div.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-content">${processedText}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'message bot';
  div.id = 'typingMsg';
  div.innerHTML = `<div class="msg-avatar">🎧</div><div class="msg-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById('typingMsg');
  if (t) t.remove();
}

// ===== CALL THE BACKEND RAG CHATBOT =====
async function getAIResponse(message) {
  const filters = getActiveFilters();

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, filters }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to get response from AI');
  }

  const data = await res.json();
  return data; // { reply, sources }
}

// ===== SEND MESSAGE =====
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  addMessage(text, 'user');
  input.value = '';

  // If user pasted a URL, auto-open it in the browser pane
  const urlMatch = text.match(urlRegex);
  if (urlMatch) {
    openInBrowser(urlMatch[0]);
  }

  showTyping();

  try {
    const data = await getAIResponse(text);
    removeTyping();
    addMessage(data.reply, 'bot');

    // If the response contains product URLs, auto-open the first one in the browser
    if (data.sources && data.sources.length > 0 && data.sources[0].url) {
      openInBrowser(data.sources[0].url);
    }
  } catch (err) {
    removeTyping();
    addMessage(`Sorry, something went wrong: ${err.message}. Please try again.`, 'bot');
  }
}

function sendQuick(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}
