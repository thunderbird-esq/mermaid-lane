/**
 * IPTV Web - Video Player with Video.js
 */

const Player = {
    // State
    player: null,
    currentChannel: null,
    currentStream: null,

    // DOM elements
    elements: {},

    /**
     * Initialize the player
     */
    init() {
        // Initialize Video.js with native controls enabled
        this.player = videojs('video-player', {
            controls: true,
            autoplay: false,
            preload: 'auto',
            fill: true,
            html5: {
                vhs: {
                    overrideNative: true
                },
                nativeAudioTracks: false,
                nativeVideoTracks: false
            }
        });

        // Initialize plugins
        // Initialize plugins
        this.player.ready(() => {
            if (this.player.httpSourceSelector) {
                this.player.httpSourceSelector();
            }
        });

        this.elements = {
            modal: document.getElementById('player-modal'),
            close: document.getElementById('player-close'),
            favorite: document.getElementById('player-favorite'),
            logo: document.getElementById('player-logo'),
            title: document.getElementById('player-title'),
            program: document.getElementById('player-program'),
            loading: document.getElementById('player-loading'),
            error: document.getElementById('player-error'),
            retryBtn: document.getElementById('retry-btn'),
            streamList: document.getElementById('stream-list'),
            // Custom controls wrapper (to hide it)
            customControls: document.querySelector('.player-controls')
        };

        this.bindEvents();
        console.log('Player initialized (Video.js + Plugins)');
    },

    /**
     * Bind control events
     */
    bindEvents() {
        // Close button (Modal UI)
        this.elements.close.addEventListener('click', () => this.close());

        // Click outside to close
        this.elements.modal.addEventListener('click', (e) => {
            if (e.target === this.elements.modal) {
                this.close();
            }
        });

        // Retry button
        this.elements.retryBtn.addEventListener('click', () => this.retry());

        // Video.js events
        this.player.ready(() => {
            this.player.on('play', () => this.onPlay());
            this.player.on('pause', () => this.onPause());
            this.player.on('waiting', () => this.showLoading());
            this.player.on('playing', () => this.hideLoading());
            this.player.on('error', (e) => this.onError(e));
        });

        // Keyboard shortcuts - Delegate to Video.js where possible, but handle Escape
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen()) return;
            if (e.key === 'Escape') this.close();
        });
    },

    /**
     * Open player with channel
     */
    async open(channel) {
        this.currentChannel = channel;

        // Track in watch history
        Favorites.addToHistory(channel);

        // Update UI info
        this.elements.title.textContent = channel.name;
        this.elements.program.textContent = channel.streams?.length ?
            `${channel.streams.length} stream${channel.streams.length > 1 ? 's' : ''} available` :
            'Loading...';

        // Set logo
        const logo = channel.logos?.[0]?.url;
        if (logo) {
            this.elements.logo.src = logo;
            this.elements.logo.style.display = 'block';
        } else {
            this.elements.logo.style.display = 'none';
        }

        // Add favorite button
        if (this.elements.favorite) {
            this.elements.favorite.innerHTML = '';
            this.elements.favorite.appendChild(
                Favorites.createToggleButton(channel.id, 'large')
            );
        }

        // Show modal
        Utils.show(this.elements.modal);
        this.showLoading();

        // Populate stream list (custom UI below player)
        this.renderStreamList(channel.streams || []);

        // Hide custom controls if they exist (we use native now)
        if (this.elements.customControls) {
            this.elements.customControls.style.display = 'none';
        }

        // Play first available stream
        if (channel.streams && channel.streams.length > 0) {
            await this.playStream(channel.streams[0]);
        } else {
            this.showError('No streams available for this channel');
        }
    },

    /**
     * Render stream selection list
     */
    renderStreamList(streams) {
        this.elements.streamList.innerHTML = '';

        streams.forEach((stream, index) => {
            const button = Utils.createElement('button', {
                className: `stream-option ${index === 0 ? 'active' : ''}`,
                dataset: { streamId: stream.stream_id },
                onClick: () => this.playStream(stream)
            }, [
                stream.title || `Stream ${index + 1}`,
                stream.quality ? Utils.createElement('span', { className: 'stream-quality' }, [stream.quality]) : null
            ].filter(Boolean));

            this.elements.streamList.appendChild(button);
        });
    },

    /**
     * Play a specific stream
     */
    async playStream(stream) {
        this.currentStream = stream;
        this.showLoading();

        // Update active stream in list
        this.elements.streamList.querySelectorAll('.stream-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.streamId === stream.stream_id);
        });

        const streamUrl = API.getStreamUrl(stream.stream_id);

        // Determine type based on URL (optional explicit type setting)
        // Video.js usually detects automatically, but we can help it.
        // Backend returns .m3u8 extension for HLS proxies.
        let type = 'application/x-mpegURL';
        if (streamUrl.includes('.mpd')) {
            type = 'application/dash+xml';
        }

        // Load stream in Video.js
        this.player.src({
            src: streamUrl,
            type: type
        });

        try {
            await this.player.play();
        } catch (e) {
            console.warn('Playback failed to start automatically', e);
        }
    },

    /**
     * Event handlers
     */
    onPlay() {
        this.hideLoading();
    },

    onPause() {
        // Optional: show overlay?
    },

    onError(e) {
        console.error('Video error:', this.player.error());
        this.showError('Playback error');
    },

    /**
     * Show loading overlay
     */
    showLoading() {
        Utils.show(this.elements.loading);
        Utils.hide(this.elements.error);
    },

    /**
     * Hide loading overlay
     */
    hideLoading() {
        Utils.hide(this.elements.loading);
    },

    /**
     * Show error overlay
     */
    showError(message) {
        Utils.hide(this.elements.loading);
        Utils.show(this.elements.error);
        const msgEl = this.elements.error.querySelector('.error-message');
        if (msgEl) msgEl.textContent = message;
    },

    /**
     * Retry playback
     */
    retry() {
        if (this.currentStream) {
            this.playStream(this.currentStream);
        }
    },

    /**
     * Check if player is open
     */
    isOpen() {
        return !this.elements.modal.classList.contains('hidden');
    },

    /**
     * Close the player
     */
    close() {
        this.player.pause();
        this.player.src(''); // Unload

        // Hide modal
        Utils.hide(this.elements.modal);
        this.elements.modal.classList.remove('fullscreen');

        // Exit fullscreen if active
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }

        this.currentChannel = null;
        this.currentStream = null;
    }
};

// Make available globally
window.Player = Player;
