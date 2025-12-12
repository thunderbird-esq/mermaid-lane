/**
 * IPTV Web - Video Player with HLS.js
 */

const Player = {
    // State
    hls: null,
    video: null,
    currentChannel: null,
    currentStream: null,
    isPlaying: false,

    // DOM elements
    elements: {},

    /**
     * Initialize the player
     */
    init() {
        this.video = document.getElementById('video-player');

        this.elements = {
            modal: document.getElementById('player-modal'),
            close: document.getElementById('player-close'),
            favorite: document.getElementById('player-favorite'),
            logo: document.getElementById('player-logo'),
            title: document.getElementById('player-title'),
            program: document.getElementById('player-program'),
            playPause: document.getElementById('play-pause'),
            muteBtn: document.getElementById('mute-btn'),
            volumeSlider: document.getElementById('volume-slider'),
            qualitySelect: document.getElementById('quality-select'),
            pipBtn: document.getElementById('pip-btn'),
            fullscreenBtn: document.getElementById('fullscreen-btn'),
            loading: document.getElementById('player-loading'),
            error: document.getElementById('player-error'),
            retryBtn: document.getElementById('retry-btn'),
            streamList: document.getElementById('stream-list')
        };

        this.bindEvents();
        console.log('Player initialized');
    },

    /**
     * Bind control events
     */
    bindEvents() {
        // Close button
        this.elements.close.addEventListener('click', () => this.close());

        // Click outside to close
        this.elements.modal.addEventListener('click', (e) => {
            if (e.target === this.elements.modal) {
                this.close();
            }
        });

        // Play/Pause
        this.elements.playPause.addEventListener('click', () => this.togglePlay());
        this.video.addEventListener('click', () => this.togglePlay());

        // Volume
        this.elements.muteBtn.addEventListener('click', () => this.toggleMute());
        this.elements.volumeSlider.addEventListener('input', (e) => {
            this.video.volume = parseFloat(e.target.value);
            this.video.muted = false;
            this.updateVolumeIcon();
        });

        // Quality
        this.elements.qualitySelect.addEventListener('change', (e) => {
            this.setQuality(e.target.value);
        });

        // Picture in Picture
        this.elements.pipBtn.addEventListener('click', () => this.togglePiP());

        // Fullscreen
        this.elements.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());

        // Retry
        this.elements.retryBtn.addEventListener('click', () => this.retry());

        // Video events
        this.video.addEventListener('play', () => this.onPlay());
        this.video.addEventListener('pause', () => this.onPause());
        this.video.addEventListener('waiting', () => this.showLoading());
        this.video.addEventListener('canplay', () => this.hideLoading());
        this.video.addEventListener('error', (e) => this.onError(e));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    },

    /**
     * Open player with channel
     */
    async open(channel) {
        this.currentChannel = channel;

        // Track in watch history
        Favorites.addToHistory(channel);

        // Update UI
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

        // Populate stream list
        this.renderStreamList(channel.streams || []);

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

        // Clean up existing HLS instance
        if (this.hls) {
            this.hls.destroy();
            this.hls = null;
        }

        // Check if HLS.js is supported
        if (Hls.isSupported()) {
            this.hls = new Hls({
                maxBufferLength: 30,
                maxMaxBufferLength: 60,
                maxBufferSize: 60 * 1000 * 1000,
                enableWorker: true
            });

            this.hls.loadSource(streamUrl);
            this.hls.attachMedia(this.video);

            this.hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
                this.updateQualityOptions(data.levels);
                this.video.play().catch(() => { });
            });

            this.hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            console.error('Network error', data);
                            this.hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            console.error('Media error', data);
                            this.hls.recoverMediaError();
                            break;
                        default:
                            this.showError('Stream playback failed');
                            break;
                    }
                }
            });
        } else if (this.video.canPlayType('application/vnd.apple.mpegurl')) {
            // Native HLS support (Safari)
            this.video.src = streamUrl;
            this.video.addEventListener('loadedmetadata', () => {
                this.video.play().catch(() => { });
            });
        } else {
            this.showError('HLS not supported in this browser');
        }
    },

    /**
     * Update quality selector options
     */
    updateQualityOptions(levels) {
        this.elements.qualitySelect.innerHTML = '<option value="auto">Auto</option>';

        levels.forEach((level, index) => {
            const height = level.height || 'Unknown';
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `${height}p`;
            this.elements.qualitySelect.appendChild(option);
        });
    },

    /**
     * Set video quality
     */
    setQuality(value) {
        if (!this.hls) return;

        if (value === 'auto') {
            this.hls.currentLevel = -1; // Auto
        } else {
            this.hls.currentLevel = parseInt(value);
        }
    },

    /**
     * Toggle play/pause
     */
    togglePlay() {
        if (this.video.paused) {
            this.video.play().catch(() => { });
        } else {
            this.video.pause();
        }
    },

    /**
     * Toggle mute
     */
    toggleMute() {
        this.video.muted = !this.video.muted;
        this.updateVolumeIcon();
    },

    /**
     * Update volume icon
     */
    updateVolumeIcon() {
        if (this.video.muted || this.video.volume === 0) {
            this.elements.muteBtn.textContent = '🔇';
        } else if (this.video.volume < 0.5) {
            this.elements.muteBtn.textContent = '🔉';
        } else {
            this.elements.muteBtn.textContent = '🔊';
        }
    },

    /**
     * Toggle Picture in Picture
     */
    async togglePiP() {
        try {
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
            } else if (document.pictureInPictureEnabled) {
                await this.video.requestPictureInPicture();
            }
        } catch (error) {
            console.error('PiP error:', error);
        }
    },

    /**
     * Toggle fullscreen
     */
    toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen();
            this.elements.modal.classList.remove('fullscreen');
        } else {
            this.elements.modal.requestFullscreen();
            this.elements.modal.classList.add('fullscreen');
        }
    },

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboard(e) {
        if (!this.isOpen()) return;

        switch (e.key) {
            case ' ':
            case 'k':
                e.preventDefault();
                this.togglePlay();
                break;
            case 'Escape':
                this.close();
                break;
            case 'f':
                this.toggleFullscreen();
                break;
            case 'm':
                this.toggleMute();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.video.volume = Math.min(1, this.video.volume + 0.1);
                this.elements.volumeSlider.value = this.video.volume;
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.video.volume = Math.max(0, this.video.volume - 0.1);
                this.elements.volumeSlider.value = this.video.volume;
                break;
        }
    },

    /**
     * Event handlers
     */
    onPlay() {
        this.isPlaying = true;
        this.elements.playPause.textContent = '⏸';
        this.hideLoading();
    },

    onPause() {
        this.isPlaying = false;
        this.elements.playPause.textContent = '▶';
    },

    onError(e) {
        console.error('Video error:', e);
        this.showError('Stream playback error');
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
        this.elements.error.querySelector('.error-message').textContent = message;
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
        // Stop playback
        this.video.pause();
        this.video.src = '';

        // Clean up HLS
        if (this.hls) {
            this.hls.destroy();
            this.hls = null;
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
