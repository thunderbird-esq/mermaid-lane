/**
 * IPTV Web - Utility Functions
 */

const Utils = {
    /**
     * Debounce function calls
     */
    debounce(fn, delay = 300) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    /**
     * Throttle function calls
     */
    throttle(fn, limit = 100) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Format time for display
     */
    formatTime(date) {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    /**
     * Format duration in minutes
     */
    formatDuration(minutes) {
        if (minutes < 60) {
            return `${minutes}m`;
        }
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Get quality badge text from quality string
     */
    parseQuality(qualityStr) {
        if (!qualityStr) return null;

        const lower = qualityStr.toLowerCase();
        if (lower.includes('4k') || lower.includes('2160')) return '4K';
        if (lower.includes('1080')) return '1080p';
        if (lower.includes('720')) return '720p';
        if (lower.includes('480')) return '480p';
        if (lower.includes('360')) return '360p';

        return qualityStr;
    },

    /**
     * Get category icon
     */
    getCategoryIcon(categoryId) {
        const icons = {
            news: '📰',
            sports: '⚽',
            movies: '🎬',
            entertainment: '🎭',
            kids: '🧸',
            music: '🎵',
            documentary: '🎥',
            education: '📚',
            religious: '⛪',
            general: '📺',
            lifestyle: '🏠',
            travel: '✈️',
            cooking: '🍳',
            weather: '🌤️',
            science: '🔬',
            series: '📺',
            comedy: '😂',
            animation: '🎨',
            shop: '🛒',
            outdoor: '🏕️',
            auto: '🚗',
            culture: '🎭',
            business: '💼',
            classic: '📻',
            xxx: '🔞'
        };
        return icons[categoryId] || '📺';
    },

    /**
     * Create element with attributes and children
     */
    createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);

        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else if (key.startsWith('on')) {
                element.addEventListener(key.slice(2).toLowerCase(), value);
            } else {
                element.setAttribute(key, value);
            }
        });

        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child) {
                element.appendChild(child);
            }
        });

        return element;
    },

    /**
     * Show element
     */
    show(element) {
        element.classList.remove('hidden');
    },

    /**
     * Hide element
     */
    hide(element) {
        element.classList.add('hidden');
    },

    /**
     * Toggle element visibility
     */
    toggle(element) {
        element.classList.toggle('hidden');
    },

    /**
     * Local storage helpers
     */
    storage: {
        get(key, defaultValue = null) {
            try {
                const value = localStorage.getItem(key);
                return value ? JSON.parse(value) : defaultValue;
            } catch {
                return defaultValue;
            }
        },

        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn('LocalStorage error:', e);
            }
        },

        remove(key) {
            localStorage.removeItem(key);
        }
    },

    /**
     * Generate placeholder logo URL
     */
    getPlaceholderLogo(name) {
        const initial = (name || '?')[0].toUpperCase();
        return `data:image/svg+xml,${encodeURIComponent(`
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
                <rect width="64" height="64" fill="#1a1a24"/>
                <text x="32" y="40" font-size="24" font-family="Inter, sans-serif" 
                      fill="#606070" text-anchor="middle">${initial}</text>
            </svg>
        `)}`;
    }
};

// Make available globally
window.Utils = Utils;
