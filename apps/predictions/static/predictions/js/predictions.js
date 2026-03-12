/* Main Predictions Market JavaScript */

// Polling for real-time price updates
class PricePoller {
    constructor(marketId, interval = 5000) {
        this.marketId = marketId;
        this.interval = interval;
        this.timeoutId = null;
    }

    start() {
        this.poll();
    }

    stop() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
        }
    }

    poll() {
        fetch(`/predictions/api/market/${this.marketId}/prices/`)
            .then(r => r.json())
            .then(data => {
                this.updatePrices(data);
                this.timeoutId = setTimeout(() => this.poll(), this.interval);
            })
            .catch(err => {
                console.error('Price poll error:', err);
                this.timeoutId = setTimeout(() => this.poll(), this.interval);
            });
    }

    updatePrices(data) {
        // Update YES price
        const yesPrice = document.querySelector('[data-price="yes"]');
        const yesProbability = document.querySelector('[data-prob="yes"]');
        if (yesPrice) yesPrice.textContent = '$' + parseFloat(data.yes_price).toFixed(4);
        if (yesProbability) yesProbability.textContent = (parseFloat(data.yes_price) * 100).toFixed(0) + '%';

        // Update NO price
        const noPrice = document.querySelector('[data-price="no"]');
        const noProbability = document.querySelector('[data-prob="no"]');
        if (noPrice) noPrice.textContent = '$' + parseFloat(data.no_price).toFixed(4);
        if (noProbability) noProbability.textContent = (parseFloat(data.no_price) * 100).toFixed(0) + '%';

        // Update statistics
        if (data.volume_24h) {
            const vol24h = document.querySelector('[data-stat="volume-24h"]');
            if (vol24h) vol24h.textContent = '$' + parseInt(data.volume_24h).toLocaleString();
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Start price poller if on market detail page
    const marketId = document.querySelector('[data-market-id]')?.dataset.marketId;
    if (marketId) {
        const poller = new PricePoller(marketId);
        poller.start();
    }

    // Initialize tooltips
    initTooltips();

    // Initialize animations
    initAnimations();
});

function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(el => {
        el.addEventListener('mouseenter', function() {
            const text = this.dataset.tooltip;
            showTooltip(this, text);
        });
        el.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(el, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    const rect = el.getBoundingClientRect();
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';

    el._tooltip = tooltip;
}

function hideTooltip(e) {
    if (e.target._tooltip) {
        e.target._tooltip.remove();
        delete e.target._tooltip;
    }
}

function initAnimations() {
    // Animate stat values
    const statValues = document.querySelectorAll('[data-animate="value"]');
    statValues.forEach(el => {
        const finalValue = parseFloat(el.textContent);
        const initialValue = 0;
        const duration = 500;

        let startTime = null;
        function animate(currentTime) {
            if (!startTime) startTime = currentTime;
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const value = initialValue + (finalValue - initialValue) * progress;

            if (el.dataset.format === 'currency') {
                el.textContent = '$' + value.toFixed(2);
            } else if (el.dataset.format === 'percent') {
                el.textContent = value.toFixed(1) + '%';
            } else if (el.dataset.format === 'integer') {
                el.textContent = Math.floor(value).toLocaleString();
            } else {
                el.textContent = value.toFixed(2);
            }

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }

        requestAnimationFrame(animate);
    });
}

// Filtering utilities
function filterByCategory() {
    const category = document.getElementById('category')?.value;
    const params = new URLSearchParams(window.location.search);
    
    if (category) {
        params.set('category', category);
    } else {
        params.delete('category');
    }
    
    window.location.search = params.toString();
}

function filterByType() {
    const form = event.target.closest('form');
    if (form) form.submit();
}

// Like functionality
document.querySelectorAll('.like-btn').forEach(btn => {
    btn.addEventListener('click', async function(e) {
        e.preventDefault();
        
        const commentId = this.dataset.commentId;
        if (!commentId) return;

        try {
            const response = await fetch(`/predictions/api/comment/${commentId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                const countEl = this.querySelector('.like-count');
                if (countEl) {
                    countEl.textContent = data.likes_count;
                }
                this.classList.toggle('liked', data.liked);
            }
        } catch (err) {
            console.error('Like error:', err);
        }
    });
});

// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function formatCurrency(value) {
    return '$' + parseFloat(value).toFixed(2);
}

function formatPercent(value) {
    return parseFloat(value).toFixed(1) + '%';
}

function formatInteger(value) {
    return Math.floor(value).toLocaleString();
}

// Modal for confirmation
function showConfirmDialog(title, message, onConfirm, onCancel) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>${title}</h3>
            <p>${message}</p>
            <div class="modal-actions">
                <button class="btn btn-secondary cancel-btn">Отмена</button>
                <button class="btn btn-primary confirm-btn">Подтвердить</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('.confirm-btn').addEventListener('click', () => {
        onConfirm();
        modal.remove();
    });

    modal.querySelector('.cancel-btn').addEventListener('click', () => {
        if (onCancel) onCancel();
        modal.remove();
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            if (onCancel) onCancel();
            modal.remove();
        }
    });
}

// Toast notifications
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Number formatting
function formatLargeNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toFixed(0);
}
