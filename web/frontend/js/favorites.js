/**
 * IPTV Web - Favorites Manager
 * Handles favorite channels with localStorage persistence
 */

const Favorites = {
    // Storage key
    STORAGE_KEY: 'iptv_favorites',

    // Cached favorites set
    favorites: new Set(),

    // Event listeners
    listeners: [],

    /**
     * Initialize favorites
     */
    init() {
        this.load();
        console.log(`Favorites initialized: ${this.favorites.size} channels`);
    },

    /**
     * Load favorites from localStorage
     */
    load() {
        const stored = Utils.storage.get(this.STORAGE_KEY, []);
        this.favorites = new Set(stored);
    },

    /**
     * Save favorites to localStorage
     */
    save() {
        Utils.storage.set(this.STORAGE_KEY, Array.from(this.favorites));
        this.notifyListeners();
    },

    /**
     * Add a channel to favorites
     */
    add(channelId) {
        if (!this.favorites.has(channelId)) {
            this.favorites.add(channelId);
            this.save();
            console.log(`Added to favorites: ${channelId}`);
            return true;
        }
        return false;
    },

    /**
     * Remove a channel from favorites
     */
    remove(channelId) {
        if (this.favorites.has(channelId)) {
            this.favorites.delete(channelId);
            this.save();
            console.log(`Removed from favorites: ${channelId}`);
            return true;
        }
        return false;
    },

    /**
     * Toggle favorite status
     */
    toggle(channelId) {
        if (this.favorites.has(channelId)) {
            this.remove(channelId);
            return false;
        } else {
            this.add(channelId);
            return true;
        }
    },

    /**
     * Check if channel is favorited
     */
    isFavorite(channelId) {
        return this.favorites.has(channelId);
    },

    /**
     * Get all favorite channel IDs
     */
    getAll() {
        return Array.from(this.favorites);
    },

    /**
     * Get count of favorites
     */
    count() {
        return this.favorites.size;
    },

    /**
     * Clear all favorites
     */
    clear() {
        this.favorites.clear();
        this.save();
    },

    /**
     * Add change listener
     */
    onChange(callback) {
        this.listeners.push(callback);
    },

    /**
     * Remove change listener
     */
    offChange(callback) {
        this.listeners = this.listeners.filter(l => l !== callback);
    },

    /**
     * Notify all listeners
     */
    notifyListeners() {
        this.listeners.forEach(cb => cb(this.getAll()));
    },

    /**
     * Create favorite toggle button
     */
    createToggleButton(channelId, size = 'small') {
        const isFav = this.isFavorite(channelId);

        const button = Utils.createElement('button', {
            className: `favorite-btn ${size} ${isFav ? 'active' : ''}`,
            title: isFav ? 'Remove from favorites' : 'Add to favorites',
            dataset: { channelId },
            onClick: (e) => {
                e.stopPropagation();
                const newState = this.toggle(channelId);
                button.classList.toggle('active', newState);
                button.title = newState ? 'Remove from favorites' : 'Add to favorites';
                button.innerHTML = newState ? '★' : '☆';
            }
        }, [isFav ? '★' : '☆']);

        return button;
    },

    /**
     * Export favorites as JSON
     */
    export() {
        return JSON.stringify({
            version: 1,
            exported: new Date().toISOString(),
            favorites: this.getAll()
        }, null, 2);
    },

    /**
     * Import favorites from JSON
     */
    import(jsonString) {
        try {
            const data = JSON.parse(jsonString);
            if (data.favorites && Array.isArray(data.favorites)) {
                data.favorites.forEach(id => this.favorites.add(id));
                this.save();
                return data.favorites.length;
            }
            return 0;
        } catch (e) {
            console.error('Failed to import favorites:', e);
            return -1;
        }
    },

    // ============ WATCH HISTORY ============

    HISTORY_KEY: 'iptv_history',
    MAX_HISTORY: 20,
    history: [],

    /**
     * Load watch history from localStorage
     */
    loadHistory() {
        this.history = Utils.storage.get(this.HISTORY_KEY, []);
    },

    /**
     * Add channel to watch history
     */
    addToHistory(channel) {
        if (!channel || !channel.id) return;

        // Load current history
        if (this.history.length === 0) {
            this.loadHistory();
        }

        // Remove if already in history
        this.history = this.history.filter(h => h.id !== channel.id);

        // Add to front
        this.history.unshift({
            id: channel.id,
            name: channel.name,
            country: channel.country,
            logo: channel.logos?.[0]?.url,
            watchedAt: Date.now()
        });

        // Trim to max
        if (this.history.length > this.MAX_HISTORY) {
            this.history = this.history.slice(0, this.MAX_HISTORY);
        }

        // Save and notify listeners
        Utils.storage.set(this.HISTORY_KEY, this.history);
        this.notifyHistoryListeners();
    },

    /**
     * Get watch history
     */
    getHistory() {
        if (this.history.length === 0) {
            this.loadHistory();
        }
        return this.history;
    },

    /**
     * Clear watch history
     */
    clearHistory() {
        this.history = [];
        Utils.storage.remove(this.HISTORY_KEY);
    },

    /**
     * Add history change listener
     * Called when watch history is modified
     */
    historyListeners: [],

    onHistoryChange(callback) {
        this.historyListeners.push(callback);
    },

    /**
     * Notify history listeners
     */
    notifyHistoryListeners() {
        this.historyListeners.forEach(cb => cb(this.getHistory()));
    }
};

// Make available globally
window.Favorites = Favorites;
