/* Lausanne Cultura : programme du moment.
   Données : /api/events (déjà trié et groupé par moment côté serveur).
   Préférences (Mes goûts, vue, filtres) : localStorage, sans compte. */
(() => {
    'use strict';

    const API = '/api/events';
    const TAG_STYLES = ['t1', 't2', 't3'];
    const KEYS = { view: 'lc.view', tastes: 'lc.tastes', forMe: 'lc.forMe', cheap: 'lc.cheap' };

    const $ = (sel, root = document) => root.querySelector(sel);

    const store = {
        get(key, fallback) {
            try {
                const raw = localStorage.getItem(key);
                return raw === null ? fallback : JSON.parse(raw);
            } catch { return fallback; }
        },
        set(key, value) {
            try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* stockage indisponible */ }
        },
    };

    // ---------- État ----------

    const tastes = Object.assign({ rubrics: [], venues: [], onboarded: false }, store.get(KEYS.tastes, {}));
    const state = {
        data: null,
        byId: new Map(),
        moment: 'tonight',
        view: store.get(KEYS.view, 'list') === 'posters' ? 'posters' : 'list',
        forMe: store.get(KEYS.forMe, true) && tastes.rubrics.length > 0,
        cheap: !!store.get(KEYS.cheap, false),
        query: '',
        revealed: new Set(),
        status: 'loading',
        controller: null,
    };

    // ---------- Outils ----------

    function h(tag, attrs = {}, ...children) {
        const node = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (v === null || v === undefined || v === false) continue;
            if (k === 'class') node.className = v;
            else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
            else node.setAttribute(k, v === true ? '' : v);
        }
        for (const child of children.flat()) {
            if (child === null || child === undefined || child === false) continue;
            node.append(child instanceof Node ? child : document.createTextNode(String(child)));
        }
        return node;
    }

    const fold = (s) => (s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
    const venueKey = (evt) => fold(evt.location);
    const hasVenue = (evt) => venueKey(evt) !== '' && venueKey(evt) !== 'lausanne';
    const hasLink = (evt) => /^https?:\/\//i.test(evt.url || '');
    const tagClass = (rubric) => {
        const i = (state.data?.rubrics || []).indexOf(rubric);
        return TAG_STYLES[(i < 0 ? 5 : i) % TAG_STYLES.length];
    };

    const dayFmt = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'long' });
    const shortFmt = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'long' });
    const parseDay = (iso) => {
        if (!iso) return null;
        const [y, m, d] = iso.split('-').map(Number);
        return y ? new Date(y, m - 1, d) : null;
    };
    const dayLabel = (iso) => (iso ? dayFmt.format(parseDay(iso)) : 'Date non communiquée');

    function save() {
        store.set(KEYS.tastes, tastes);
        store.set(KEYS.forMe, state.forMe);
        store.set(KEYS.cheap, state.cheap);
        store.set(KEYS.view, state.view);
    }

    // ---------- Filtres ----------

    const isSmallPrice = (evt) =>
        evt.is_free || (evt.price_min !== null && evt.price_min !== undefined && evt.price_min <= state.data.small_price_chf);

    /** Masqué par Mes goûts : lieu masqué, ou rubrique hors « Pour moi ». */
    function isMasked(evt) {
        if (hasVenue(evt) && tastes.venues.includes(venueKey(evt))) return true;
        return state.forMe && tastes.rubrics.length > 0 && !tastes.rubrics.includes(evt.rubric);
    }

    /** Événements d'un jour après filtres. Les masqués sont comptés, pas oubliés. */
    function dayView(block) {
        const key = block.date || 'undated';
        const reveal = state.revealed.has(key);
        let masked = 0;
        const shown = [];
        for (const id of block.ids) {
            const evt = state.byId.get(id);
            if (!evt) continue;
            if (state.cheap && !isSmallPrice(evt)) continue;
            const m = isMasked(evt);
            if (m) masked += 1;
            if (!m || reveal) shown.push({ evt, masked: m });
        }
        return { key, date: block.date, shown, masked, reveal };
    }

    function momentCount(moment) {
        const ids = new Set();
        for (const block of moment.days) {
            for (const id of block.ids) {
                const evt = state.byId.get(id);
                if (!evt || (state.cheap && !isSmallPrice(evt)) || isMasked(evt)) continue;
                ids.add(id);
            }
        }
        return ids.size;
    }

    /** En recherche : tous les jours de tous les onglets, une seule fois. */
    function searchDays() {
        const seen = new Map();
        for (const m of state.data.moments) {
            for (const block of m.days) {
                const k = block.date || 'undated';
                if (!seen.has(k)) seen.set(k, { date: block.date, ids: [] });
                const entry = seen.get(k);
                for (const id of block.ids) if (!entry.ids.includes(id)) entry.ids.push(id);
            }
        }
        return [...seen.values()].sort((a, b) => (a.date || '9999').localeCompare(b.date || '9999'));
    }

    // ---------- Rendu : onglets et contrôles ----------

    const tabsEl = $('#tabs');
    const panel = $('#panel');

    function renderTabs() {
        tabsEl.replaceChildren(...state.data.moments.map((m) => {
            const selected = m.key === state.moment;
            return h('button', {
                type: 'button', role: 'tab', class: 'tab', id: `tab-${m.key}`,
                'aria-selected': String(selected), 'aria-controls': 'panel',
                tabindex: selected ? '0' : '-1', 'data-moment': m.key,
            }, m.label, h('small', {}, momentCount(m)));
        }));
        panel.setAttribute('aria-labelledby', `tab-${state.moment}`);
    }

    function renderControls() {
        $('#filter-forme').setAttribute('aria-pressed', String(state.forMe));
        $('#filter-cheap').setAttribute('aria-pressed', String(state.cheap));
        for (const b of document.querySelectorAll('.seg button')) {
            b.setAttribute('aria-pressed', String(b.dataset.view === state.view));
        }
    }

    // ---------- Rendu : événements ----------

    function hourCell(evt, cls = 'h') {
        return evt.time
            ? h('span', { class: cls }, evt.time)
            : h('span', { class: `${cls} nc` }, 'Heure n. c.');
    }

    function detailLine(evt, day) {
        const parts = [];
        if (evt.subcategory && fold(evt.subcategory) !== fold(evt.category)) parts.push(evt.subcategory);
        if (evt.end_date && evt.end_date !== evt.date && day) {
            parts.push(`jusqu'au ${shortFmt.format(parseDay(evt.end_date))}`);
        }
        return parts.length ? h('span', { class: 'd' }, parts.join(' · ')) : null;
    }

    function priceNode(evt, cls = 'price') {
        if (evt.is_free) return h('span', { class: 'free' }, 'GRATUIT');
        if (evt.known && evt.price) return h('span', { class: cls }, evt.price);
        return h('span', { class: `${cls} nc` }, 'Prix n. c.');
    }

    const venueText = (evt) => (hasVenue(evt) ? evt.location : 'Lieu n. c.');

    function rowItem({ evt, masked }, day) {
        return h('li', {},
            h('button', {
                type: 'button', class: `row${masked ? ' is-masked' : ''}`,
                'data-id': evt.id, 'aria-haspopup': 'dialog',
            },
            hourCell(evt),
            h('span', {}, h('span', { class: 't' }, evt.title), detailLine(evt, day)),
            h('span', { class: 'v' }, venueText(evt), priceNode(evt))));
    }

    function tileItem({ evt, masked }) {
        const typeLabel = evt.subcategory && evt.subcategory.length <= 22 ? evt.subcategory : evt.rubric;
        const typeMedia = () => h('span', { class: 'media type' },
            h('span', { class: 'k' }, typeLabel),
            h('span', { class: 'vn' }, venueText(evt)));
        let media;
        if (evt.image) {
            const img = h('img', { src: evt.image, alt: '', loading: 'lazy', decoding: 'async' });
            media = h('span', { class: 'media' }, img, evt.time ? h('span', { class: 'st' }, evt.time) : null);
            img.addEventListener('error', () => {
                media.replaceWith(typeMedia());
                const t = btn.querySelector('.t');
                if (evt.time && t && !t.dataset.timed) { t.dataset.timed = '1'; t.prepend(`${evt.time} · `); }
            }, { once: true });
        } else {
            media = typeMedia();
        }
        const title = h('span', { class: 't' }, !evt.image && evt.time ? `${evt.time} · ` : '', evt.title);
        if (!evt.image && evt.time) title.dataset.timed = '1';
        const btn = h('button', {
            type: 'button', class: `tile${masked ? ' is-masked' : ''}`,
            'data-id': evt.id, 'aria-haspopup': 'dialog',
        },
        media,
        h('span', { class: 'tile-body' }, title,
            h('span', { class: 'vv' }, venueText(evt), ' · ', priceNode(evt, 'p'))));
        return h('li', {}, btn);
    }

    function renderDay(view) {
        const groups = new Map();
        for (const item of view.shown) {
            if (!groups.has(item.evt.rubric)) groups.set(item.evt.rubric, []);
            groups.get(item.evt.rubric).push(item);
        }
        const order = state.data.rubrics;
        const rubrics = [...groups.keys()].sort((a, b) => order.indexOf(a) - order.indexOf(b));
        const headId = `day-${view.key}`;

        const maskedNote = view.masked > 0
            ? h('p', { class: 'masked' },
                `${view.masked} masqué${view.masked > 1 ? 's' : ''} · `,
                h('button', { type: 'button', 'data-reveal': view.key, 'aria-expanded': String(view.reveal) },
                    view.reveal ? 'cacher' : 'afficher'))
            : null;

        return h('section', { class: 'day', 'aria-labelledby': headId },
            h('div', { class: 'day-head' }, h('h2', { id: headId }, dayLabel(view.date)), maskedNote),
            rubrics.map((r) => {
                const items = groups.get(r);
                return h('div', { class: 'rubric' },
                    h('h3', { class: 'rubric-head' },
                        h('span', { class: `tag ${tagClass(r)}` }, r),
                        h('span', { class: 'n', 'aria-label': `${items.length} événement${items.length > 1 ? 's' : ''}` }, items.length)),
                    state.view === 'posters'
                        ? h('ul', { class: 'grid' }, items.map((it) => tileItem(it)))
                        : h('ul', { class: 'rows' }, items.map((it) => rowItem(it, view.date))));
            }));
    }

    function stateBlock(title, text, actions = []) {
        return h('div', { class: 'state' }, h('h2', {}, title), text ? h('p', {}, text) : null,
            actions.length ? h('div', { class: 'state-actions' }, actions) : null);
    }

    const actionBtn = (label, onClick, ink = false) =>
        h('button', { type: 'button', class: `btn${ink ? ' btn-ink' : ''}`, onclick: onClick }, label);

    function renderEmpty(totalMasked, rawCount) {
        if (state.query && rawCount === 0) {
            return stateBlock(`Aucun résultat pour « ${state.query} »`,
                'Vérifiez l\'orthographe ou essayez un nom de lieu.',
                [actionBtn('Effacer la recherche', () => closeSearch(true), true)]);
        }
        if (rawCount > 0) {
            const actions = [];
            if (state.cheap) actions.push(actionBtn('Retirer « Gratuit / petit prix »', () => setCheap(false), true));
            if (totalMasked > 0) actions.push(actionBtn(`Afficher les ${totalMasked} masqués`, revealAll));
            return stateBlock('Rien avec ces filtres', state.cheap
                ? 'Aucun événement gratuit ou à CHF 15 et moins, parmi ceux dont le prix est connu.'
                : 'Tout est masqué par Mes goûts.', actions);
        }
        const moment = state.data.moments.find((m) => m.key === state.moment);
        const others = state.data.moments.filter((m) => m.key !== state.moment && m.count > 0)
            .slice(0, 2)
            .map((m) => actionBtn(`${m.label} · ${momentCount(m)}`, () => selectMoment(m.key, true)));
        const label = { tonight: 'ce soir', tomorrow: 'demain', weekend: 'ce week-end', later: 'plus tard' }[moment.key];
        return stateBlock(`Rien au programme ${label}`,
            'Aucun événement collecté pour ce moment.', others);
    }

    function render() {
        panel.setAttribute('aria-busy', String(state.status === 'loading'));
        if (state.status === 'loading') {
            panel.replaceChildren(h('div', { class: 'skeleton', 'aria-label': 'Chargement du programme' },
                h('div', { class: 'sk w1' }), ...Array.from({ length: 6 }, (_, i) => h('div', { class: `sk ${i % 2 ? 'w3' : 'w2'}` }))));
            return;
        }
        if (state.status === 'error') {
            $('#tabs-shell').hidden = !!state.query;
            panel.replaceChildren(stateBlock('Le programme n\'a pas pu être chargé',
                'Le serveur ne répond pas pour l\'instant. Vérifiez votre connexion puis réessayez.',
                [actionBtn('Réessayer', () => load(), true)]));
            return;
        }

        const searching = !!state.query;
        $('#tabs-shell').hidden = searching;
        $('#demo-note').hidden = !state.data.demo;
        $('#onboard').hidden = tastes.onboarded || searching;
        renderTabs();
        renderControls();

        const blocks = searching
            ? searchDays()
            : state.data.moments.find((m) => m.key === state.moment).days;
        const views = blocks.map(dayView);
        const visible = views.filter((v) => v.shown.length > 0);
        const totalMasked = views.reduce((n, v) => n + v.masked, 0);
        const rawCount = blocks.reduce((n, b) => n + b.ids.length, 0);

        const summary = $('#search-summary');
        const found = new Set(visible.flatMap((v) => v.shown.map((s) => s.evt.id))).size;
        summary.hidden = !searching || found === 0;
        if (searching) {
            const n = found;
            summary.replaceChildren(
                h('strong', {}, `${n} résultat${n > 1 ? 's' : ''}`), ` pour « ${state.query} » · `,
                h('button', { type: 'button', class: 'text-btn', onclick: () => closeSearch(true) }, 'Effacer'));
        }

        panel.replaceChildren(...(visible.length ? visible.map(renderDay) : [renderEmpty(totalMasked, rawCount)]));
        updateFooter();
    }

    function updateFooter() {
        const d = state.data;
        const el = $('#foot-source');
        if (d.demo) {
            el.textContent = 'Aucun événement collecté pour l\'instant : la page affiche des données de démonstration fictives.';
            return;
        }
        let text = `Programme collecté automatiquement sur ${d.source_count} sites de lieux et d'agendas lausannois, mis à jour au plus une fois par heure.`;
        if (d.last_update) {
            const t = new Date(d.last_update);
            text += ` Dernière collecte : ${t.toLocaleDateString('fr-CH', { day: 'numeric', month: 'long' })} à ${t.toLocaleTimeString('fr-CH', { hour: '2-digit', minute: '2-digit' })}.`;
        }
        el.textContent = text;
    }

    // ---------- Actions ----------

    function selectMoment(key, focus = false) {
        state.moment = key;
        state.revealed.clear();
        render();
        if (focus) $(`#tab-${key}`)?.focus();
    }

    function setCheap(on) { state.cheap = on; save(); render(); }

    function revealAll() {
        const blocks = state.data.moments.find((m) => m.key === state.moment).days;
        for (const b of blocks) state.revealed.add(b.date || 'undated');
        render();
    }

    async function load() {
        state.controller?.abort();
        const controller = new AbortController();
        state.controller = controller;
        if (!state.data) { state.status = 'loading'; render(); }
        try {
            const url = state.query ? `${API}?search=${encodeURIComponent(state.query)}` : API;
            const res = await fetch(url, { signal: controller.signal, headers: { Accept: 'application/json' } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            state.data = data;
            state.byId = new Map(data.events.map((e) => [e.id, e]));
            state.status = 'ready';
            render();
            openFromHash();
        } catch (err) {
            if (err.name === 'AbortError') return;
            state.status = 'error';
            render();
        }
    }

    // ---------- Recherche ----------

    const searchRow = $('#search-row');
    const searchInput = $('#search-input');
    const searchToggle = $('#search-toggle');
    let searchTimer = null;

    function openSearch() {
        searchRow.hidden = false;
        searchToggle.setAttribute('aria-expanded', 'true');
        searchInput.focus();
    }

    function closeSearch(refocus = false) {
        searchRow.hidden = true;
        searchToggle.setAttribute('aria-expanded', 'false');
        searchInput.value = '';
        clearTimeout(searchTimer);
        if (state.query) { state.query = ''; load(); }
        if (refocus) searchToggle.focus();
    }

    searchToggle.addEventListener('click', () => (searchRow.hidden ? openSearch() : closeSearch(true)));
    $('#search-close').addEventListener('click', () => closeSearch(true));
    $('#search-form').addEventListener('submit', (e) => { e.preventDefault(); clearTimeout(searchTimer); runSearch(); });
    searchInput.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(runSearch, 250); });
    searchInput.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSearch(true); });

    function runSearch() {
        const q = searchInput.value.trim();
        if (q === state.query) return;
        state.query = q;
        state.revealed.clear();
        load();
    }

    // ---------- Panneaux (dialog natif : focus piégé, Échap) ----------

    let returnFocus = null;

    function openSheet(dialog) {
        returnFocus = document.activeElement;
        dialog.showModal();
        dialog.scrollTop = 0;
        const target = dialog.querySelector('[data-autofocus]') || dialog.querySelector('.sheet-title, .ev-title');
        if (target) { target.setAttribute('tabindex', '-1'); target.focus(); }
    }

    for (const dialog of document.querySelectorAll('dialog.sheet')) {
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog || e.target.closest('[data-close]')) dialog.close();
        });
        dialog.addEventListener('close', () => {
            if (dialog.id === 'event-sheet' && location.hash.startsWith('#e=')) {
                history.replaceState(null, '', location.pathname + location.search);
            }
            const back = returnFocus && document.contains(returnFocus) ? returnFocus : null;
            const id = dialog.dataset.eventId;
            (back || (id && panel.querySelector(`[data-id="${CSS.escape(id)}"]`)) || panel).focus?.();
            returnFocus = null;
        });
    }

    // ---------- Fiche détaillée ----------

    const eventSheet = $('#event-sheet');

    function whenText(evt) {
        if (!evt.date) return h('span', { class: 'nc' }, 'Date non communiquée');
        const multi = evt.end_date && evt.end_date !== evt.date;
        const dates = multi
            ? `Du ${shortFmt.format(parseDay(evt.date))} au ${shortFmt.format(parseDay(evt.end_date))}`
            : dayLabel(evt.date);
        return [dates.charAt(0).toUpperCase() + dates.slice(1),
            h('small', {}, evt.time ? `${multi ? 'Dès' : 'À'} ${evt.time}` : 'Heure non communiquée')];
    }

    function renderEventSheet(evt) {
        const venueHidden = hasVenue(evt) && tastes.venues.includes(venueKey(evt));
        const shareBtn = h('button', { type: 'button', class: 'btn btn-ink', onclick: () => share(evt) },
            svgIcon('share'), 'Partager');
        const linkBtn = hasLink(evt)
            ? h('a', { class: 'btn', href: evt.url, target: '_blank', rel: 'noopener' }, 'Site officiel', svgIcon('out'),
                h('span', { class: 'sr-only' }, '(nouvel onglet)'))
            : null;
        const hideBtn = hasVenue(evt)
            ? h('button', { type: 'button', class: 'text-btn ev-hide', onclick: () => toggleVenue(evt) },
                venueHidden ? `Ne plus masquer ${evt.location}` : `Masquer ${evt.location}`)
            : null;

        $('#sheet-body').replaceChildren(
            h('span', { class: `tag ${tagClass(evt.rubric)}` }, evt.rubric),
            h('h2', { class: 'ev-title', id: 'sheet-title' }, evt.title),
            h('dl', { class: 'ev-facts' },
                h('div', {}, h('dt', {}, 'Quand'), h('dd', {}, whenText(evt))),
                h('div', {}, h('dt', {}, 'Où'), h('dd', {},
                    hasVenue(evt) ? evt.location : h('span', { class: 'nc' }, 'Lieu non communiqué'),
                    evt.address && fold(evt.address) !== venueKey(evt) ? h('small', {}, evt.address) : null)),
                h('div', {}, h('dt', {}, 'Prix'), h('dd', {},
                    evt.known && evt.price ? evt.price : h('span', { class: 'nc' }, 'Prix non communiqué')))),
            evt.description ? h('p', { class: 'ev-desc' }, evt.description) : null,
            state.data.demo ? h('p', { class: 'ev-demo' }, 'Événement fictif (données de démonstration).') : null,
            h('div', { class: 'sheet-actions' }, shareBtn, linkBtn),
            hideBtn);
        eventSheet.dataset.eventId = evt.id;
    }

    function openEvent(id) {
        const evt = state.byId.get(id);
        if (!evt) return;
        renderEventSheet(evt);
        if (location.hash !== `#e=${id}`) history.replaceState(null, '', `#e=${encodeURIComponent(id)}`);
        if (!eventSheet.open) openSheet(eventSheet);
    }

    function openFromHash() {
        const m = location.hash.match(/^#e=(.+)$/);
        if (m && !eventSheet.open) openEvent(decodeURIComponent(m[1]));
    }

    async function share(evt) {
        const url = `${location.origin}${location.pathname}#e=${encodeURIComponent(evt.id)}`;
        const when = evt.date ? `${dayLabel(evt.date)}${evt.time ? ` à ${evt.time}` : ''}` : '';
        const text = [evt.title, [when, hasVenue(evt) ? evt.location : ''].filter(Boolean).join(', ')].filter(Boolean).join(' · ');
        if (navigator.share) {
            try { await navigator.share({ title: evt.title, text, url }); return; } catch (err) {
                if (err.name === 'AbortError') return;
            }
        }
        try {
            await navigator.clipboard.writeText(url);
            toast('Lien copié');
        } catch {
            toast('Copie impossible : le lien est dans la barre d\'adresse');
        }
    }

    function svgIcon(kind) {
        const ns = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('width', '16'); svg.setAttribute('height', '16'); svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '2.4');
        svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round'); svg.setAttribute('aria-hidden', 'true');
        const d = kind === 'share' ? 'M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6' : 'M7 17 17 7M8 7h9v9';
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', d);
        svg.append(path);
        return svg;
    }

    // ---------- Mes goûts ----------

    function toggleVenue(evt) {
        const key = venueKey(evt);
        const wasHidden = tastes.venues.includes(key);
        tastes.venues = wasHidden ? tastes.venues.filter((v) => v !== key) : [...tastes.venues, key];
        tastes.venueNames = Object.assign({}, tastes.venueNames, { [key]: evt.location });
        save();
        if (wasHidden) {
            renderEventSheet(evt);
            render();
            toast(`${evt.location} n'est plus masqué`);
            return;
        }
        render();
        eventSheet.close();
        toast(`${evt.location} masqué`, 'Annuler', () => toggleVenue(evt));
    }

    function choiceButtons(container, selected) {
        container.replaceChildren(...state.data.rubrics.map((r) => h('button', {
            type: 'button', class: `choice ${tagClass(r)}`, 'data-rubric': r,
            'aria-pressed': String(selected.includes(r)),
            onclick: (e) => {
                const b = e.currentTarget;
                b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true'));
            },
        }, r)));
    }

    const pickedRubrics = (container) =>
        [...container.querySelectorAll('[aria-pressed="true"]')].map((b) => b.dataset.rubric);

    function applyRubrics(rubrics) {
        tastes.rubrics = rubrics;
        tastes.onboarded = true;
        state.forMe = rubrics.length > 0;
        state.revealed.clear();
        save();
        render();
    }

    const tastesSheet = $('#tastes-sheet');

    function openTastes() {
        if (!state.data) return;
        choiceButtons($('#tastes-choices'), tastes.rubrics);
        const list = $('#tastes-venues');
        const names = tastes.venueNames || {};
        list.replaceChildren(...(tastes.venues.length
            ? tastes.venues.map((key) => h('li', {}, names[key] || key,
                h('button', {
                    type: 'button', class: 'text-btn',
                    onclick: (e) => {
                        tastes.venues = tastes.venues.filter((v) => v !== key);
                        save();
                        e.currentTarget.closest('li').remove();
                        if (!tastes.venues.length) list.append(emptyVenues());
                        render();
                    },
                }, 'Afficher à nouveau')))
            : [emptyVenues()]));
        openSheet(tastesSheet);
    }

    const emptyVenues = () => h('li', { class: 'empty' }, 'Aucun lieu masqué. Pour en masquer un, ouvrez un événement puis « Masquer ».');

    $('#tastes-open').addEventListener('click', openTastes);
    $('#tastes-save').addEventListener('click', () => {
        applyRubrics(pickedRubrics($('#tastes-choices')));
        tastesSheet.close();
        toast(tastes.rubrics.length ? 'Mes goûts enregistrés' : 'Aucune rubrique choisie : tout est affiché');
    });

    $('#onboard-save').addEventListener('click', () => {
        applyRubrics(pickedRubrics($('#onboard-choices')));
        $('#tabs')?.querySelector('[aria-selected="true"]')?.focus();
    });
    $('#onboard-skip').addEventListener('click', () => {
        tastes.onboarded = true;
        save();
        render();
        $('#tabs')?.querySelector('[aria-selected="true"]')?.focus();
    });

    // ---------- Contrôles ----------

    $('#filter-forme').addEventListener('click', () => {
        if (!tastes.rubrics.length) { openTastes(); return; }
        state.forMe = !state.forMe;
        state.revealed.clear();
        save();
        render();
    });
    $('#filter-cheap').addEventListener('click', () => setCheap(!state.cheap));

    for (const b of document.querySelectorAll('.seg button')) {
        b.addEventListener('click', () => { state.view = b.dataset.view; save(); render(); });
    }

    tabsEl.addEventListener('click', (e) => {
        const tab = e.target.closest('[role="tab"]');
        if (tab) selectMoment(tab.dataset.moment);
    });
    tabsEl.addEventListener('keydown', (e) => {
        const keys = { ArrowRight: 1, ArrowLeft: -1, Home: -99, End: 99 };
        if (!(e.key in keys)) return;
        e.preventDefault();
        const list = state.data.moments.map((m) => m.key);
        let i = list.indexOf(state.moment) + keys[e.key];
        i = Math.max(0, Math.min(list.length - 1, e.key === 'Home' ? 0 : e.key === 'End' ? list.length - 1 : (i + list.length) % list.length));
        selectMoment(list[i], true);
    });

    panel.addEventListener('click', (e) => {
        const reveal = e.target.closest('[data-reveal]');
        if (reveal) {
            const k = reveal.dataset.reveal;
            state.revealed.has(k) ? state.revealed.delete(k) : state.revealed.add(k);
            render();
            panel.querySelector(`[data-reveal="${CSS.escape(k)}"]`)?.focus();
            return;
        }
        const card = e.target.closest('[data-id]');
        if (card) openEvent(card.dataset.id);
    });

    window.addEventListener('hashchange', openFromHash);

    // ---------- Toast ----------

    const toastEl = $('#toast');
    let toastTimer = null;

    function toast(message, actionLabel, onAction) {
        clearTimeout(toastTimer);
        toastEl.replaceChildren(h('span', {}, message),
            actionLabel ? h('button', {
                type: 'button',
                onclick: () => { toastEl.hidden = true; onAction(); },
            }, actionLabel) : null);
        toastEl.hidden = false;
        toastTimer = setTimeout(() => { toastEl.hidden = true; }, actionLabel ? 6000 : 3000);
    }

    // ---------- Démarrage ----------

    function initOnboarding() {
        if (tastes.onboarded || !state.data) return;
        choiceButtons($('#onboard-choices'), []);
    }

    load().then(initOnboarding);
})();
