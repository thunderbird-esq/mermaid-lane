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

        // Initialize plugins when player is ready
        this.player.ready(() => {
            // NOTE: httpSourceSelector is disabled due to incompatibility with Video.js 8
            // It causes: "TypeError: Class constructor Qi cannot be invoked without 'new'"
            // TODO: Find a compatible quality selector plugin for Video.js 8
            console.log('[Player] Ready - quality selector disabled (Video.js 8 compatibility)');
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
        console.log('[Player] playStream called:', stream.title, stream.url);
        this.currentStream = stream;
        this.showLoading();

        // Clear any existing timeout
        if (this.loadingTimeout) {
            clearTimeout(this.loadingTimeout);
            this.loadingTimeout = null;
        }

        // Check for YouTube URL early to set appropriate timeout
        const isYouTube = stream.url.includes('youtube.com') || stream.url.includes('youtu.be');

        // Set loading timeout (30s for YouTube, 15s for HLS)
        // YouTube takes longer due to iframe initialization
        const timeoutMs = isYouTube ? 30000 : 15000;
        this.loadingTimeout = setTimeout(() => {
            console.error(`[Player] Loading timeout after ${timeoutMs / 1000} seconds`);
            this.showError('Stream took too long to load. Try another stream.');
        }, timeoutMs);

        // Update active stream in list
        this.elements.streamList.querySelectorAll('.stream-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.streamId === stream.stream_id);
        });

        const streamUrl = API.getStreamUrl(stream.stream_id);
        console.log('[Player] Stream URL:', streamUrl);

        // Define type variable
        let type = 'application/x-mpegURL';

        // isYouTube already defined above for timeout logic
        console.log('[Player] Is YouTube:', isYouTube);

        if (isYouTube) {
            type = 'video/youtube';
            console.log('[Player] Setting YouTube source:', stream.url);
            // Use original URL for YouTube, not proxy
            this.player.src({
                src: stream.url,
                type: type
            });
        } else {
            // Standard HLS/DASH proxy
            if (streamUrl.includes('.mpd')) {
                type = 'application/dash+xml';
            }
            console.log('[Player] Setting HLS source:', streamUrl, 'type:', type);

            // Load stream in Video.js
            this.player.src({
                src: streamUrl,
                type: type
            });
        }

        // Set up one-time event listeners for this playback attempt
        const clearTimeoutOnSuccess = () => {
            if (this.loadingTimeout) {
                clearTimeout(this.loadingTimeout);
                this.loadingTimeout = null;
            }
            console.log('[Player] Playback started successfully');
            this.hideLoading();
        };

        const clearTimeoutOnError = () => {
            if (this.loadingTimeout) {
                clearTimeout(this.loadingTimeout);
                this.loadingTimeout = null;
            }
        };

        // Listen to both 'playing' and 'play' events
        // YouTube tech may not fire 'playing' but does fire 'play'
        this.player.one('playing', clearTimeoutOnSuccess);
        this.player.one('play', clearTimeoutOnSuccess);
        this.player.one('error', clearTimeoutOnError);

        try {
            console.log('[Player] Calling player.play()...');
            await this.player.play();
            console.log('[Player] play() promise resolved');
        } catch (e) {
            console.warn('[Player] Playback failed to start automatically:', e.message);
            // Don't show error yet - browser autoplay policies may prevent this
            // The 'playing' event will still fire if user clicks play manually
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
        // Clear any pending timeout
        if (this.loadingTimeout) {
            clearTimeout(this.loadingTimeout);
            this.loadingTimeout = null;
        }

        // Track if we're on YouTube tech (doesn't support full reset)
        const isYouTubeTech = this.currentStream &&
            (this.currentStream.url.includes('youtube.com') ||
                this.currentStream.url.includes('youtu.be'));

        try {
            this.player.pause();

            // YouTube tech doesn't support reset() - only pause
            // reset() causes: "defaultPlaybackRate method not defined for Youtube"
            if (!isYouTubeTech) {
                this.player.reset();
            }
        } catch (e) {
            // Silently ignore - these are expected for some techs
            console.debug('[Player] Close cleanup:', e.message);
        }

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
