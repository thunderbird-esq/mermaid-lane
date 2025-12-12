/**
 * IPTV Web - API Client
 * Handles all communication with the backend API
 */

const API = {
    baseUrl: '',  // Same origin

    /**
     * Make an API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    /**
     * Get channels with filtering and pagination
     */
    async getChannels({ country, category, search, page = 1, perPage = 50 } = {}) {
        const params = new URLSearchParams();
        if (country) params.set('country', country);
        if (category) params.set('category', category);
        if (search) params.set('search', search);
        params.set('page', page);
        params.set('per_page', perPage);

        return this.request(`/api/channels?${params}`);
    },

    /**
     * Get single channel with streams and logos
     */
    async getChannel(channelId) {
        return this.request(`/api/channels/${encodeURIComponent(channelId)}`);
    },

    /**
     * Get all categories
     */
    async getCategories() {
        return this.request('/api/categories');
    },

    /**
     * Get all countries
     */
    async getCountries() {
        return this.request('/api/countries');
    },

    /**
     * Get languages
     */
    async getLanguages() {
        return this.request('/api/languages');
    },

    /**
     * Get regions
     */
    async getRegions() {
        return this.request('/api/regions');
    },

    /**
     * Get stream providers
     */
    async getProviders() {
        return this.request('/api/providers');
    },

    /**
     * Check stream health
     */
    async checkStreamStatus(streamId) {
        return this.request(`/api/streams/${streamId}/status`);
    },

    /**
     * Get stream manifest URL (for player)
     */
    getStreamUrl(streamId) {
        return `${this.baseUrl}/api/streams/${streamId}/play.m3u8`;
    },

    /**
     * Get EPG for a channel
     */
    async getChannelEPG(channelId, hours = 24) {
        return this.request(`/api/epg/${encodeURIComponent(channelId)}?hours=${hours}`);
    },

    /**
     * Get currently playing programs
     */
    async getNowPlaying({ country, category, limit = 50 } = {}) {
        const params = new URLSearchParams();
        if (country) params.set('country', country);
        if (category) params.set('category', category);
        params.set('limit', limit);

        return this.request(`/api/epg/now?${params}`);
    },

    /**
     * Get EPG timeline for multiple channels
     */
    async getEPGTimeline(channelIds, { start, hours = 6 } = {}) {
        const params = new URLSearchParams();
        params.set('channels', channelIds.join(','));
        if (start) params.set('start', start);
        params.set('hours', hours);

        return this.request(`/api/epg/timeline?${params}`);
    },

    /**
     * Search EPG programs
     */
    async searchEPG(query, limit = 50) {
        return this.request(`/api/epg/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    },

    /**
     * Get API stats
     */
    async getStats() {
        return this.request('/api/stats');
    },

    /**
     * Trigger data sync (admin)
     */
    async triggerSync() {
        return this.request('/api/sync', { method: 'POST' });
    }
};

// Make available globally
window.API = API;
