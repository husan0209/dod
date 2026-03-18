// Mini App JavaScript
// static/miniapp/js/app.js

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Initialize navigation
    initializeNavigation();

    // Initialize modals
    initializeModals();

    // Initialize forms
    initializeForms();

    // Initialize pull-to-refresh
    initializePullToRefresh();

    console.log('Mini App initialized');
}

// Navigation handling
function initializeNavigation() {
    // Handle navigation tab clicks
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            haptic?.select();

            const tabName = tab.dataset.tab;
            navigateToTab(tabName);

            // Update URL without page reload
            const url = tab.getAttribute('href');
            if (url) {
                window.history.pushState({}, '', url);
                updateBackButton();
            }
        });
    });

    // Handle browser back/forward
    window.addEventListener('popstate', () => {
        // Reload page on back/forward for simplicity
        window.location.reload();
    });

    // Set active tab based on current URL
    setActiveTabFromUrl();
}

function navigateToTab(tabName) {
    // Update active tab styling
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        }
    });

    // Save preference to DeviceStorage
    if (window.tg?.DeviceStorage) {
        window.tg.DeviceStorage.setItem('preferred_tab', tabName);
    }
}

function setActiveTabFromUrl() {
    const path = window.location.pathname;

    let activeTab = 'home';

    if (path.includes('/sports')) {
        activeTab = 'sports';
    } else if (path.includes('/casino')) {
        activeTab = 'casino';
    } else if (path.includes('/predictions')) {
        activeTab = 'predictions';
    } else if (path.includes('/profile')) {
        activeTab = 'profile';
    }

    navigateToTab(activeTab);
}

// Modal handling
function initializeModals() {
    // Close modal on backdrop click
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('tg-modal-backdrop')) {
            closeModal();
        }
    });
}

function showModal(content, title = '') {
    // Remove existing modal
    closeModal();

    const modal = document.createElement('div');
    modal.className = 'tg-modal-backdrop';
    modal.innerHTML = `
        <div class="tg-modal">
            <div class="tg-modal-handle"></div>
            ${title ? `<h2 class="text-lg font-semibold mb-4">${title}</h2>` : ''}
            ${content}
        </div>
    `;

    document.body.appendChild(modal);

    // Animate in
    setTimeout(() => {
        modal.style.opacity = '1';
    }, 10);

    return modal;
}

function closeModal() {
    const modal = document.querySelector('.tg-modal-backdrop');
    if (modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.remove();
        }, 200);
    }
}

// Form handling
function initializeForms() {
    // Handle form submissions with HTMX
    document.addEventListener('htmx:beforeRequest', (e) => {
        // Show loading state
        const form = e.target;
        if (form.tagName === 'FORM') {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '⏳ Загрузка...';
            }
        }
    });

    document.addEventListener('htmx:afterRequest', (e) => {
        // Reset loading state
        const form = e.target;
        if (form.tagName === 'FORM') {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') ||
                                    submitBtn.innerHTML.replace('⏳ Загрузка...', 'Отправить');
            }
        }
    });
}

// Pull to refresh
function initializePullToRefresh() {
    let startY = 0;
    let isPulling = false;
    const threshold = 80;

    document.addEventListener('touchstart', (e) => {
        startY = e.touches[0].clientY;
    });

    document.addEventListener('touchmove', (e) => {
        const currentY = e.touches[0].clientY;
        const pullDistance = currentY - startY;

        if (pullDistance > threshold && window.scrollY === 0 && !isPulling) {
            isPulling = true;
            showPullToRefresh();
        }
    });

    document.addEventListener('touchend', () => {
        if (isPulling) {
            isPulling = false;
            hidePullToRefresh();
            // Trigger refresh
            location.reload();
        }
    });
}

function showPullToRefresh() {
    let refreshIndicator = document.querySelector('.pull-to-refresh');
    if (!refreshIndicator) {
        refreshIndicator = document.createElement('div');
        refreshIndicator.className = 'pull-to-refresh';
        refreshIndicator.innerHTML = '🔄 Потяните для обновления';
        document.body.insertBefore(refreshIndicator, document.body.firstChild);
    }
    refreshIndicator.style.display = 'block';
}

function hidePullToRefresh() {
    const refreshIndicator = document.querySelector('.pull-to-refresh');
    if (refreshIndicator) {
        refreshIndicator.style.display = 'none';
    }
}

// Utility functions
function showNotificationsModal() {
    const content = `
        <div id="notifications-list">
            <div class="text-center text-tg-hint py-8">
                Уведомлений пока нет
            </div>
        </div>
        <button class="tg-btn mt-4" onclick="closeModal()">Закрыть</button>
    `;
    showModal(content, 'Уведомления');
}

function formatCurrency(amount, currency = 'USD') {
    const symbols = {
        'USD': '$',
        'EUR': '€',
        'RUB': '₽',
        'BTC': '₿',
        'USDT': '💎',
        'TON': '💎'
    };

    const symbol = symbols[currency] || currency;
    return `${symbol}${parseFloat(amount).toFixed(2)}`;
}

function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('JavaScript error:', e.error);
    // Could send error to server for logging
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    // Could send error to server for logging
});

// Export functions globally
window.showModal = showModal;
window.closeModal = closeModal;
window.showNotificationsModal = showNotificationsModal;
window.formatCurrency = formatCurrency;
window.formatNumber = formatNumber;
