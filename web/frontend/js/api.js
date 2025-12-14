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
    async getChannels({ country, category, provider, search, playableOnly = true, includeEpg = true, page = 1, perPage = 50 } = {}) {
        const params = new URLSearchParams();
        if (country) params.set('country', country);
        if (category) params.set('category', category);
        if (provider) params.set('provider', provider);
        if (search) params.set('search', search);
        params.set('playable_only', playableOnly);
        if (includeEpg) params.set('include_epg', 'true');
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
    },

    /**
     * Get recent stream health updates (for polling)
     */
    async getHealthUpdates(since = 60) {
        return this.request(`/api/streams/health-updates?since=${since}`);
    },

    /**
     * Get stream health statistics
     */
    async getHealthStats() {
        return this.request('/api/streams/health-stats');
    },

    /**
     * Get health worker status
     */
    async getHealthWorkerStatus() {
        return this.request('/api/streams/health-worker');
    },

    // ==================== User Data Methods ====================

    /**
     * Get device ID for user identification
     */
    getDeviceId() {
        let deviceId = localStorage.getItem('iptv_device_id');
        if (!deviceId) {
            deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('iptv_device_id', deviceId);
        }
        return deviceId;
    },

    /**
     * Get user's favorites
     */
    async getFavorites() {
        return this.request('/api/user/favorites', {
            headers: { 'X-Device-Id': this.getDeviceId() }
        });
    },

    /**
     * Add channel to favorites
     */
    async addFavorite(channelId) {
        return this.request('/api/user/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Device-Id': this.getDeviceId()
            },
            body: JSON.stringify({ channel_id: channelId })
        });
    },

    /**
     * Remove channel from favorites
     */
    async removeFavorite(channelId) {
        return this.request(`/api/user/favorites/${channelId}`, {
            method: 'DELETE',
            headers: { 'X-Device-Id': this.getDeviceId() }
        });
    },

    /**
     * Check if channel is favorite
     */
    async isFavorite(channelId) {
        return this.request(`/api/user/favorites/${channelId}/check`, {
            headers: { 'X-Device-Id': this.getDeviceId() }
        });
    },

    /**
     * Record watch event
     */
    async recordWatch(channelId, streamId = null, durationSeconds = 0) {
        return this.request('/api/user/watch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Device-Id': this.getDeviceId()
            },
            body: JSON.stringify({
                channel_id: channelId,
                stream_id: streamId,
                duration_seconds: durationSeconds
            })
        });
    },

    /**
     * Get watch history
     */
    async getWatchHistory(limit = 20) {
        return this.request(`/api/user/history?limit=${limit}`, {
            headers: { 'X-Device-Id': this.getDeviceId() }
        });
    },

    /**
     * Get popular channels
     */
    async getPopularChannels(limit = 20) {
        return this.request(`/api/user/popular?limit=${limit}`);
    },

    /**
     * Export user data
     */
    async exportUserData() {
        return this.request('/api/user/export', {
            headers: { 'X-Device-Id': this.getDeviceId() }
        });
    },

    /**
     * Import user data
     */
    async importUserData(favorites) {
        return this.request('/api/user/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Device-Id': this.getDeviceId()
            },
            body: JSON.stringify({ favorites })
        });
    }
};

// Make available globally
window.API = API;
