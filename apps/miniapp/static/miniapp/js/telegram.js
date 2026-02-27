// Telegram Mini App SDK Integration
// static/miniapp/js/telegram.js

const tg = window.Telegram?.WebApp;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (!tg) {
        console.warn('Telegram WebApp SDK not available');
        return;
    }

    // 1. Expand to full screen (remove Telegram's interface)
    tg.expand();
    tg.isClosingConfirmationEnabled = true;

    // 2. Apply Telegram theme
    applyTelegramTheme();

    // 3. Setup back button
    setupBackButton();

    // 4. Send initData to server via HTMX headers
    setupInitDataHeaders();

    // 5. Update back button visibility
    updateBackButton();

    // 6. Handle viewport changes (for safe area)
    tg.onEvent('viewportChanged', (event) => {
        document.documentElement.style.setProperty(
            '--tg-viewport-height',
            `${event.viewportHeight}px`
        );
        document.documentElement.style.setProperty(
            '--tg-viewport-stable-height',
            `${event.viewportStableHeight || event.viewportHeight}px`
        );
    });

    // 7. DeviceStorage for settings (Bot API 9.0+)
    if (tg.DeviceStorage) {
        // Load saved tab preference
        tg.DeviceStorage.getItem('preferred_tab', (err, val) => {
            if (val && !err) {
                navigateToTab(val);
            }
        });
    }

    // 8. Handle theme changes
    tg.onEvent('themeChanged', () => {
        applyTelegramTheme();
    });

    // 9. Handle popup closing
    tg.onEvent('popupClosed', (event) => {
        console.log('Popup closed:', event);
    });

    console.log('Telegram Mini App initialized');
});

// Apply Telegram theme colors to CSS variables
function applyTelegramTheme() {
    const tp = tg.themeParams;

    const root = document.documentElement;

    // Set theme colors as CSS variables
    root.style.setProperty('--tg-bg', tp.bg_color || '#1a1a2e');
    root.style.setProperty('--tg-text', tp.text_color || '#ffffff');
    root.style.setProperty('--tg-hint', tp.hint_color || '#999999');
    root.style.setProperty('--tg-link', tp.link_color || '#00e701');
    root.style.setProperty('--tg-btn', tp.button_color || '#00e701');
    root.style.setProperty('--tg-btn-text', tp.button_text_color || '#ffffff');
    root.style.setProperty('--tg-secondary', tp.secondary_bg_color || '#16213e');
    root.style.setProperty('--tg-header', tp.header_bg_color || '#0f3460');
    root.style.setProperty('--tg-section', tp.section_bg_color || '#16213e');

    // Update header and background colors
    tg.setHeaderColor(tp.header_bg_color || '#0f3460');
    tg.setBackgroundColor(tp.bg_color || '#1a1a2e');
}

// Setup back button behavior
function setupBackButton() {
    // Show/hide Telegram's back button based on history
    tg.BackButton.onClick(() => {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            tg.close();
        }
    });
}

// Update back button visibility
function updateBackButton() {
    const isHomePage = window.location.pathname === '/tg/' ||
                      window.location.pathname === '/tg';
    if (tg.BackButton) {
        if (isHomePage) {
            tg.BackButton.hide();
        } else {
            tg.BackButton.show();
        }
    }

    // Update DOM back button
    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
        backBtn.style.display = isHomePage ? 'none' : 'block';
    }
}

// Setup HTMX headers for initData
function setupInitDataHeaders() {
    const getCsrfToken = () => {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    };

    // Set headers for all HTMX requests
    document.body.setAttribute(
        'hx-headers',
        JSON.stringify({
            'X-Telegram-Init-Data': tg.initData || '',
            'X-CSRFToken': getCsrfToken(),
        })
    );
}

// Navigation helpers
function navigateToTab(tabName) {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        }
    });

    // Save preference
    if (tg.DeviceStorage) {
        tg.DeviceStorage.setItem('preferred_tab', tabName);
    }
}

// Haptic feedback wrapper
const haptic = {
    light: () => tg?.HapticFeedback?.impactOccurred('light'),
    medium: () => tg?.HapticFeedback?.impactOccurred('medium'),
    heavy: () => tg?.HapticFeedback?.impactOccurred('heavy'),
    success: () => tg?.HapticFeedback?.notificationOccurred('success'),
    warning: () => tg?.HapticFeedback?.notificationOccurred('warning'),
    error: () => tg?.HapticFeedback?.notificationOccurred('error'),
    select: () => tg?.HapticFeedback?.selectionChanged(),
};

// Telegram-specific functions
function showAlert(message, callback) {
    if (tg && tg.showAlert) {
        tg.showAlert(message, callback);
    } else {
        alert(message);
        if (callback) callback();
    }
}

function showConfirm(message, callback) {
    if (tg && tg.showConfirm) {
        tg.showConfirm(message, callback);
    } else {
        const result = confirm(message);
        callback(result);
    }
}

function openLink(url, options) {
    if (tg && tg.openLink) {
        tg.openLink(url, options);
    } else {
        window.open(url, '_blank');
    }
}

function openInvoice(invoiceUrl, callback) {
    if (tg && tg.openInvoice) {
        tg.openInvoice(invoiceUrl, callback);
    } else {
        console.warn('openInvoice not available');
        callback({ status: 'error' });
    }
}

function switchInlineQuery(query, chatTypes) {
    if (tg && tg.switchInlineQuery) {
        tg.switchInlineQuery(query, chatTypes);
    } else {
        console.warn('switchInlineQuery not available');
    }
}

// Handle history changes for back button
window.addEventListener('popstate', () => {
    updateBackButton();
});

// Handle HTMX navigation
document.addEventListener('htmx:afterSwap', () => {
    updateBackButton();
});

// Export functions globally
window.haptic = haptic;
window.tgShowAlert = showAlert;
window.tgShowConfirm = showConfirm;
window.tgOpenLink = openLink;
window.tgOpenInvoice = openInvoice;
window.tgSwitchInlineQuery = switchInlineQuery;
window.updateBackButton = updateBackButton;
