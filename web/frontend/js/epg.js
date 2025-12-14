/**
 * IPTV Web - EPG (Electronic Program Guide)
 */

const EPG = {
    // State
    currentChannels: [],
    timeOffset: 0,  // Hours from now

    // DOM elements
    elements: {},

    /**
     * Initialize EPG
     */
    init() {
        this.elements = {
            panel: document.getElementById('epg-panel'),
            toggle: document.getElementById('epg-toggle'),
            close: document.getElementById('epg-close'),
            grid: document.getElementById('epg-grid'),
            timeDisplay: document.getElementById('epg-time-display'),
            prevBtn: document.getElementById('epg-prev'),
            nextBtn: document.getElementById('epg-next')
        };

        this.bindEvents();
        console.log('EPG initialized');
    },

    /**
     * Bind events
     */
    bindEvents() {
        // Toggle panel
        this.elements.toggle.addEventListener('click', () => this.toggle());
        this.elements.close.addEventListener('click', () => this.close());

        // Time navigation
        this.elements.prevBtn.addEventListener('click', () => this.navigateTime(-3));
        this.elements.nextBtn.addEventListener('click', () => this.navigateTime(3));

        // Keyboard
        document.addEventListener('keydown', (e) => {
            if (e.key === 'g' && !e.ctrlKey && !e.metaKey) {
                if (!Player.isOpen() && document.activeElement.tagName !== 'INPUT') {
                    this.toggle();
                }
            }
        });
    },

    /**
     * Toggle EPG panel
     */
    toggle() {
        if (this.isOpen()) {
            this.close();
        } else {
            this.open();
        }
    },

    /**
     * Open EPG panel
     */
    async open() {
        Utils.show(this.elements.panel);
        this.elements.panel.classList.remove('hidden');

        // Load EPG for currently visible channels
        await this.loadEPGForVisibleChannels();
    },

    /**
     * Close EPG panel
     */
    close() {
        this.elements.panel.classList.add('hidden');
    },

    /**
     * Check if EPG is open
     */
    isOpen() {
        return !this.elements.panel.classList.contains('hidden');
    },

    /**
     * Navigate time
     */
    navigateTime(hoursOffset) {
        this.timeOffset += hoursOffset;

        // Limit to -24 to +24 hours
        this.timeOffset = Math.max(-24, Math.min(24, this.timeOffset));

        this.updateTimeDisplay();
        this.loadEPGForVisibleChannels();
    },

    /**
     * Update time display
     */
    updateTimeDisplay() {
        if (this.timeOffset === 0) {
            this.elements.timeDisplay.textContent = 'Now';
        } else if (this.timeOffset > 0) {
            this.elements.timeDisplay.textContent = `+${this.timeOffset}h`;
        } else {
            this.elements.timeDisplay.textContent = `${this.timeOffset}h`;
        }
    },

    /**
     * Load EPG for visible channels
     */
    async loadEPGForVisibleChannels() {
        // Get first 10 channels from current view
        const channelIds = Channels.channels.slice(0, 10).map(c => c.id);

        if (channelIds.length === 0) {
            this.elements.grid.innerHTML = '<p class="epg-message">No channels to show. Browse channels first.</p>';
            return;
        }

        this.elements.grid.innerHTML = '<div class="loading-container"><div class="loading-spinner"></div></div>';

        try {
            // Calculate start time
            const startTime = new Date();
            startTime.setHours(startTime.getHours() + this.timeOffset);

            const data = await API.getEPGTimeline(channelIds, {
                start: startTime.toISOString(),
                hours: 6
            });

            this.renderEPG(data);
        } catch (error) {
            console.error('Failed to load EPG:', error);
            this.elements.grid.innerHTML = `
                <div class="loading-container error-state">
                    <p class="error-icon">📺</p>
                    <p>Failed to load program guide.</p>
                    <p class="error-detail">${Utils.escapeHtml(error.message || 'Network error')}</p>
                    <button class="retry-btn" onclick="EPG.loadEPGForVisibleChannels()">Retry</button>
                </div>
            `;
        }
    },

    /**
     * Render EPG grid
     */
    renderEPG(data) {
        this.elements.grid.innerHTML = '';

        if (!data.channels || data.channels.length === 0) {
            this.elements.grid.innerHTML = '<p class="epg-message">No program data available.</p>';
            return;
        }

        data.channels.forEach(channel => {
            const row = this.createChannelRow(channel);
            this.elements.grid.appendChild(row);
        });
    },

    /**
     * Create EPG channel row
     */
    createChannelRow(channelData) {
        // Find channel info from Channels module
        const channelInfo = Channels.channels.find(c => c.id === channelData.channel_id);
        const logo = channelInfo?.logos?.[0]?.url;

        const row = Utils.createElement('div', { className: 'epg-channel-row' }, [
            Utils.createElement('div', { className: 'epg-channel-info' }, [
                logo ?
                    Utils.createElement('img', {
                        className: 'epg-channel-logo',
                        src: logo,
                        alt: channelData.channel_name
                    }) :
                    Utils.createElement('div', {
                        className: 'epg-channel-logo',
                        style: 'background: var(--bg-tertiary); display: flex; align-items: center; justify-content: center;'
                    }, ['📺']),
                Utils.createElement('span', { className: 'epg-channel-name' }, [
                    channelData.channel_name || channelData.channel_id
                ])
            ]),
            Utils.createElement('div', { className: 'epg-programs' },
                this.createProgramBlocks(channelData.programs, channelData.channel_id)
            )
        ]);

        return row;
    },

    /**
     * Create program blocks for timeline
     */
    createProgramBlocks(programs, channelId) {
        if (!programs || programs.length === 0) {
            return [
                Utils.createElement('div', { className: 'epg-program' }, [
                    Utils.createElement('span', { className: 'epg-program-title' }, ['No program data']),
                    Utils.createElement('span', { className: 'epg-program-time' }, ['—'])
                ])
            ];
        }

        const now = new Date();

        return programs.map(program => {
            const startTime = new Date(program.start);
            const endTime = new Date(program.stop);
            const isNow = startTime <= now && now <= endTime;

            // Calculate progress for current program
            let progress = 0;
            if (isNow) {
                const total = endTime - startTime;
                const elapsed = now - startTime;
                progress = Math.min(100, (elapsed / total) * 100);
            }

            const block = Utils.createElement('div', {
                className: `epg-program ${isNow ? 'now' : ''}`,
                onClick: () => this.onProgramClick(channelId, program)
            }, [
                Utils.createElement('div', { className: 'epg-program-title' }, [program.title]),
                Utils.createElement('div', { className: 'epg-program-time' }, [
                    `${Utils.formatTime(startTime)} - ${Utils.formatTime(endTime)}`
                ]),
                isNow ? Utils.createElement('div', { className: 'epg-progress' }, [
                    Utils.createElement('div', {
                        className: 'epg-progress-bar',
                        style: `width: ${progress}%`
                    })
                ]) : null
            ].filter(Boolean));

            return block;
        });
    },

    /**
     * Handle program click
     */
    async onProgramClick(channelId, program) {
        // Open the channel in player
        try {
            const channel = await API.getChannel(channelId);
            Player.open(channel);

            // Update program display
            if (Player.elements.program) {
                Player.elements.program.textContent = program.title;
            }
        } catch (error) {
            console.error('Failed to open channel:', error);
        }
    }
};

// Make available globally
window.EPG = EPG;
