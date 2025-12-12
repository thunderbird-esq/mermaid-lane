/**
 * IPTV Web - Main Application
 * Initializes all modules and sets up the application
 */

const App = {
    /**
     * Initialize the application
     */
    async init() {
        console.log('🚀 IPTV Web starting...');

        try {
            // Initialize modules
            Favorites.init();
            Player.init();
            EPG.init();
            await Channels.init();

            // Set up theme toggle
            this.initTheme();

            // Set up favorites filter in sidebar
            this.initFavoritesFilter();

            // Set up continue watching filter
            this.initContinueWatching();

            // Load stats
            this.loadStats();

            console.log('✅ IPTV Web ready!');
        } catch (error) {
            console.error('❌ Failed to initialize:', error);
            this.showError('Failed to load application. Please refresh the page.');
        }
    },

    /**
     * Initialize favorites filter in sidebar
     */
    initFavoritesFilter() {
        const countryList = document.getElementById('country-list');
        if (countryList) {
            // Insert favorites filter at the top
            const favItem = Utils.createElement('div', {
                className: 'filter-item favorites-filter',
                onClick: () => this.showFavorites()
            }, [
                Utils.createElement('span', { className: 'filter-icon' }, ['⭐']),
                Utils.createElement('span', { className: 'filter-name' }, ['My Favorites']),
                Utils.createElement('span', { className: 'filter-count', id: 'favorites-count' },
                    [String(Favorites.count())])
            ]);

            // Insert after "All Countries"
            const allCountries = countryList.querySelector('.filter-item');
            if (allCountries && allCountries.nextSibling) {
                countryList.insertBefore(favItem, allCountries.nextSibling);
            } else {
                countryList.appendChild(favItem);
            }

            // Update count when favorites change
            Favorites.onChange(() => {
                const countEl = document.getElementById('favorites-count');
                if (countEl) countEl.textContent = String(Favorites.count());
            });
        }
    },

    /**
     * Show only favorite channels
     */
    async showFavorites() {
        const favoriteIds = Favorites.getAll();

        if (favoriteIds.length === 0) {
            Channels.elements.grid.innerHTML = `
                <div class="loading-container">
                    <p>No favorites yet. Click the ⭐ on channels to add them!</p>
                </div>
            `;
            Channels.elements.channelCount.textContent = '0 favorites';
            Channels.elements.contentTitle.textContent = '⭐ My Favorites';
            Utils.hide(Channels.elements.loadMore);
            return;
        }

        // Update UI
        Channels.elements.contentTitle.textContent = '⭐ My Favorites';
        Channels.elements.grid.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <p>Loading favorites...</p>
            </div>
        `;

        // Clear active states from country/category filters
        document.querySelectorAll('.filter-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector('.favorites-filter')?.classList.add('active');

        // Fetch each favorite channel
        const channels = [];
        for (const id of favoriteIds) {
            try {
                const channel = await API.getChannel(id);
                channels.push(channel);
            } catch (e) {
                console.warn(`Failed to load favorite ${id}:`, e);
            }
        }

        Channels.elements.grid.innerHTML = '';
        Channels.channels = channels;
        Channels.renderChannels(channels);
        Channels.elements.channelCount.textContent = `${channels.length} favorites`;
        Utils.hide(Channels.elements.loadMore);
    },

    /**
     * Show continue watching (watch history)
     */
    async showContinueWatching() {
        const history = Favorites.getHistory();

        if (history.length === 0) {
            Channels.elements.grid.innerHTML = `
                <div class="loading-container">
                    <p>No watch history yet. Start watching some channels!</p>
                </div>
            `;
            Channels.elements.channelCount.textContent = '0 channels';
            Channels.elements.contentTitle.textContent = '📺 Continue Watching';
            Utils.hide(Channels.elements.loadMore);
            return;
        }

        // Update UI
        Channels.elements.contentTitle.textContent = '📺 Continue Watching';
        Channels.elements.grid.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <p>Loading history...</p>
            </div>
        `;

        // Clear active states
        document.querySelectorAll('.filter-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector('.history-filter')?.classList.add('active');

        // Fetch each channel from history
        const channels = [];
        for (const item of history) {
            try {
                const channel = await API.getChannel(item.id);
                channels.push(channel);
            } catch (e) {
                console.warn(`Failed to load channel ${item.id}:`, e);
            }
        }

        Channels.elements.grid.innerHTML = '';
        Channels.channels = channels;
        Channels.renderChannels(channels);
        Channels.elements.channelCount.textContent = `${channels.length} recently watched`;
        Utils.hide(Channels.elements.loadMore);
    },

    /**
     * Initialize continue watching filter in sidebar
     */
    initContinueWatching() {
        const countryList = document.getElementById('country-list');
        if (countryList) {
            // Insert continue watching filter
            const historyItem = Utils.createElement('div', {
                className: 'filter-item history-filter',
                onClick: () => this.showContinueWatching()
            }, [
                Utils.createElement('span', { className: 'filter-icon' }, ['📺']),
                Utils.createElement('span', { className: 'filter-name' }, ['Continue Watching']),
                Utils.createElement('span', { className: 'filter-count', id: 'history-count' },
                    [String(Favorites.getHistory().length)])
            ]);

            // Insert after favorites filter
            const favoritesFilter = countryList.querySelector('.favorites-filter');
            if (favoritesFilter && favoritesFilter.nextSibling) {
                countryList.insertBefore(historyItem, favoritesFilter.nextSibling);
            } else if (favoritesFilter) {
                countryList.appendChild(historyItem);
            } else {
                // Fallback if favorites filter isn't present for some reason
                const allCountries = countryList.querySelector('.filter-item');
                if (allCountries && allCountries.nextSibling) {
                    countryList.insertBefore(historyItem, allCountries.nextSibling);
                } else {
                    countryList.appendChild(historyItem);
                }
            }

            // Update count when history changes (assuming Favorites provides a way to listen)
            if (Favorites.onHistoryChange) { // Assuming Favorites module will expose this
                Favorites.onHistoryChange(() => {
                    const countEl = document.getElementById('history-count');
                    if (countEl) countEl.textContent = String(Favorites.getHistory().length);
                });
            }
        }
    },

    /**
     * Initialize theme handling
     */
    initTheme() {
        const themeToggle = document.getElementById('theme-toggle');

        // Load saved theme
        const savedTheme = Utils.storage.get('theme', 'dark');
        document.documentElement.dataset.theme = savedTheme;
        this.updateThemeIcon(themeToggle, savedTheme);

        // Toggle handler
        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.dataset.theme || 'dark';
            const next = current === 'dark' ? 'light' : 'dark';

            document.documentElement.dataset.theme = next;
            Utils.storage.set('theme', next);
            this.updateThemeIcon(themeToggle, next);
        });
    },

    /**
     * Update theme toggle icon
     */
    updateThemeIcon(button, theme) {
        button.textContent = theme === 'dark' ? '🌙' : '☀️';
    },

    /**
     * Load and display stats
     */
    async loadStats() {
        try {
            const stats = await API.getStats();
            console.log('📊 Stats:', stats);
        } catch (error) {
            console.warn('Could not load stats:', error);
        }
    },

    /**
     * Show global error message
     */
    showError(message) {
        const grid = document.getElementById('channel-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="loading-container">
                    <p style="color: var(--error);">${Utils.escapeHtml(message)}</p>
                    <button onclick="location.reload()" class="retry-btn">Refresh Page</button>
                </div>
            `;
        }
    }
};

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Make available globally
window.App = App;
