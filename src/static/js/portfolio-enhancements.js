import Storage from './storage.js';

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const money = (value, currency = 'KES') => new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(value) || 0);
const asOf = value => value ? `As of ${new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - ${new Date(value).toLocaleDateString('en-GB')}` : 'As of —';

async function ensureCategory(name, type) {
    const categories = await Storage.getAll(Storage.STORES.categories);
    let category = categories.find(item => item.name === name);
    if (!category) {
        category = { id: crypto.randomUUID(), name, category_type: type, is_default: false, created_at: new Date().toISOString() };
        await Storage.setItem(Storage.STORES.categories, category);
    }
    return category;
}

async function saveLocalHolding({ name, category, amount, currency = 'KES', units = 0, buyPrice = 0, currentPrice = 0, exchange = null, backendId = null, notes = '' }) {
    await Storage.setItem(Storage.STORES.holdings, {
        id: crypto.randomUUID(), name, category_id: category.id, amount: Number(amount) || 0, currency,
        units: Number(units) || 0, average_buy_price: Number(buyPrice) || 0, current_price: Number(currentPrice) || 0,
        exchange, backend_stock_id: backendId, notes, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
}

function modalMarkup() {
    return `<div class="asset-modal-backdrop" id="asset-modal" hidden><div class="asset-modal" role="dialog" aria-modal="true" aria-labelledby="asset-modal-title">
      <div class="asset-modal-head"><div><p class="eyebrow">Quick add</p><h2 id="asset-modal-title">Add existing asset</h2></div><button type="button" class="btn btn-sm btn-secondary" id="asset-modal-close" aria-label="Close">×</button></div>
      <div class="asset-type-grid" id="asset-type-grid">
        <button type="button" data-asset-type="nse">📈<strong>NSE Stock</strong><small>Kenya equities</small></button>
        <button type="button" data-asset-type="us">🇺🇸<strong>US Stock</strong><small>Yahoo Finance</small></button>
        <button type="button" data-asset-type="mmf">🏦<strong>MMF</strong><small>Money market</small></button>
        <button type="button" data-asset-type="reit">🏢<strong>REIT</strong><small>Real estate</small></button>
        <button type="button" data-asset-type="bond">📜<strong>Government Bond</strong><small>Fixed income</small></button>
        <button type="button" data-asset-type="t-bill">🧾<strong>T-Bill</strong><small>Fixed income</small></button>
        <button type="button" data-asset-type="cash">💵<strong>Cash / Other</strong><small>Manual holding</small></button>
      </div>
      <form id="asset-modal-form" hidden></form>
    </div></div>`;
}

function field(label, id, type = 'text', attrs = '') { return `<div class="form-group"><label for="${id}">${label}</label><input id="${id}" type="${type}" ${attrs}></div>`; }

async function buildForm(type) {
    const form = $('#asset-modal-form');
    if (!form) return;
    const isStock = type === 'nse' || type === 'us';
    let html = '';
    if (type === 'nse') html += `<div class="form-group grid-span-2"><label for="asset-ticker">NSE stock</label><select id="asset-ticker"><option value="">Choose NSE stock</option></select></div>`;
    if (type === 'us') html += field('US ticker', 'asset-ticker', 'text', 'required maxlength="20" placeholder="AAPL, MSFT, NVDA" style="text-transform:uppercase"');
    if (type === 'mmf') html += field('Fund name', 'asset-name', 'text', 'required placeholder="e.g. CIC Money Market Fund"');
    if (type === 'reit') html += field('REIT / security', 'asset-name', 'text', 'required placeholder="e.g. ACORN-D"');
    if (['bond','t-bill','cash'].includes(type)) html += field('Asset name', 'asset-name', 'text', 'required');
    if (type === 'mmf') html += field('Investment amount (KES)', 'asset-amount', 'number', 'required min="0.01" step="0.01"');
    else if (isStock) html += `${field('Units / shares', 'asset-units', 'number', 'required min="0.000001" step="any"')}${field('Average buy price', 'asset-buy', 'number', 'required min="0.0001" step="any"')}${field('Current price', 'asset-current', 'number', 'required min="0.0001" step="any"')}`;
    else html += field(type === 'reit' ? 'Market value (KES)' : 'Current value (KES)', 'asset-amount', 'number', 'required min="0" step="0.01"');
    if (type === 'reit') html += `<div class="notice grid-span-2">ACORN is a REIT, not an ordinary NSE equity. It is tracked separately from NSE Stocks.</div>`;
    if (type === 'us') html += `<p id="us-price-status" class="text-muted grid-span-2"></p>`;
    html += `<div class="form-group grid-span-2"><label for="asset-notes">Notes <span class="text-muted">(optional)</span></label><input id="asset-notes" maxlength="500"></div><div class="form-group grid-span-2 form-actions"><button class="btn btn-primary" style="width:100%">Add asset</button></div>`;
    form.innerHTML = html; form.hidden = false;
    if (type === 'nse') {
        try {
            const response = await fetch('/api/market/stocks/nse-tickers');
            const stocks = await response.json();
            const select = $('#asset-ticker');
            (Array.isArray(stocks) ? stocks : []).filter(s => !String(s.ticker || '').startsWith('ACORN') && !String(s.ticker || '').includes('FAHR')).forEach(s => select.add(new Option(`${s.ticker} — ${s.name || ''}`, s.ticker)));
        } catch { /* manual API route remains available */ }
    }
    form.onsubmit = event => submitAsset(event, type);
}

async function submitAsset(event, type) {
    event.preventDefault();
    const ticker = $('#asset-ticker')?.value?.trim().toUpperCase();
    const name = $('#asset-name')?.value?.trim();
    const notes = $('#asset-notes')?.value?.trim() || '';
    try {
        if (type === 'us') {
            const response = await fetch('/api/us-market/stocks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker, shares_owned: Number($('#asset-units').value), average_buy_price: Number($('#asset-buy').value) }) });
            if (!response.ok) throw new Error((await response.json()).detail || 'Could not fetch Yahoo Finance price');
            const stock = await response.json();
            const category = await ensureCategory('US Stocks', 'Equities');
            await saveLocalHolding({ name: stock.ticker, category, amount: stock.current_value, currency: 'USD', units: stock.shares_owned, buyPrice: stock.average_buy_price, currentPrice: stock.current_price, exchange: 'US', backendId: stock.id, notes });
        } else if (type === 'nse') {
            const response = await fetch('/api/market/stocks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker, exchange: 'NSE', shares_owned: Number($('#asset-units').value), average_buy_price: Number($('#asset-buy').value), current_price: Number($('#asset-current').value) }) });
            if (!response.ok) throw new Error((await response.json()).detail || 'Could not save NSE stock');
            const stock = await response.json();
            const category = await ensureCategory('NSE Stocks', 'Equities');
            await saveLocalHolding({ name: stock.ticker, category, amount: stock.current_value, units: stock.shares_owned, buyPrice: stock.average_buy_price, currentPrice: stock.current_price, exchange: 'NSE', backendId: stock.id, notes });
        } else if (type === 'mmf') {
            const amount = Number($('#asset-amount').value);
            const response = await fetch('/api/market/mmfs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fund_name: name, current_principal_balance: amount }) });
            if (!response.ok) throw new Error((await response.json()).detail || 'Could not save MMF');
            await fetch('/api/market/mmfs/accrue', { method: 'POST' }).catch(() => null);
            const category = await ensureCategory('Money Market Fund', 'Fixed Income');
            await saveLocalHolding({ name, category, amount, notes });
        } else {
            const amount = Number($('#asset-amount').value);
            const categoryName = type === 'reit' ? 'REITs' : type === 'bond' ? 'Government Bonds' : type === 't-bill' ? 'Treasury Bills' : 'Cash & Bank';
            const category = await ensureCategory(categoryName, type === 'reit' ? 'Real Estate' : type === 'cash' ? 'Cash' : 'Fixed Income');
            await saveLocalHolding({ name, category, amount, notes, exchange: type === 'reit' ? 'NSE-REIT' : null });
        }
        closeModal();
        window.showToast?.('Asset added successfully');
        setTimeout(() => window.location.reload(), 250);
    } catch (error) { window.showToast?.(error.message || 'Could not add asset', 'error'); }
}

function openModal(type = null) {
    const modal = $('#asset-modal'); if (!modal) return;
    modal.hidden = false; document.body.classList.add('modal-open');
    $('#asset-type-grid').hidden = Boolean(type);
    if (type) buildForm(type);
}
function closeModal() { const modal = $('#asset-modal'); if (!modal) return; modal.hidden = true; document.body.classList.remove('modal-open'); }

function installDashboardModal() {
    const stockForm = $('#dashboard-stock-form');
    const mmfForm = $('#dashboard-mmf-form');
    if (!stockForm || !mmfForm) return;
    const card = stockForm.closest('.card');
    if (!card || card.dataset.enhanced) return;
    card.dataset.enhanced = 'true';
    const header = $('.card-header', card);
    if (header) header.innerHTML = `<div><h2 class="card-title">Add existing asset</h2><span class="text-muted">Choose the asset type first</span></div><button id="dashboard-add-asset" type="button" class="btn btn-primary">+ Add asset</button>`;
    $$('.tab-bar, #dashboard-stock-form, #dashboard-mmf-form', card).forEach(el => { el.hidden = true; });
    document.body.insertAdjacentHTML('beforeend', modalMarkup());
    $('#dashboard-add-asset').onclick = () => openModal();
    $('#asset-modal-close').onclick = closeModal;
    $('#asset-modal').addEventListener('click', e => { if (e.target.id === 'asset-modal') closeModal(); });
    $$('#asset-type-grid button').forEach(button => button.onclick = () => openModal(button.dataset.assetType));
}

function installTimestampBanner() {
    const section = $('#stocks-table-wrap')?.closest('.card');
    if (!section || $('#market-price-disclaimer')) return;
    const notice = document.createElement('div'); notice.id = 'market-price-disclaimer'; notice.className = 'notice market-disclaimer';
    notice.textContent = 'Market prices and MMF returns are estimates. Final statement values may differ because of applicable taxes, VAT where applicable, fees and charges.';
    section.insertBefore(notice, $('#stocks-table-wrap'));
}

function enhanceStockRows() {
    const body = $('#stocks-body');
    if (!body) return;
    [...body.rows].forEach(row => {
        const exchange = row.cells[1]?.textContent.trim();
        if (exchange === 'US' && row.cells[0] && !row.cells[0].querySelector('.market-badge')) row.cells[0].insertAdjacentHTML('beforeend', ' <span class="market-badge">US</span>');
        const updated = row.cells[9];
        if (updated && updated.dataset.formatted !== 'true') { const raw = updated.textContent.trim(); const date = Date.parse(raw); if (!Number.isNaN(date)) updated.textContent = asOf(date); updated.dataset.formatted = 'true'; }
    });
}

function addPagination(tableId, bodyId, pageSize = 10) {
    const table = $(`#${tableId}`); const body = $(`#${bodyId}`); if (!table || !body || body.dataset.pagination === 'true') return;
    body.dataset.pagination = 'true'; const wrap = table.closest('.table-wrapper') || table.parentElement; const controls = document.createElement('div'); controls.className = 'table-pagination'; wrap.after(controls);
    let page = 1;
    const render = () => { const rows = [...body.rows]; const pages = Math.max(1, Math.ceil(rows.length / pageSize)); page = Math.min(page, pages); rows.forEach((r, i) => { r.hidden = i < (page - 1) * pageSize || i >= page * pageSize; }); controls.innerHTML = `<span>Page ${page} of ${pages}</span><div><button type="button" class="btn btn-sm btn-secondary" ${page === 1 ? 'disabled' : ''} data-page="prev">Previous</button><button type="button" class="btn btn-sm btn-secondary" ${page === pages ? 'disabled' : ''} data-page="next">Next</button></div>`; controls.querySelector('[data-page="prev"]').onclick = () => { page--; render(); }; controls.querySelector('[data-page="next"]').onclick = () => { page++; render(); }; };
    new MutationObserver(() => render()).observe(body, { childList: true }); render();
}

function observeTables() {
    installTimestampBanner(); enhanceStockRows(); addPagination('stocks-table-wrap table', 'stocks-body', 10); addPagination('holdings-content table', 'holdings-body', 10);
    const body = $('#stocks-body'); if (body && !body.dataset.observed) { body.dataset.observed = 'true'; new MutationObserver(() => enhanceStockRows()).observe(body, { childList: true }); }
}

function init() {
    installDashboardModal(); installTimestampBanner(); observeTables();
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
    setTimeout(observeTables, 500); setTimeout(observeTables, 1500);
}

document.addEventListener('DOMContentLoaded', init);
