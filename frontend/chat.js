// Mobile nav
document.getElementById('navToggle').addEventListener('click', () => {
  document.getElementById('navLinks').classList.toggle('open');
});

// ===== API CONFIG =====
const API_BASE = window.audioIntelAuth?.API_BASE || 'http://localhost:8000';

// ===== PRODUCT PANEL (replaces embedded browser) =====
// Most websites block iframe embedding (X-Frame-Options / CSP).
// Instead, we show product cards in the right panel and open links in new tabs.

let displayedSources = [];

function openInBrowser(url) {
  // Open product URLs in a new tab (iframes are blocked by most sites)
  if (url) window.open(url, '_blank', 'noopener,noreferrer');
}

function showProductPanel(sources) {
  const welcome = document.getElementById('browserWelcome');
  const cardsContainer = document.getElementById('productCards');
  const urlBar = document.getElementById('browserUrl');

  if (!sources || sources.length === 0) return;

  displayedSources = sources;

  // Hide welcome
  if (welcome) welcome.style.display = 'none';

  // Show cards
  if (cardsContainer) {
    cardsContainer.style.display = 'flex';
    cardsContainer.innerHTML = '';

    sources.forEach((src, i) => {
      const price = src.price ? `৳${src.price}` : 'N/A';
      const type = src.type || 'Audio';
      const conn = src.connectivity || '';
      const name = src.product_name || 'Unknown Product';
      const url = src.url || '#';

      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <div class="pc-header">
          <span class="pc-badge">${type}</span>
          ${conn ? `<span class="pc-badge pc-badge-conn">${conn}</span>` : ''}
        </div>
        <h4 class="pc-name">${name}</h4>
        <div class="pc-price">${price}</div>
        <a class="pc-link" href="${url}" target="_blank" rel="noopener noreferrer">
          Visit Store →
        </a>
      `;
      cardsContainer.appendChild(card);
    });
  }

  // Update URL bar with first product
  if (urlBar && sources[0]?.url) {
    urlBar.value = sources[0].url;
  }
}

function navigateBrowser(url) {
  if (!url) return;
  if (!url.startsWith('http')) url = 'https://' + url;
  openInBrowser(url);
}

function browserBack() { }
function browserForward() { }
function browserReload() {
  if (displayedSources.length > 0) showProductPanel(displayedSources);
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
  let msg = `I'm looking for ${connect ? connect + ' ' : ''}${type} headphones`;
  if (+budget < 500) msg += ` under $${budget}`;
  if (useCase !== 'general') msg += ` for ${useCase}`;
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
}

// ===== GATHER CURRENT FILTERS =====
function getActiveFilters() {
  return {
    product_type: activeType,
    connectivity: activeConnect,
    budget: parseInt(document.getElementById('budgetSlider').value, 10),
    use_case: document.getElementById('useCaseFilter').value,
  };
}

// ===== CHAT RENDERING =====
const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;

function cleanUrl(raw) {
  // Strip trailing punctuation that isn't part of the actual URL
  // Handles URLs wrapped in parens: (https://example.com) or markdown [text](url)
  let url = raw;
  // Remove trailing characters that are almost never part of a URL
  url = url.replace(/[)\].,;:!?]+$/, '');
  return url;
}

function linkifyUrls(text) {
  return text.replace(urlRegex, (matched) => {
    const url = cleanUrl(matched);
    const trailing = matched.slice(url.length); // chars we stripped (e.g. ")")
    const short = url.length > 50 ? url.slice(0, 47) + '...' : url;
    return `<a class="product-link" onclick="event.preventDefault();openInBrowser('${url}')" href="#" title="Open in browser">${short}</a>${trailing}`;
  });
}

/**
 * Render markdown formatting from LLM responses:
 *  - Tables (| col1 | col2 | ...)
 *  - **bold**
 *  - ### headings
 *  - Numbered lists (1. item)
 *  - Bullet lists (- or • item)
 *  - URLs → clickable links
 *  - Horizontal rules (---)
 */
function formatBotReply(text) {
  const lines = text.split('\n');
  const htmlParts = [];
  let i = 0;

  while (i < lines.length) {
    // ── Table detection ──
    // A table starts when we see a line that contains at least one |
    // followed by a separator line like |---|---|
    if (isTableRow(lines[i]) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const tableLines = [];
      while (i < lines.length && isTableRow(lines[i])) {
        tableLines.push(lines[i]);
        i++;
      }
      htmlParts.push(renderTable(tableLines));
      continue;
    }

    // ── Heading (### or ##) ──
    const headingMatch = lines[i].match(/^(#{2,3})\s+(.+)/);
    if (headingMatch) {
      const level = headingMatch[1].length; // 2 or 3
      const content = inlineFormat(headingMatch[2]);
      htmlParts.push(`<h${level} class="chat-heading">${content}</h${level}>`);
      i++;
      continue;
    }

    // ── Horizontal rule ──
    if (/^-{3,}$/.test(lines[i].trim()) || /^\*{3,}$/.test(lines[i].trim())) {
      htmlParts.push('<hr class="chat-hr">');
      i++;
      continue;
    }

    // ── Numbered list ──
    if (/^\d+\.\s+/.test(lines[i])) {
      let listHtml = '<ol class="chat-ol">';
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        const content = inlineFormat(lines[i].replace(/^\d+\.\s+/, ''));
        listHtml += `<li>${content}</li>`;
        i++;
      }
      listHtml += '</ol>';
      htmlParts.push(listHtml);
      continue;
    }

    // ── Bullet list ──
    if (/^[\-•\*]\s+/.test(lines[i])) {
      let listHtml = '<ul class="chat-ul">';
      while (i < lines.length && /^[\-•\*]\s+/.test(lines[i])) {
        const content = inlineFormat(lines[i].replace(/^[\-•\*]\s+/, ''));
        listHtml += `<li>${content}</li>`;
        i++;
      }
      listHtml += '</ul>';
      htmlParts.push(listHtml);
      continue;
    }

    // ── Empty line (paragraph break) ──
    if (lines[i].trim() === '') {
      htmlParts.push('<br>');
      i++;
      continue;
    }

    // ── Normal text line ──
    htmlParts.push(inlineFormat(lines[i]));
    // Add <br> if next line is also a plain text line (not a block element)
    if (i + 1 < lines.length && lines[i + 1].trim() !== '' &&
      !isTableRow(lines[i + 1]) && !/^#{2,3}\s/.test(lines[i + 1]) &&
      !/^\d+\.\s/.test(lines[i + 1]) && !/^[\-•\*]\s/.test(lines[i + 1])) {
      htmlParts.push('<br>');
    }
    i++;
  }

  return htmlParts.join('\n');
}

/** Apply inline formatting: bold, URLs */
function inlineFormat(text) {
  let result = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  result = linkifyUrls(result);
  return result;
}

/** Check if a line looks like a markdown table row */
function isTableRow(line) {
  if (!line) return false;
  const trimmed = line.trim();
  return trimmed.includes('|') && (trimmed.startsWith('|') || trimmed.endsWith('|'));
}

/** Check if a line is a table separator (|---|---|) */
function isTableSeparator(line) {
  if (!line) return false;
  return /^\|?[\s\-:]+(\|[\s\-:]+)+\|?$/.test(line.trim());
}

/** Convert an array of markdown table lines into an HTML <table> */
function renderTable(tableLines) {
  // Filter out separator rows
  const dataRows = tableLines.filter(line => !isTableSeparator(line));
  if (dataRows.length === 0) return '';

  const parseRow = (line) => {
    return line.trim().replace(/^\|/, '').replace(/\|$/, '')
      .split('|').map(cell => inlineFormat(cell.trim()));
  };

  let html = '<div class="chat-table-wrap"><table class="chat-table">';

  // First data row = header
  const headerCells = parseRow(dataRows[0]);
  html += '<thead><tr>';
  headerCells.forEach(cell => { html += `<th>${cell}</th>`; });
  html += '</tr></thead>';

  // Remaining rows = body
  if (dataRows.length > 1) {
    html += '<tbody>';
    for (let r = 1; r < dataRows.length; r++) {
      const cells = parseRow(dataRows[r]);
      html += '<tr>';
      cells.forEach(cell => { html += `<td>${cell}</td>`; });
      html += '</tr>';
    }
    html += '</tbody>';
  }

  html += '</table></div>';
  return html;
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

    // Show product cards in the right panel from RAG sources
    if (data.sources && data.sources.length > 0) {
      showProductPanel(data.sources);
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
