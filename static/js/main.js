/**
 * Lausanne Cultura — frontend controller.
 * Fetches events, renders featured rail + themed sections,
 * handles filters, search and the detail modal.
 */
(() => {
    'use strict';

    const API = {
        events: '/api/events',
    };

    const MONTHS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'];

    const CATEGORY_VAR = {
        'Musique': 'var(--cat-musique)',
        'Théâtre': 'var(--cat-theatre)',
        'Exposition': 'var(--cat-exposition)',
        'Cinéma': 'var(--cat-cinema)',
        'Danse': 'var(--cat-danse)',
        'Festival': 'var(--cat-festival)',
        'Famille': 'var(--cat-famille)',
        'Conférence': 'var(--cat-conference)',
        'Sport': 'var(--cat-sport)',
        'Humour': 'var(--cat-humour)',
        'Atelier': 'var(--cat-atelier)',
        'Marché': 'var(--cat-marche)',
    };

    const FALLBACK_IMG = 'data:image/svg+xml;utf8,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">' +
        '<rect width="400" height="300" fill="%231d1d27"/>' +
        '<text x="50%" y="50%" font-family="serif" font-size="36" fill="%23555" text-anchor="middle" dy=".35em" font-style="italic">Cultura</text>' +
        '</svg>'
    );

    // ---------- DOM refs ----------
    const $ = (sel) => document.querySelector(sel);
    const refs = {
        topbar: $('#topbar'),
        searchToggle: $('#search-toggle'),
        searchBar: $('#search-bar'),
        searchInput: $('#search-input'),
        eventCount: $('#event-count'),
        categoryCount: $('#category-count'),
        featuredRail: $('#featured-rail'),
        filters: $('#filters'),
        themesContainer: $('#themes-container'),
        empty: $('#empty-state'),
        modal: $('#modal'),
        modalImage: $('#modal-image'),
        modalCat: $('#modal-cat'),
        modalTitle: $('#modal-title'),
        modalDate: $('#modal-date'),
        modalLocation: $('#modal-location'),
        modalPrice: $('#modal-price'),
        modalDesc: $('#modal-desc'),
        modalLink: $('#modal-link'),
    };

    // ---------- State ----------
    const state = {
        all: [],
        categories: [],
        active: '',
        search: '',
    };

    // ---------- Utilities ----------
    function categoryColor(cat) {
        return CATEGORY_VAR[cat] || 'var(--cat-default)';
    }

    function formatDateTag(iso) {
        if (!iso) return { day: '—', month: '' };
        const d = new Date(iso);
        if (isNaN(d.getTime())) {
            // Try yyyy-mm-dd manually
            const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
            if (m) {
                return { day: parseInt(m[3], 10), month: MONTHS[parseInt(m[2], 10) - 1] };
            }
            return { day: '—', month: '' };
        }
        return { day: d.getDate(), month: MONTHS[d.getMonth()] };
    }

    function formatFullDate(iso, time, end) {
        const tag = formatDateTag(iso);
        let out = `${tag.day} ${tag.month}`;
        if (time) out += ` · ${time}`;
        if (end && end !== iso) {
            const e = formatDateTag(end);
            out += ` → ${e.day} ${e.month}`;
        }
        return out;
    }

    function safeImg(url) {
        return url && url.startsWith('http') ? url : FALLBACK_IMG;
    }

    function debounce(fn, wait) {
        let t;
        return (...args) => {
            clearTimeout(t);
            t = setTimeout(() => fn(...args), wait);
        };
    }

    // ---------- Rendering ----------
    function renderFeatured(events) {
        const featured = events.filter(e => e.featured).slice(0, 8);
        if (featured.length === 0) {
            // No featured events: take first 5 with images
            const fallback = events.filter(e => e.image).slice(0, 5);
            featured.push(...fallback);
        }

        if (featured.length === 0) {
            refs.featuredRail.innerHTML = '<p style="padding: 0 var(--gutter); color: var(--muted);">Aucun événement à la une.</p>';
            return;
        }

        refs.featuredRail.innerHTML = featured.map(evt => `
            <article class="featured-card" data-id="${evt.id}">
                <img src="${safeImg(evt.image)}" alt="${escapeHtml(evt.title)}" loading="lazy"
                     onerror="this.src='${FALLBACK_IMG}'">
                <div class="featured-content">
                    <span class="featured-badge">
                        <span class="pulse" aria-hidden="true"></span>
                        ${evt.category || 'À la une'}
                    </span>
                    <h3 class="featured-title">${escapeHtml(evt.title)}</h3>
                    <div class="featured-meta">
                        <span>${formatFullDate(evt.date, evt.time, evt.end_date)}</span>
                        <span class="sep">·</span>
                        <span>${escapeHtml(evt.location || 'Lausanne')}</span>
                    </div>
                </div>
            </article>
        `).join('');
    }

    function renderFilters(categories) {
        const present = new Set(state.all.map(e => e.category).filter(Boolean));
        const sortedCats = Array.from(present).sort();

        refs.filters.innerHTML =
            `<button class="chip ${state.active === '' ? 'active' : ''}" data-category="">Tout</button>` +
            sortedCats.map(c =>
                `<button class="chip ${state.active === c ? 'active' : ''}" data-category="${escapeAttr(c)}" style="--cat-color: ${categoryColor(c)};">${escapeHtml(c)}</button>`
            ).join('');
    }

    function renderThemes(events) {
        if (events.length === 0) {
            refs.themesContainer.innerHTML = '';
            refs.empty.hidden = false;
            return;
        }
        refs.empty.hidden = true;

        // Group by category
        const groups = {};
        events.forEach(evt => {
            const cat = evt.category || 'Culture';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(evt);
        });

        // If a single category is filtered, just show its events under one heading
        const sortedKeys = state.active
            ? [state.active]
            : Object.keys(groups).sort((a, b) => groups[b].length - groups[a].length);

        refs.themesContainer.innerHTML = sortedKeys.map(cat => {
            const items = groups[cat] || [];
            if (items.length === 0) return '';
            return `
                <section class="theme-section" aria-labelledby="theme-${slug(cat)}">
                    <div class="section-head">
                        <h2 id="theme-${slug(cat)}" class="section-title" style="--cat-color: ${categoryColor(cat)};">
                            ${escapeHtml(cat)}
                        </h2>
                        <p class="section-sub">${items.length} événement${items.length > 1 ? 's' : ''}</p>
                    </div>
                    <div class="theme-rail">
                        ${items.map(renderEventCard).join('')}
                    </div>
                </section>
            `;
        }).join('');
    }

    function renderEventCard(evt) {
        const tag = formatDateTag(evt.date);
        return `
            <article class="event-card" data-id="${evt.id}" style="--cat-color: ${categoryColor(evt.category)};">
                <div class="event-image">
                    <img src="${safeImg(evt.image)}" alt="${escapeHtml(evt.title)}" loading="lazy"
                         onerror="this.src='${FALLBACK_IMG}'">
                    <div class="event-date-tag">
                        <span class="day">${tag.day}</span>
                        <span class="month">${tag.month}</span>
                    </div>
                </div>
                <div class="event-body">
                    <span class="event-cat">${escapeHtml(evt.category || 'Culture')}</span>
                    <h3 class="event-title">${escapeHtml(evt.title)}</h3>
                    <p class="event-loc">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                        ${escapeHtml(evt.location || 'Lausanne')}
                    </p>
                </div>
            </article>
        `;
    }

    // ---------- Modal ----------
    function openModal(evt) {
        refs.modalImage.style.backgroundImage = `url('${safeImg(evt.image)}')`;
        refs.modalCat.textContent = evt.category || 'Culture';
        refs.modalCat.style.setProperty('--cat-color', categoryColor(evt.category));
        refs.modalTitle.textContent = evt.title;
        refs.modalDate.textContent = formatFullDate(evt.date, evt.time, evt.end_date);
        refs.modalLocation.textContent = evt.location + (evt.address && evt.address !== evt.location ? ` — ${evt.address}` : '');
        refs.modalPrice.textContent = evt.price || 'Voir détails';
        refs.modalDesc.textContent = evt.description || '';

        if (evt.url && evt.url !== '#') {
            refs.modalLink.href = evt.url;
            refs.modalLink.style.display = 'inline-flex';
        } else {
            refs.modalLink.style.display = 'none';
        }

        refs.modal.hidden = false;
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        refs.modal.hidden = true;
        document.body.style.overflow = '';
    }

    // ---------- Data fetch ----------
    async function fetchEvents() {
        const params = new URLSearchParams();
        if (state.active) params.set('category', state.active);
        if (state.search) params.set('search', state.search);

        try {
            const resp = await fetch(`${API.events}?${params}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            state.all = data.events || [];
            state.categories = data.categories || [];
            return data;
        } catch (err) {
            console.error('Failed to load events', err);
            state.all = [];
            return { events: [], categories: [] };
        }
    }

    async function refreshAll() {
        await fetchEvents();
        refs.eventCount.textContent = state.all.length;
        refs.categoryCount.textContent = new Set(state.all.map(e => e.category).filter(Boolean)).size;

        // Featured + filters built from full dataset only on first load
        if (!state.active && !state.search) {
            renderFeatured(state.all);
            renderFilters(state.categories);
        }
        renderThemes(state.all);
    }

    // ---------- Event handlers ----------
    function onCardClick(target) {
        const card = target.closest('[data-id]');
        if (!card) return;
        const id = card.dataset.id;
        const evt = state.all.find(e => e.id === id);
        if (evt) openModal(evt);
    }

    function bindEvents() {
        refs.searchToggle.addEventListener('click', () => {
            const isOpen = !refs.searchBar.hidden;
            refs.searchBar.hidden = isOpen;
            refs.searchToggle.setAttribute('aria-expanded', String(!isOpen));
            if (!isOpen) refs.searchInput.focus();
        });

        refs.searchInput.addEventListener('input', debounce(async (e) => {
            state.search = e.target.value.trim();
            await fetchEvents();
            renderThemes(state.all);
        }, 240));

        refs.filters.addEventListener('click', async (e) => {
            const chip = e.target.closest('.chip');
            if (!chip) return;
            state.active = chip.dataset.category || '';
            refs.filters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            await fetchEvents();
            renderThemes(state.all);
            window.scrollTo({ top: refs.filters.offsetTop - 60, behavior: 'smooth' });
        });

        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-close]')) {
                closeModal();
                return;
            }
            if (e.target.closest('.featured-card, .event-card')) {
                onCardClick(e.target);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !refs.modal.hidden) closeModal();
        });

        // Subtle topbar elevation on scroll
        let lastY = 0;
        window.addEventListener('scroll', () => {
            const y = window.scrollY;
            refs.topbar.style.boxShadow = y > 8 ? '0 8px 24px rgba(0,0,0,0.4)' : 'none';
            lastY = y;
        }, { passive: true });
    }

    // ---------- Helpers ----------
    function escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    function escapeAttr(s) { return escapeHtml(s); }
    function slug(s) {
        return String(s || '').toLowerCase()
            .normalize('NFD').replace(/[̀-ͯ]/g, '')
            .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    }

    // ---------- Boot ----------
    document.addEventListener('DOMContentLoaded', () => {
        bindEvents();
        refreshAll();
    });
})();
