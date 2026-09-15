const q = (s, r = document) => r.querySelector(s);
const qa = (s, r = document) => [...r.querySelectorAll(s)];

function paginate(bodyId, pageSize = 10) {
    const body = q(`#${bodyId}`); if (!body || body.dataset.fixedPagination) return;
    body.dataset.fixedPagination = 'true';
    const wrap = body.closest('.table-wrapper'); if (!wrap) return;
    const controls = document.createElement('div'); controls.className = 'table-pagination'; wrap.after(controls);
    let page = 1;
    const render = () => {
        const rows = [...body.rows];
        const pages = Math.max(1, Math.ceil(rows.length / pageSize));
        page = Math.max(1, Math.min(page, pages));
        rows.forEach((row, index) => { row.hidden = index < (page - 1) * pageSize || index >= page * pageSize; });
        controls.innerHTML = `<span>Page ${page} of ${pages} · ${rows.length} items</span><div><button type="button" class="btn btn-sm btn-secondary" data-p="prev" ${page === 1 ? 'disabled' : ''}>Previous</button><button type="button" class="btn btn-sm btn-secondary" data-p="next" ${page === pages ? 'disabled' : ''}>Next</button></div>`;
        q('[data-p="prev"]', controls).onclick = () => { page -= 1; render(); };
        q('[data-p="next"]', controls).onclick = () => { page += 1; render(); };
    };
    new MutationObserver(render).observe(body, { childList: true });
    render();
}

async function decoratePortfolioStocks() {
    const body = q('#holdings-body'); if (!body) return;
    try {
        const response = await fetch('/api/market/stocks'); if (!response.ok) return;
        const stocks = await response.json();
        const byTicker = new Map(stocks.map(stock => [stock.ticker, stock]));
        [...body.rows].forEach(row => {
            const ticker = row.cells[0]?.textContent.trim().split(/\s+/)[0];
            const stock = byTicker.get(ticker);
            if (!stock) return;
            const category = row.cells[1];
            const current = row.cells[4];
            if (stock.exchange === 'US') {
                if (category) category.innerHTML = 'US Stocks <span class="market-badge">USD</span>';
                if (current) current.title = stock.price_updated_at ? `Price ${new Date(stock.price_updated_at).toLocaleString()}` : 'Yahoo Finance price';
            } else if (category && /US Stocks/i.test(category.textContent)) {
                category.textContent = 'NSE Stocks';
            }
        });
    } catch { /* UI enhancement is non-blocking */ }
}

function installUsPriceFetcher() {
    const observer = new MutationObserver(() => {
        const ticker = q('#asset-ticker'); const current = q('#asset-current');
        if (!ticker || !current || ticker.tagName === 'SELECT' || ticker.dataset.yahooFetcher) return;
        ticker.dataset.yahooFetcher = 'true';
        const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-sm btn-secondary'; button.textContent = '⚡ Fetch Yahoo price'; button.style.marginBottom = '.25rem';
        const parent = current.closest('.form-group'); const label = parent?.querySelector('label');
        if (label?.parentElement) label.parentElement.appendChild(button);
        button.onclick = async () => {
            const symbol = ticker.value.trim().toUpperCase(); if (!symbol) return;
            button.disabled = true; button.textContent = 'Fetching…';
            try { const response = await fetch(`/api/us-market/quote?ticker=${encodeURIComponent(symbol)}`); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Yahoo Finance lookup failed'); current.value = data.current_price; button.textContent = `Yahoo: $${Number(data.current_price).toFixed(2)}`; }
            catch (error) { button.textContent = 'Fetch failed'; window.showToast?.(error.message, 'error'); }
            finally { button.disabled = false; }
        };
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

function initFixes() {
    paginate('stocks-body', 10); paginate('holdings-body', 10); decoratePortfolioStocks(); installUsPriceFetcher();
    setTimeout(() => { paginate('stocks-body', 10); paginate('holdings-body', 10); decoratePortfolioStocks(); }, 800);
    setTimeout(() => { paginate('stocks-body', 10); paginate('holdings-body', 10); decoratePortfolioStocks(); }, 1800);
}

document.addEventListener('DOMContentLoaded', initFixes);
