// Mobile nav
document.getElementById('navToggle').addEventListener('click', () => {
  document.getElementById('navLinks').classList.toggle('open');
});

// ===== PRODUCT URL MAP =====
// Maps product names to real product/search URLs
const productUrls = {
  "Sony WH-1000XM5": "https://www.amazon.com/s?k=Sony+WH-1000XM5",
  "Bose QC Ultra": "https://www.amazon.com/s?k=Bose+QuietComfort+Ultra",
  "Sennheiser Momentum 4": "https://www.amazon.com/s?k=Sennheiser+Momentum+4+Wireless",
  "JBL Tune 770NC": "https://www.amazon.com/s?k=JBL+Tune+770NC",
  "Beyerdynamic DT 900 Pro X": "https://www.amazon.com/s?k=Beyerdynamic+DT+900+Pro+X",
  "Audio-Technica ATH-M50x": "https://www.amazon.com/s?k=Audio-Technica+ATH-M50x",
  "Sony MDR-7506": "https://www.amazon.com/s?k=Sony+MDR-7506",
  "HiFiMAN Sundara": "https://www.amazon.com/s?k=HiFiMAN+Sundara",
  "AirPods Pro 2": "https://www.amazon.com/s?k=AirPods+Pro+2",
  "Sony WF-1000XM5": "https://www.amazon.com/s?k=Sony+WF-1000XM5",
  "Samsung Galaxy Buds3 Pro": "https://www.amazon.com/s?k=Samsung+Galaxy+Buds3+Pro",
  "Nothing Ear 2": "https://www.amazon.com/s?k=Nothing+Ear+2",
  "Jabra Elite 85t": "https://www.amazon.com/s?k=Jabra+Elite+85t",
  "JBL Tour Pro 2": "https://www.amazon.com/s?k=JBL+Tour+Pro+2",
  "Google Pixel Buds Pro 2": "https://www.amazon.com/s?k=Google+Pixel+Buds+Pro+2",
  "Beats Fit Pro": "https://www.amazon.com/s?k=Beats+Fit+Pro",
  "Sony WI-1000XM2": "https://www.amazon.com/s?k=Sony+WI-1000XM2",
  "JBL Tune Beam": "https://www.amazon.com/s?k=JBL+Tune+Beam",
  "OnePlus Bullets Z2": "https://www.amazon.com/s?k=OnePlus+Bullets+Z2",
  "Moondrop Aria": "https://www.amazon.com/s?k=Moondrop+Aria",
  "Shure SE846": "https://www.amazon.com/s?k=Shure+SE846",
  "Truthear HEXA": "https://www.amazon.com/s?k=Truthear+HEXA",
  "KZ ZS10 Pro": "https://www.amazon.com/s?k=KZ+ZS10+Pro",
  "SteelSeries Arctis Nova Pro": "https://www.amazon.com/s?k=SteelSeries+Arctis+Nova+Pro",
  "HyperX Cloud III": "https://www.amazon.com/s?k=HyperX+Cloud+III",
};

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

// ===== CHAT BOT =====
// Detect URLs in any text and wrap them as clickable links
const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;

function linkifyUrls(text) {
  return text.replace(urlRegex, (url) => {
    const short = url.length > 50 ? url.slice(0, 47) + '...' : url;
    return `<a class="product-link" onclick="event.preventDefault();openInBrowser('${url}')" href="#" title="Open in browser">${short}</a>`;
  });
}

// Helper: wraps **Product Name** with a clickable link that opens in the browser pane
function makeProductLinks(text) {
  // First, handle **bold product names**
  let result = text.replace(/\*\*(.*?)\*\*/g, (match, name) => {
    const url = productUrls[name];
    if (url) {
      return `<a class="product-link" onclick="event.preventDefault();openInBrowser('${url}')" href="#" title="View ${name} in browser">${name}</a>`;
    }
    return `<strong>${name}</strong>`;
  });
  // Then, linkify any raw URLs in the text
  result = linkifyUrls(result);
  return result;
}

const botResponses = {
  bass: "For bass lovers, I'd recommend the **Sony WH-1000XM5** (over-ear, $298) or **JBL Tune 770NC** (budget $79). Both deliver deep, punchy bass. Click any product to browse it →",
  noise: "Top ANC picks: **Bose QC Ultra** (best silence, $349), **Sony WH-1000XM5** (best all-rounder, $298), and **AirPods Pro 2** (compact ANC, $199). Click to view details →",
  gaming: "For gaming: **SteelSeries Arctis Nova Pro** (best spatial audio, $349) or **HyperX Cloud III** (budget-friendly, $99). Both offer low latency and clear mics. Click to browse →",
  wireless: "Best wireless: **Sony WH-1000XM5** ($298, 30h), **Sennheiser Momentum 4** ($279, 60h!), or **JBL Tune 770NC** ($79, 44h). Click a product to see it →",
  budget: "Great budget picks: **JBL Tune 770NC** ($79 headphone), **Nothing Ear 2** ($99 TWS), **OnePlus Bullets Z2** ($29 neckband), or **Moondrop Aria** ($79 IEM). Click to browse →",
  workout: "For workouts: **Beats Fit Pro** (secure wingtips, $159), **Samsung Galaxy Buds3 Pro** (IPX7, $179). Both are sweat and splash proof! Click to view →",
  studio: "Studio picks: **Beyerdynamic DT 900 Pro X** (open-back mixing, $249), **Audio-Technica ATH-M50x** (closed monitoring, $149), **Sony MDR-7506** (studio legend, $89). Click any →",
  tws: "Top TWS: **AirPods Pro 2** (best for iPhone, $199), **Sony WF-1000XM5** (best ANC, $228), **Samsung Galaxy Buds3 Pro** (Android, $179). Click to view →",
  neckband: "Best neckbands: **Sony WI-1000XM2** ($248, ANC), **JBL Tune Beam** ($49, 32h battery), **OnePlus Bullets Z2** ($29, fast charge). Click to browse →",
  earphone: "Wired IEM picks: **Moondrop Aria** ($79, Harman-tuned), **Truthear HEXA** ($79, hybrid), **Shure SE846** ($699, audiophile). Click a link to view →",
  headphone: "Best headphones: **Sony WH-1000XM5** (overall, $298), **Bose QC Ultra** (ANC, $349), **Sennheiser Momentum 4** (60h, $279), **HiFiMAN Sundara** (planar, $299). Click to browse →",
  travel: "For travel: **Bose QC Ultra** (best ANC, $349), **Sony WH-1000XM5** (30h + multipoint, $298), or **AirPods Pro 2** (compact, $199). Click any product →",
  default: "I'd love to help! Ask about headphones, TWS, neckbands, or earphones. I'll recommend products with clickable links — click any to view in the browser panel on the right! What matters most — sound, comfort, ANC, or price?"
};

function getResponse(msg) {
  const lower = msg.toLowerCase();
  for (const [key, val] of Object.entries(botResponses)) {
    if (key !== 'default' && lower.includes(key)) return val;
  }
  if (/\$\d+|under|budget|cheap|affordable/i.test(lower)) return botResponses.budget;
  if (/cancel|quiet|silent|anc/i.test(lower)) return botResponses.noise;
  if (/run|gym|sport|exercise|sweat/i.test(lower)) return botResponses.workout;
  if (/plane|flight|commut/i.test(lower)) return botResponses.travel;
  if (/mix|master|monitor|record|produc/i.test(lower)) return botResponses.studio;
  if (/game|fps|spatial/i.test(lower)) return botResponses.gaming;
  // Check for specific product by name
  for (const name of Object.keys(productUrls)) {
    if (lower.includes(name.toLowerCase())) {
      return `Here's the **${name}** — a great choice! Click the link to browse it in the panel. I can compare it with others if you'd like.`;
    }
  }
  return botResponses.default;
}

function addMessage(text, type) {
  const welcome = document.getElementById('chatWelcome');
  if (welcome) welcome.style.display = 'none';
  const container = document.getElementById('chatMessages');
  const avatar = type === 'bot' ? '🎧' : '👤';
  const div = document.createElement('div');
  div.className = `message ${type}`;
  // For bot: process product names + URLs; For user: also linkify URLs
  const processedText = type === 'bot' ? makeProductLinks(text) : linkifyUrls(text);
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

function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  addMessage(text, 'user');
  input.value = '';

  // If user pasted a URL, auto-open it in the browser pane
  const urlMatch = text.match(urlRegex);
  if (urlMatch) {
    openInBrowser(urlMatch[0]);
    showTyping();
    setTimeout(() => {
      removeTyping();
      addMessage(`I've opened that link in the browser panel for you! 🌐 If it's a product page, I can help compare it with alternatives — just ask.`, 'bot');
    }, 600);
    return;
  }

  showTyping();
  setTimeout(() => {
    removeTyping();
    addMessage(getResponse(text), 'bot');
  }, 800 + Math.random() * 800);
}

function sendQuick(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}
