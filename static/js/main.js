// ==================================================
// 🌟 MAIN.JS — QUICKNEWSAI CORE LOGIC
// ==================================================

// ================================
// 🔊 CLICK SOUND SETUP
// ================================
const clickSound = new Audio("/static/sound/click.mp3");

function playClickSound() {
    clickSound.currentTime = 0;
    clickSound.play().catch(() => {});
}

// ================================
// SUMMARY LENGTH SLIDER
// ================================
const range = document.getElementById("summaryRange");
const label = document.getElementById("lengthLabel");
const hidden = document.getElementById("summaryLengthValue");

if (range && label && hidden) {
    range.addEventListener("input", () => {
        const map = { "1": "Short", "2": "Medium", "3": "Long" };
        label.innerText = map[range.value];
        hidden.value = map[range.value].toLowerCase();
        label.style.transform = "scale(1.15)";
        setTimeout(() => (label.style.transform = "scale(1)"), 150);
    });
}

// ================================
// TOGGLE FULL NEWS (SMOOTH)
// ================================
function toggleNews() {
    const box = document.getElementById("fullNewsBox");
    if (!box) return;

    if (!box.dataset.initialized) {
        box.style.overflow = "hidden";
        box.style.transition = "max-height 0.35s ease, opacity 0.25s ease";
        box.style.maxHeight = box.scrollHeight + "px";
        box.dataset.initialized = "true";
        return;
    }

    if (box.style.maxHeight === "0px" || box.style.maxHeight === "") {
        box.style.display = "block";
        box.style.opacity = "1";
        box.style.maxHeight = box.scrollHeight + "px";
    } else {
        box.style.opacity = "0";
        box.style.maxHeight = "0px";
        setTimeout(() => { box.style.display = "none"; }, 350);
    }
}

// ================================
// SHOW/HIDE LOADING OVERLAY
// ================================
function showLoading() {
    const loader = document.getElementById("globalLoader");
    if (loader) {
        loader.style.display = "flex";
        loader.style.opacity = "0";
        setTimeout(() => (loader.style.opacity = "1"), 50);
    }
}

function hideLoading() {
    const loader = document.getElementById("globalLoader");
    if (loader) {
        loader.style.opacity = "0";
        setTimeout(() => (loader.style.display = "none"), 300);
    }
}

// ================================
// 🔔 TOAST NOTIFICATION SYSTEM
// ================================
function showToast(message, category = "success", duration = 4000) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const iconMap = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };
    const classMap = { success: "toast-success", error: "toast-error", info: "toast-info", warning: "toast-error" };

    const toast = document.createElement("div");
    toast.className = `custom-toast ${classMap[category] || "toast-info"}`;
    toast.innerHTML = `
        <span>${iconMap[category] || "ℹ️"}</span>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = "toastSlideOut 0.4s ease forwards";
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

// Auto-attach loading overlay to forms
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", () => showLoading());
    });
});

// ================================
// IMAGE FALLBACK
// ================================
function handleImgError(img) {
    img.src = "/static/img/news_placeholder.jpg";
}

// ================================
// 🌙 DARK MODE TOGGLE
// ================================
function toggleDarkMode() {
    const isDark = document.body.classList.toggle("dark-mode");
    document.documentElement.classList.toggle("dark-mode", isDark);
    const icon = document.getElementById("darkIcon");

    if (isDark) {
        if (icon) icon.innerText = "☀️";
        localStorage.setItem("theme", "dark");
    } else {
        if (icon) icon.innerText = "🌙";
        localStorage.setItem("theme", "light");
    }
}

// ================================
// OPEN SUMMARY MODAL
// ================================
let baseSummaryText = "";
let baseFullNewsText = "";

function openSummary(url, title) {
    playClickSound();
    const modalEl = document.getElementById("summaryModal");
    if (!modalEl) return;

    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    const sEl = document.getElementById("modalSummary");
    const fEl = document.getElementById("modalFullNews");
    document.getElementById("modalTitle").innerText = title;
    
    sEl.innerText = "Generating summary...";
    fEl.innerText = "Loading full news...";

    const langSelect = document.getElementById("modalLang");
    if (langSelect) langSelect.value = "";

    fetch(`/api/summary?url=${encodeURIComponent(url)}&lang=en`)
        .then(res => res.json())
        .then(data => {
            baseSummaryText = data.summary || "Summary not available.";
            baseFullNewsText = data.full_news || "Full news not available.";
            sEl.innerText = baseSummaryText;
            fEl.innerText = baseFullNewsText;
        })
        .catch(() => {
            sEl.innerText = "❌ Error loading summary.";
        });
}

function changeSummaryLanguage() {
    const lang = document.getElementById("modalLang").value;
    if (!lang) return;

    const sEl = document.getElementById("modalSummary");
    const fEl = document.getElementById("modalFullNews");
    sEl.innerText = "🌐 Translating...";
    fEl.innerText = "🌐 Translating...";

    Promise.all([
        fetch(`/api/translate?lang=${lang}&text=${encodeURIComponent(baseSummaryText)}`),
        fetch(`/api/translate?lang=${lang}&text=${encodeURIComponent(baseFullNewsText)}`)
    ])
    .then(r => Promise.all(r.map(res => res.json())))
    .then(([s, f]) => {
        sEl.innerText = s.translated;
        fEl.innerText = f.translated;
    });
}

// ================================
// LOAD MORE & CATEGORIES
// ================================
// Pagination & Categories (using window for template-sync)
window.nextPageToken = window.nextPageToken || null;
let currentCategory = "general";

const loadMoreBtn = document.getElementById("loadMoreBtn");
const newsContainer = document.getElementById("newsContainer");

function renderNewsCard(news) {
    if (!newsContainer) return;

    const col = document.createElement("div");
    col.className = "col-md-4 col-lg-3 py-3";
    col.innerHTML = `
        <div class="news-card h-100" 
             style="cursor:pointer;"
             data-url="${news.url}" 
             data-title="${news.title.replace(/"/g, '&quot;')}">
            <div class="news-img">
                <img src="${news.urlToImage || '/static/img/news_placeholder.jpg'}" 
                     onerror="handleImgError(this)" 
                     loading="lazy">
            </div>
            <div class="news-body p-3">
                <h6 class="news-title fw-bold mb-1">${news.title}</h6>
                <div class="news-meta small text-muted">
                    <span>📡 ${news.source?.name || ""}</span>
                </div>
            </div>
        </div>
    `;
    newsContainer.appendChild(col);
}

// Click anywhere on card -> open modal
document.addEventListener("click", (e) => {
    const card = e.target.closest(".news-card");
    if (card) openSummary(card.dataset.url, card.dataset.title);
});

// Load more button
if (loadMoreBtn && newsContainer) {
    loadMoreBtn.addEventListener("click", () => {
        if (!nextPageToken) {
            loadMoreBtn.innerText = "No more news";
            loadMoreBtn.disabled = true;
            return;
        }
        playClickSound();
        loadMoreBtn.innerText = "Loading...";
        loadMoreBtn.disabled = true;

        fetch(`/news?page=${nextPageToken}&category=${currentCategory}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            const newsList = data.results || [];
            nextPageToken = data.nextPage;

            if (newsList.length === 0) {
                loadMoreBtn.innerText = "No more news";
                return;
            }
            newsList.forEach(renderNewsCard);
            
            if (!nextPageToken) {
                loadMoreBtn.innerText = "No more news";
                loadMoreBtn.disabled = true;
            } else {
                loadMoreBtn.innerText = "Load More News";
                loadMoreBtn.disabled = false;
            }
        })
        .catch(() => {
            loadMoreBtn.innerText = "Error, try again";
            loadMoreBtn.disabled = false;
        });
    });
}

// Change category
function changeCategory(category) {
    playClickSound();
    currentCategory = category;
    nextPageToken = null;

    document.querySelectorAll(".category-btn").forEach(btn => {
        const isMatch = btn.dataset.category === category;
        btn.classList.toggle("btn-primary", isMatch);
        btn.classList.toggle("btn-outline-primary", !isMatch);
    });

    if (newsContainer) newsContainer.innerHTML = "<div class='col-12 text-center py-5'><div class='spinner-border text-primary'></div></div>";

    fetch(`/news?category=${category}&page=1`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
    })
    .then(res => res.json())
    .then(data => {
        if (newsContainer) {
            newsContainer.innerHTML = "";
            const newsList = data.results || [];
            nextPageToken = data.nextPage;
            newsList.forEach(renderNewsCard);
        }
    })
    .catch(() => {
        if (newsContainer) newsContainer.innerHTML = "<div class='alert alert-danger'>Error loading news.</div>";
    })
    .finally(() => {
        if (loadMoreBtn) {
            if (!nextPageToken) {
                loadMoreBtn.innerText = "No more news";
                loadMoreBtn.disabled = true;
            } else {
                loadMoreBtn.innerText = "Load More News";
                loadMoreBtn.disabled = false;
            }
        }
    });
}

// ================================
// 📋 UTILS
// ================================
function copyToClipboard(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        showToast("📋 Copied!", "success", 2000);
    });
}

// ================================
// 🗣️ TEXT TO SPEECH (TTS)
// ================================
let currentAudio = null; 

function speakSummary() {
    const sEl = document.getElementById("modalSummary") || 
                document.getElementById("dashboardSummary") || 
                document.getElementById("vhSummary");
    
    if (!sEl) return showToast("❌ Summary not found to speak.", "error");

    const text = sEl.innerText;
    if (!text || text === "Generating summary..." || text === "🌐 Translating..." || text === "Loading...") {
        return showToast("⌛ Please wait for the summary to load.", "info");
    }

    // Stop and cancel any currently playing speech/audio
    stopSpeech();

    // Detect language from any of the select boxes
    const langSelect = document.getElementById("modalLang") || document.getElementById("dashboardLang") || document.getElementById("resLang");
    let langCode = langSelect && langSelect.value ? langSelect.value : "en";
    const langName = langSelect ? langSelect.options[langSelect.selectedIndex]?.text : "English";

    // Standard BCP-47 tags for native TTS detection
    const langMap = {
        'en': 'en-US', 'hi': 'hi-IN', 'gu': 'gu-IN', 'mr': 'mr-IN',
        'bn': 'bn-IN', 'ta': 'ta-IN', 'te': 'te-IN', 'kn': 'kn-IN', 'ur': 'ur-PK'
    };
    const targetLang = langMap[langCode] || 'en-US';

    // 🔍 SEARCH FOR NATIVE VOICE
    let voices = window.speechSynthesis.getVoices();
    let voice = voices.find(v => v.lang.toLowerCase() === targetLang.toLowerCase() && v.name.includes("Google"));
    if (!voice) voice = voices.find(v => v.lang.toLowerCase() === targetLang.toLowerCase() || v.lang.replace('_', '-').toLowerCase() === targetLang.toLowerCase());
    if (!voice) voice = voices.find(v => v.lang.toLowerCase().startsWith(langCode));
    if (!voice) voice = voices.find(v => v.name.toLowerCase().includes(langName.toLowerCase()));

    if (voice && (langCode === 'en' || langCode === 'hi')) {
        // Use Native for English and Hindi as they are usually stable
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.voice = voice;
        utterance.lang = targetLang;
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
        showToast(`🔊 Speaking in ${langName} (Native)...`, "success", 2000);
    } else {
        // ☁️ CLOUD FALLBACK for Gujarati and other regional languages
        // This is much more reliable when local voice packs are missing
        showToast(`☁️ Speaking in ${langName} (Cloud Mode)...`, "info", 2000);
        
        // Chunk text into sentences to avoid URL length limits
        const chunks = text.match(/[^.!?]+[.!?]+/g) || [text];
        let chunkIdx = 0;

        function playNextChunk() {
            if (chunkIdx >= chunks.length || !currentAudio) return;
            const currentText = chunks[chunkIdx++].trim();
            if (!currentText) { playNextChunk(); return; }

            // USE INTERNAL BACKEND TTS (More stable and avoids CORS/blocking)
            const url = `/tts?text=${encodeURIComponent(currentText)}&lang=${langCode}`;
            const audio = new Audio(url);
            currentAudio = audio; 
            audio.onended = playNextChunk;
            audio.onerror = () => {
                console.error("Cloud TTS Chunk Error");
                showToast("❌ Speech error. Please check internet.", "error");
            };
            audio.play().catch(e => console.warn("Autoplay blocked or failed", e));
        }

        // Initialize currentAudio so stopSpeech can find it
        currentAudio = { pause: () => { if (currentAudio && currentAudio.pause) currentAudio.pause(); } }; 
        playNextChunk();
    }
}

// Ensure voices are loaded (some browsers need this event)
window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };

function stopSpeech() {
    // Stop native speech
    window.speechSynthesis.cancel();
    
    // Stop cloud audio if playing
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
    
    showToast("⏹ Speech stopped.", "info", 1000);
}

// ================================
// 🎙️ VOICE SEARCH (STT)
// ================================
function startVoiceSearch() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        return showToast("❌ Voice search not supported in this browser.", "error");
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US'; 
    recognition.interimResults = false;

    const micBtn = document.getElementById("micBtn");
    if (micBtn) micBtn.innerHTML = "🔴";

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const input = document.getElementById("newsSearchInput");
        if (input) {
            input.value = transcript;
            // Trigger the existing filter function
            if (typeof filterNewsByKeyword === "function") {
                filterNewsByKeyword();
            }
        }
        showToast(`🔍 Searching for: "${transcript}"`, "info");
    };

    recognition.onerror = () => {
        showToast("❌ Voice recognition error.", "error");
        if (micBtn) micBtn.innerHTML = "🎙️";
    };

    recognition.onend = () => {
        if (micBtn) micBtn.innerHTML = "🎙️";
    };

    recognition.start();
    showToast("🎙️ Listening... Speak now.", "info");
}

function exportToPDF(title, areaId) {
    const el = document.getElementById(areaId);
    if (!el) return showToast("❌ Export area not found", "error");

    showToast("⌛ Generating Perfect Multilingual PDF...");

    const { jsPDF } = window.jspdf;
    
    // 1. Create a hidden "Print Template" that looks BEAUTIFUL
    const printTemplate = document.createElement('div');
    printTemplate.style.width = '800px';
    printTemplate.style.background = '#ffffff';
    printTemplate.style.color = '#1f2937';
    printTemplate.style.fontFamily = 'Arial, sans-serif';
    printTemplate.style.position = 'absolute';
    printTemplate.style.left = '-9999px';
    printTemplate.style.top = '0';
    printTemplate.style.padding = '0';
    printTemplate.style.zIndex = '-1';

    const summaryEl = el.querySelector('#dashboardSummary') || el.querySelector('#modalSummary') || el.querySelector('#vhSummary');
    const newsEl = el.querySelector('#fullNewsBox') || el.querySelector('#modalFullNews') || el.querySelector('#vhFullNews');
    
    const summaryText = summaryEl ? summaryEl.innerText : "No summary";
    const newsText = newsEl ? newsEl.innerText : "No news content";

    printTemplate.innerHTML = `
        <div style="background:#2563eb; color:white; padding:40px; text-align:left;">
            <h1 style="margin:0; font-size:32px;">QuickNewsAI Report</h1>
            <p style="margin:10px 0 0 0; opacity:0.8; font-size:14px;">Generated on: ${new Date().toLocaleString()}</p>
        </div>
        <div style="padding:40px;">
            <h2 style="font-size:22px; color:#111827; margin-bottom:30px;">${title || 'News Update'}</h2>
            
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:25px; margin-bottom:30px;">
                <h4 style="color:#2563eb; margin:0 0 15px 0; font-size:14px; text-transform:uppercase; letter-spacing:1px;">🧠 AI Summary</h4>
                <p style="margin:0; font-size:16px; line-height:1.6; color:#374151;">${summaryText}</p>
            </div>
            
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:25px;">
                <h4 style="color:#2563eb; margin:0 0 15px 0; font-size:14px; text-transform:uppercase; letter-spacing:1px;">📰 Full News</h4>
                <p style="margin:0; font-size:15px; line-height:1.7; color:#4b5563; white-space:pre-line;">${newsText}</p>
            </div>
        </div>
        <div style="padding:20px; text-align:center; color:#94a3b8; font-size:12px; border-top:1px solid #f1f5f9;">
            QuickNewsAI — Your Multilingual News Companion
        </div>
    `;

    document.body.appendChild(printTemplate);

    // 2. Render Template to Canvas (Perfect for Hindi/Gujarati)
    html2canvas(printTemplate, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff'
    }).then(canvas => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('p', 'mm', 'a4');
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
        
        // Handle multipage automatically if needed
        let heightLeft = pdfHeight;
        let position = 0;
        const pageHeight = pdf.internal.pageSize.getHeight();

        pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, pdfHeight);
        heightLeft -= pageHeight;

        while (heightLeft >= 0) {
            position = heightLeft - pdfHeight;
            pdf.addPage();
            pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, pdfHeight);
            heightLeft -= pageHeight;
        }

        const fileName = `${(title || 'news_report').substring(0, 30)}.pdf`;
        pdf.save(fileName);
        
        // Preview
        const blob = pdf.output('blob');
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');

        // Cleanup
        document.body.removeChild(printTemplate);
        showToast("✅ Multilingual PDF Ready!");
    }).catch(err => {
        console.error("PDF Export Error:", err);
        showToast("❌ PDF Export Failed", "error");
        if (printTemplate.parentNode) document.body.removeChild(printTemplate);
    });
}

// ================================
// PWA & CHATBOT
// ================================
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}

let chatContext = '';

function toggleChat() {
    const panel = document.getElementById('chatPanel');
    if (!panel) return;
    const isOpen = panel.style.display !== 'none' && panel.style.display !== '';
    panel.style.display = isOpen ? 'none' : 'flex';
    const icon = document.getElementById('chatBtnIcon');
    if (icon) icon.textContent = isOpen ? '💬' : '✕';

    if (!isOpen) {
        document.getElementById('chatInput')?.focus();
        const ctxEl = document.getElementById('dashboardSummary') || document.getElementById('modalSummary') || document.getElementById('vhSummary');
        if (ctxEl) chatContext = ctxEl.innerText;
    }
}

function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input?.value.trim();
    if (!msg) return;

    const container = document.getElementById('chatMessages');
    if (!container) return;

    const uMsg = document.createElement('div');
    uMsg.className = 'chat-bubble user-bubble';
    uMsg.innerText = msg;
    container.appendChild(uMsg);
    input.value = '';

    const tId = 'bot-' + Date.now();
    const bMsg = document.createElement('div');
    bMsg.className = 'chat-bubble bot-bubble';
    bMsg.id = tId;
    bMsg.innerText = '⏳ Thinking...';
    container.appendChild(bMsg);
    container.scrollTop = container.scrollHeight;

    fetch('/api/qna', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: msg, context: chatContext || msg })
    })
    .then(r => r.json())
    .then(data => {
        const el = document.getElementById(tId);
        if (el) el.innerText = data.answer || 'No answer found.';
        container.scrollTop = container.scrollHeight;
    });
}

// ✅ Theme initialization on page load
document.addEventListener("DOMContentLoaded", () => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") {
        document.body.classList.add("dark-mode");
        document.documentElement.classList.add("dark-mode");
        const icon = document.getElementById("darkIcon");
        if (icon) icon.innerText = "☀️";
    }
});
