/**
 * DOD Platform - Global JavaScript Utilities
 * This file provides reusable functionality for the entire platform
 */

// Toast Notification System
class Toast {
    constructor() {
        this.toasts = [];
        this.container = this.initContainer();
    }

    initContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed top-4 right-4 z-50 space-y-2 max-w-sm';
            document.body.appendChild(container);
        }
        return container;
    }

    show(message, type = 'info', duration = 5000) {
        const id = Date.now();
        const toast = {
            id,
            message,
            type
        };

        // If Alpine.js is available, use it for reactive updates
        if (window.Alpine && window.Alpine.store) {
            setTimeout(() => {
                const toasts = window.Alpine.store('toasts');
                if (toasts) {
                    toasts.push({ id, message, type });
                    setTimeout(() => {
                        const idx = toasts.findIndex(t => t.id === id);
                        if (idx > -1) toasts.splice(idx, 1);
                    }, duration);
                }
            });
        } else {
            // Fallback: DOM manipulation
            const toastEl = document.createElement('div');
            toastEl.className = `alert alert-${type}`;
            toastEl.innerHTML = `
                <div class="flex-1">${message}</div>
                <button onclick="this.parentElement.remove()" class="text-current hover:opacity-70">
                    <span class="text-xl">×</span>
                </button>
            `;
            this.container.appendChild(toastEl);

            // Auto remove after duration
            setTimeout(() => {
                toastEl.remove();
            }, duration);
        }
    }

    success(message, duration = 5000) {
        this.show(message, 'success', duration);
    }

    error(message, duration = 5000) {
        this.show(message, 'error', duration);
    }

    warning(message, duration = 5000) {
        this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        this.show(message, 'info', duration);
    }
}

// Initialize Toast globally
window.Toast = new Toast();

// Utility Functions
const DOD = {
    // Copy text to clipboard
    copyToClipboard: function(text, callback) {
        navigator.clipboard.writeText(text).then(() => {
            window.Toast.success('Copied to clipboard');
            if (callback) callback();
        }).catch(err => {
            window.Toast.error('Failed to copy');
            console.error(err);
        });
    },

    // Confirm action with modal
    confirm: function(title, message, callback) {
        const confirmed = window.confirm(`${title}\n\n${message}`);
        if (confirmed) callback();
    },

    // Format currency
    formatCurrency: function(amount, currency = 'USD') {
        const formatter = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 8
        });
        return formatter.format(amount);
    },

    // Format date
    formatDate: function(date, format = 'en-US') {
        return new Date(date).toLocaleDateString(format);
    },

    // Format time ago
    formatTimeAgo: function(date) {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + ' years ago';
        
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + ' months ago';
        
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + ' days ago';
        
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + ' hours ago';
        
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + ' minutes ago';
        
        return Math.floor(seconds) + ' seconds ago';
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    },

    // Throttle function
    throttle: function(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // API call with error handling
    api: function(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            }
        };

        return fetch(url, { ...defaultOptions, ...options })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login/';
                    }
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                window.Toast.error('An error occurred: ' + error.message);
                throw error;
            });
    }
};

// Make DOD globally available
window.DOD = DOD;

// Initialize Alpine.js if available
document.addEventListener('DOMContentLoaded', function() {
    // HTMX Configuration
    if (window.htmx) {
        htmx.config.defaultIndicatorStyle = 'spinner';
        htmx.config.refreshOnHistoryMiss = true;

        // HTMX event handlers
        document.body.addEventListener('htmx:promptCancelled', function(evt) {
            console.log('HTMX prompt cancelled');
        });

        document.body.addEventListener('htmx:responseError', function(evt) {
            window.Toast.error('Request failed. Please try again.');
        });

        document.body.addEventListener('htmx:sendError', function(evt) {
            window.Toast.error('Network error. Please check your connection.');
        });
    }

    // Alpine.js initialization
    if (window.Alpine) {
        window.Alpine.store('toasts', []);
        window.Alpine.store('loading', false);
    }

    // Initialize tooltips (if Popper.js is available)
    if (window.Popper) {
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            new Popper(el, {
                placement: el.dataset.tooltipPlacement || 'top',
                modifiers: {
                    offset: {
                        offset: '0, 10'
                    }
                }
            });
        });
    }
});

// Automatic form submission with loading state
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form[data-auto-submit]').forEach(form => {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('[type="submit"]');
            if (btn) {
                btn.disabled = true;
                const originalText = btn.textContent;
                btn.innerHTML = '<span class="spinner mr-2"></span>Processing...';
            }
        });
    });
});

// Handle responsive table scrolling
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('table').forEach(table => {
        const wrapper = document.createElement('div');
        wrapper.className = 'overflow-x-auto';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
});
