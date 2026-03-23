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
    const text = document.getElementById("darkText");

    if (isDark) {
        if (icon) icon.innerText = "☀️";
        if (text) text.innerText = "Light Mode";
        localStorage.setItem("theme", "dark");
    } else {
        if (icon) icon.innerText = "🌙";
        if (text) text.innerText = "Dark Mode";
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
let currentPage = 1;
let currentCategory = "general";

const loadMoreBtn = document.getElementById("loadMoreBtn");
const newsContainer = document.getElementById("newsContainer");

function renderNewsCard(news) {
    if (!newsContainer) return;

    const col = document.createElement("div");
    col.className = "col-md-4 col-lg-3 py-3";
    col.innerHTML = `
        <div class="news-card h-100 shadow-sm border-0 rounded-4 overflow-hidden" 
             style="cursor:pointer;"
             data-url="${news.url}" 
             data-title="${news.title.replace(/"/g, '&quot;')}">
            <div class="news-img" style="height:160px; overflow:hidden;">
                <img src="${news.urlToImage || '/static/img/news_placeholder.jpg'}" 
                     class="w-100 h-100 object-fit-cover transition-all"
                     onerror="handleImgError(this)" 
                     style="transition: transform 0.3s ease;">
            </div>
            <div class="news-body p-3">
                <h6 class="news-title fw-bold text-dark mb-1" style="font-size:0.95rem; line-height:1.4;">${news.title}</h6>
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
        playClickSound();
        currentPage += 1;
        loadMoreBtn.innerText = "Loading...";
        loadMoreBtn.disabled = true;

        fetch(`/news?page=${currentPage}&category=${currentCategory}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(newsList => {
            if (!newsList || newsList.length === 0) {
                loadMoreBtn.innerText = "No more news";
                return;
            }
            newsList.forEach(renderNewsCard);
            loadMoreBtn.innerText = "Load More News";
            loadMoreBtn.disabled = false;
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
    currentPage = 1;

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
    .then(newsList => {
        if (newsContainer) {
            newsContainer.innerHTML = "";
            newsList.forEach(renderNewsCard);
        }
    })
    .catch(() => {
        if (newsContainer) newsContainer.innerHTML = "<div class='alert alert-danger'>Error loading news.</div>";
    })
    .finally(() => {
        if (loadMoreBtn) {
            loadMoreBtn.innerText = "Load More News";
            loadMoreBtn.disabled = false;
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

function exportToPDF(title, areaId) {
    const el = document.getElementById(areaId);
    if (!el) return showToast("❌ Export area not found", "error");

    if (typeof html2canvas === "undefined") {
        return showToast("❌ PDF library still loading...", "error");
    }

    showToast("⌛ Generating Perfect PDF...");

    html2canvas(el, { 
        scale: 2, 
        useCORS: true,
        backgroundColor: "#ffffff",
        logging: false,
        onclone: (clonedDoc) => {
            const clonedArea = clonedDoc.getElementById(areaId);
            if (!clonedArea) return;

            // NUCLEAR RESET: Force Pure Black Text and White Background using setProperty (most reliable)
            clonedArea.style.setProperty('background-color', '#ffffff', 'important');
            clonedArea.style.setProperty('color', '#000000', 'important');
            clonedArea.style.setProperty('padding', '20px', 'important');

            const allC = clonedArea.querySelectorAll('*');
            allC.forEach(child => {
                child.style.setProperty('color', '#000000', 'important');
                child.style.setProperty('background-color', 'transparent', 'important');
                child.style.setProperty('border-color', '#000000', 'important');
                child.style.setProperty('box-shadow', 'none', 'important');
                child.style.setProperty('text-shadow', 'none', 'important');
                child.style.setProperty('opacity', '1', 'important');
                child.style.setProperty('visibility', 'visible', 'important');
            });

            // Specific fix for news text and boxes
            const fn = clonedDoc.getElementById('fullNewsBox');
            if (fn) {
                fn.style.setProperty('display', 'block', 'important');
                fn.style.setProperty('color', '#000000', 'important');
            }
            
            const ds = clonedArea.querySelector('#dashboardSummary') || clonedArea.querySelector('#modalSummary') || clonedArea.querySelector('#vhSummary');
            if (ds) {
                ds.style.setProperty('color', '#000000', 'important');
                ds.style.setProperty('display', 'block', 'important');
            }

            // Hide UI buttons
            clonedDoc.querySelectorAll('.no-export').forEach(btn => btn.style.display = 'none');
        }
    }).then(canvas => {
        const imgData = canvas.toDataURL('image/png');
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const imgProps = pdf.getImageProperties(imgData);
        const imgHeight = (imgProps.height * pdfWidth) / imgProps.width;
        
        let heightLeft = imgHeight;
        let position = 0;
        const pageHeight = pdf.internal.pageSize.getHeight();

        // Header for first page
        pdf.setFontSize(18);
        pdf.setTextColor(0, 0, 0); // Pure Black
        pdf.text("QuickNewsAI Report", 15, 15);
        pdf.setFontSize(10);
        pdf.text(`Generated on: ${new Date().toLocaleString()}`, 15, 22);
        
        // Add image
        pdf.addImage(imgData, 'PNG', 0, 30, pdfWidth, imgHeight);
        heightLeft -= (pageHeight - 30);

        while (heightLeft >= 0) {
            position = heightLeft - imgHeight;
            pdf.addPage();
            pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, imgHeight);
            heightLeft -= pageHeight;
        }

        pdf.save(`${(title || 'news_report').substring(0, 30)}.pdf`);
        showToast("✅ Perfect PDF Ready!");

    }).catch(err => {
        console.error("PDF Export Error:", err);
        showToast("❌ PDF Export Failed", "error");
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
        const text = document.getElementById("darkText");
        if (icon) icon.innerText = "☀️";
        if (text) text.innerText = "Light Mode";
    }
});
