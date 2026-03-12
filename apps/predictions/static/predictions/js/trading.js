/* Trading functionality */

class TradeManager {
    constructor(marketId) {
        this.marketId = marketId;
        this.tradeForms = document.querySelectorAll('.trade-form');
        this.init();
    }

    init() {
        this.tradeForms.forEach(form => {
            this.setupFormListeners(form);
        });
    }

    setupFormListeners(form) {
        const amountInput = form.querySelector('.amount-input');
        const side = form.dataset.side;
        
        // Debounced preview update
        let previewTimeout;
        amountInput.addEventListener('input', () => {
            clearTimeout(previewTimeout);
            previewTimeout = setTimeout(() => this.updatePreview(form, side), 300);
        });

        // Form submission
        form.addEventListener('submit', (e) => this.handleSubmit(e, form, side));
    }

    async updatePreview(form, side) {
        const amount = parseFloat(form.querySelector('.amount-input').value) || 0;
        
        if (amount <= 0) {
            form.querySelector('.trade-preview').style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/predictions/preview_buy/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `market_id=${this.marketId}&side=${side}&amount=${amount}`
            });

            if (!response.ok) {
                throw new Error('Preview failed');
            }

            const data = await response.json();

            if (data.error) {
                this.showError(form, data.error);
            } else {
                this.showPreview(form, side, data);
            }
        } catch (error) {
            console.error('Preview error:', error);
        }
    }

    showPreview(form, side, data) {
        const preview = form.querySelector('.trade-preview');
        const errorDiv = form.querySelector('.error-message');

        errorDiv.style.display = 'none';
        preview.style.display = 'block';

        form.querySelector(`#shares-${side}`).textContent = 
            (parseFloat(data.shares) || 0).toFixed(2);
        form.querySelector(`#avg-price-${side}`).textContent = 
            '$' + (parseFloat(data.avg_price) || 0).toFixed(4);
        form.querySelector(`#slippage-${side}`).textContent = 
            (parseFloat(data.slippage) || 0).toFixed(2) + '%';
        form.querySelector(`#fee-${side}`).textContent = 
            '$' + (parseFloat(data.fee) || 0).toFixed(2);
        form.querySelector(`#total-${side}`).textContent = 
            '$' + (parseFloat(data.total) || 0).toFixed(2);
    }

    showError(form, error) {
        const errorDiv = form.querySelector('.error-message');
        const preview = form.querySelector('.trade-preview');

        errorDiv.textContent = '❌ ' + error;
        errorDiv.style.display = 'block';
        preview.style.display = 'none';
    }

    async handleSubmit(e, form, side) {
        e.preventDefault();

        const amount = parseFloat(form.querySelector('.amount-input').value);
        if (amount <= 0) {
            this.showError(form, 'Введите корректную сумму');
            return;
        }

        const submitBtn = form.querySelector('[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Обработка...';

        try {
            const response = await fetch(`/predictions/trade/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `market_id=${this.marketId}&action=buy&side=${side}&amount=${amount}`
            });

            const data = await response.json();

            if (data.error) {
                this.showError(form, data.error);
            } else {
                // Success!
                showToast(`✅ Куплено ${data.shares.toFixed(2)} долей`, 'success');
                form.querySelector('.amount-input').value = '';
                form.querySelector('.trade-preview').style.display = 'none';

                // Reload after delay
                setTimeout(() => window.location.reload(), 1500);
            }
        } catch (error) {
            this.showError(form, 'Ошибка сервера: ' + error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
}

// Initialize trading on page load
document.addEventListener('DOMContentLoaded', function() {
    const marketId = document.querySelector('[data-market-id]')?.dataset.marketId;
    if (marketId) {
        new TradeManager(marketId);
    }
});

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
