/**
 * IPTV Web - Channel Browser
 */

const Channels = {
    // State
    channels: [],
    countries: [],
    categories: [],
    currentPage: 1,
    hasMore: true,
    loading: false,

    // Filters
    filters: {
        country: null,
        category: null,
        search: ''
    },

    // DOM elements
    elements: {},

    /**
     * Initialize channel browser
     */
    async init() {
        this.elements = {
            grid: document.getElementById('channel-grid'),
            countryList: document.getElementById('country-list'),
            categoryList: document.getElementById('category-list'),
            contentTitle: document.getElementById('content-title'),
            channelCount: document.getElementById('channel-count'),
            loadMore: document.getElementById('load-more'),
            viewToggle: document.getElementById('view-toggle'),
            search: document.getElementById('global-search')
        };

        this.bindEvents();

        // Load initial data
        await Promise.all([
            this.loadCountries(),
            this.loadCategories(),
            this.loadChannels()
        ]);

        console.log('Channels initialized');
    },

    /**
     * Bind events
     */
    bindEvents() {
        // Search
        this.elements.search.addEventListener('input', Utils.debounce((e) => {
            this.filters.search = e.target.value.trim();
            this.resetAndReload();
        }, 300));

        // Load more
        this.elements.loadMore.querySelector('button').addEventListener('click', () => {
            this.loadMore();
        });

        // View toggle
        this.elements.viewToggle.addEventListener('click', () => {
            this.elements.grid.classList.toggle('list-view');
        });

        // Infinite scroll
        window.addEventListener('scroll', Utils.throttle(() => {
            if (this.shouldLoadMore()) {
                this.loadMore();
            }
        }, 200));
    },

    /**
     * Load countries
     */
    async loadCountries() {
        try {
            const data = await API.getCountries();
            this.countries = data.countries || [];
            this.renderCountries();
        } catch (error) {
            console.error('Failed to load countries:', error);
        }
    },

    /**
     * Render country list
     */
    renderCountries() {
        this.elements.countryList.innerHTML = '';

        // Add "All Countries" option
        const allItem = this.createFilterItem(null, '🌍', 'All Countries',
            this.countries.reduce((sum, c) => sum + (c.channel_count || 0), 0));
        this.elements.countryList.appendChild(allItem);

        // Sort by channel count and filter out empty
        const sortedCountries = this.countries
            .filter(c => c.channel_count > 0)
            .sort((a, b) => b.channel_count - a.channel_count);

        sortedCountries.forEach(country => {
            const item = this.createFilterItem(
                country.code,
                country.flag || '🏳️',
                country.name,
                country.channel_count,
                'country'
            );
            this.elements.countryList.appendChild(item);
        });
    },

    /**
     * Load categories
     */
    async loadCategories() {
        try {
            const data = await API.getCategories();
            this.categories = data.categories || [];
            this.renderCategories();
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    },

    /**
     * Render category list
     */
    renderCategories() {
        this.elements.categoryList.innerHTML = '';

        // Add "All Categories" option
        const allItem = this.createFilterItem(null, '📺', 'All Categories', null, 'category');
        allItem.classList.add('active');
        this.elements.categoryList.appendChild(allItem);

        // Sort by channel count
        const sortedCategories = [...this.categories]
            .filter(c => c.channel_count > 0)
            .sort((a, b) => b.channel_count - a.channel_count);

        sortedCategories.forEach(category => {
            const item = this.createFilterItem(
                category.id,
                Utils.getCategoryIcon(category.id),
                category.name,
                category.channel_count,
                'category'
            );
            this.elements.categoryList.appendChild(item);
        });
    },

    /**
     * Create filter item element
     */
    createFilterItem(value, icon, name, count, type = 'country') {
        const item = Utils.createElement('div', {
            className: `filter-item ${value === null && type === 'country' ? 'active' : ''}`,
            dataset: { value: value || '', type },
            onClick: () => this.selectFilter(type, value)
        }, [
            Utils.createElement('span', { className: 'filter-icon' }, [icon]),
            Utils.createElement('span', { className: 'filter-name' }, [name]),
            count !== null ? Utils.createElement('span', { className: 'filter-count' }, [String(count)]) : null
        ].filter(Boolean));

        return item;
    },

    /**
     * Select a filter
     */
    selectFilter(type, value) {
        this.filters[type] = value;

        // Update active state
        const list = type === 'country' ? this.elements.countryList : this.elements.categoryList;
        list.querySelectorAll('.filter-item').forEach(item => {
            const itemValue = item.dataset.value || null;
            item.classList.toggle('active', itemValue === (value || ''));
        });

        // Update title
        this.updateTitle();

        // Reload channels
        this.resetAndReload();
    },

    /**
     * Update content title based on filters
     */
    updateTitle() {
        let title = 'All Channels';

        if (this.filters.country) {
            const country = this.countries.find(c => c.code === this.filters.country);
            if (country) {
                title = `${country.flag} ${country.name} Channels`;
            }
        }

        if (this.filters.category) {
            const category = this.categories.find(c => c.id === this.filters.category);
            if (category) {
                title = this.filters.country ?
                    `${title} - ${category.name}` :
                    `${category.name} Channels`;
            }
        }

        if (this.filters.search) {
            title = `Search: "${this.filters.search}"`;
        }

        this.elements.contentTitle.textContent = title;
    },

    /**
     * Reset and reload channels
     */
    resetAndReload() {
        this.channels = [];
        this.currentPage = 1;
        this.hasMore = true;
        this.elements.grid.innerHTML = '';
        this.loadChannels();
    },

    /**
     * Load channels
     */
    async loadChannels() {
        if (this.loading) return;
        this.loading = true;

        // Show loading state
        if (this.currentPage === 1) {
            this.elements.grid.innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <p>Loading channels...</p>
                </div>
            `;
        }

        try {
            const data = await API.getChannels({
                country: this.filters.country,
                category: this.filters.category,
                search: this.filters.search || undefined,
                page: this.currentPage
            });

            const newChannels = data.channels || [];
            this.channels.push(...newChannels);
            this.hasMore = data.has_more;

            // Clear loading state on first page
            if (this.currentPage === 1) {
                this.elements.grid.innerHTML = '';
            }

            // Render new channels
            this.renderChannels(newChannels);

            // Update count
            this.elements.channelCount.textContent = `${data.total.toLocaleString()} channels`;

            // Show/hide load more
            this.hasMore ? Utils.show(this.elements.loadMore) : Utils.hide(this.elements.loadMore);

        } catch (error) {
            console.error('Failed to load channels:', error);
            if (this.currentPage === 1) {
                this.elements.grid.innerHTML = `
                    <div class="loading-container">
                        <p>Failed to load channels. Please try again.</p>
                    </div>
                `;
            }
        } finally {
            this.loading = false;
        }
    },

    /**
     * Render channel cards
     */
    renderChannels(channels) {
        channels.forEach(channel => {
            const card = this.createChannelCard(channel);
            this.elements.grid.appendChild(card);
        });
    },

    /**
     * Create channel card element
     */
    createChannelCard(channel) {
        const logo = channel.logos?.[0]?.url;
        const category = channel.categories?.[0];
        const country = this.countries.find(c => c.code === channel.country);

        const card = Utils.createElement('article', {
            className: 'channel-card',
            dataset: { channelId: channel.id },
            onClick: () => this.openChannel(channel.id)
        }, [
            Utils.createElement('div', { className: 'channel-card-inner' }, [
                // Logo
                logo ?
                    Utils.createElement('img', {
                        className: 'channel-logo',
                        src: logo,
                        alt: channel.name,
                        loading: 'lazy',
                        onError: (e) => {
                            e.target.src = Utils.getPlaceholderLogo(channel.name);
                        }
                    }) :
                    Utils.createElement('div', { className: 'channel-logo-placeholder' }, ['📺']),

                // Info
                Utils.createElement('div', { className: 'channel-info' }, [
                    Utils.createElement('h3', { className: 'channel-name' }, [channel.name]),
                    Utils.createElement('div', { className: 'channel-meta' }, [
                        country ? Utils.createElement('span', { className: 'channel-country' },
                            [`${country.flag} ${country.name}`]) : null,
                        category ? Utils.createElement('span', { className: 'channel-category' },
                            [category]) : null
                    ].filter(Boolean))
                ]),

                // Favorite button
                Favorites.createToggleButton(channel.id)
            ])
        ]);

        return card;
    },

    /**
     * Open channel in player
     */
    async openChannel(channelId) {
        try {
            const channel = await API.getChannel(channelId);
            Player.open(channel);
        } catch (error) {
            console.error('Failed to load channel:', error);
            alert('Failed to load channel. Please try again.');
        }
    },

    /**
     * Load more channels
     */
    loadMore() {
        if (!this.hasMore || this.loading) return;
        this.currentPage++;
        this.loadChannels();
    },

    /**
     * Check if should auto-load more (infinite scroll)
     */
    shouldLoadMore() {
        if (!this.hasMore || this.loading) return false;

        const scrollY = window.scrollY;
        const windowHeight = window.innerHeight;
        const docHeight = document.documentElement.scrollHeight;

        return scrollY + windowHeight >= docHeight - 500;
    }
};

// Make available globally
window.Channels = Channels;
