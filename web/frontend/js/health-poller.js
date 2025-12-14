/**
 * IPTV Web - Health Polling
 * Polls the backend for stream health updates and updates UI badges in real-time.
 */

const HealthPoller = {
    // Configuration
    pollInterval: 30000,  // 30 seconds
    enabled: true,
    _intervalId: null,
    _lastPoll: null,

    /**
     * Start polling for health updates
     */
    start() {
        if (this._intervalId) return;

        console.log('🏥 Health poller started');
        this._intervalId = setInterval(() => this.poll(), this.pollInterval);

        // Initial poll after short delay
        setTimeout(() => this.poll(), 5000);
    },

    /**
     * Stop polling
     */
    stop() {
        if (this._intervalId) {
            clearInterval(this._intervalId);
            this._intervalId = null;
            console.log('Health poller stopped');
        }
    },

    /**
     * Poll for updates
     */
    async poll() {
        if (!this.enabled) return;

        try {
            const data = await API.getHealthUpdates(60);

            if (data.updates && data.updates.length > 0) {
                console.log(`📡 ${data.updates.length} health updates received`);
                this.applyUpdates(data.updates);
            }

            this._lastPoll = Date.now();
        } catch (error) {
            console.warn('Health poll failed:', error.message);
        }
    },

    /**
     * Apply health updates to visible channel cards
     */
    applyUpdates(updates) {
        // Build lookup by channel_id
        const updatesByChannel = {};
        updates.forEach(u => {
            if (!updatesByChannel[u.channel_id]) {
                updatesByChannel[u.channel_id] = [];
            }
            updatesByChannel[u.channel_id].push(u);
        });

        // Update visible channel cards
        document.querySelectorAll('.channel-card').forEach(card => {
            const channelId = card.dataset.channelId;
            if (!channelId || !updatesByChannel[channelId]) return;

            const channelUpdates = updatesByChannel[channelId];
            // Use best status among streams for this channel
            const bestStatus = this.getBestStatus(channelUpdates);

            this.updateCardBadge(card, bestStatus);
        });
    },

    /**
     * Get the best health status from a list of updates
     */
    getBestStatus(updates) {
        const priority = { 'working': 1, 'warning': 2, 'unknown': 3, 'failed': 4 };

        let best = null;
        let bestPriority = 999;

        updates.forEach(u => {
            const p = priority[u.health_status] || 999;
            if (p < bestPriority) {
                bestPriority = p;
                best = u.health_status;
            }
        });

        return best;
    },

    /**
     * Update or add badge to a channel card
     */
    updateCardBadge(card, status) {
        // Remove existing indicator
        const existing = card.querySelector('.stream-health-indicator');
        if (existing) existing.remove();

        // Don't show badge for working streams
        if (status === 'working') return;

        // Create new badge
        const badge = document.createElement('div');
        badge.className = 'stream-health-indicator';

        switch (status) {
            case 'warning':
                badge.classList.add('warning');
                badge.textContent = '⚡';
                badge.title = 'Some streams may have issues';
                break;
            case 'failed':
                badge.classList.add('geo-blocked');
                badge.textContent = '❌';
                badge.title = 'Stream currently unavailable';
                break;
            default:
                badge.classList.add('unknown');
                badge.textContent = '❓';
                badge.title = 'Stream status unknown';
        }

        card.insertBefore(badge, card.firstChild);
    },

    /**
     * Get health stats summary (for status bar)
     */
    async getStats() {
        try {
            return await API.getHealthStats();
        } catch (error) {
            console.error('Failed to get health stats:', error);
            return null;
        }
    }
};

// Auto-start when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Start polling after a delay to let initial load complete
    setTimeout(() => {
        HealthPoller.start();
    }, 10000);
});

// Make available globally
window.HealthPoller = HealthPoller;
