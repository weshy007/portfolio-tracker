import Storage from './storage.js';
import API from './api.js';
import { NSE_SECURITIES, NSE_STOCKS_BY_TICKER, nseCompanyName } from './nse_catalog.js';
import { amount, button, currencies, emptyState, formatMoney, formatPercent, row } from './ui.js';

const defaults = [
  ['NSE Stocks', 'Equities'], ['US Stocks', 'Equities'], ['Money Market Fund', 'Fixed Income'],
  ['REITs', 'Real Estate'], ['Government Bonds', 'Fixed Income'], ['Treasury Bills', 'Fixed Income'],
  ['Cash & Bank', 'Cash'], ['Emergency Fund', 'Safety'], ['SACCO', 'Other'], ['Pension', 'Retirement'],
  ['Business', 'Business'], ['Crypto', 'Alternative'], ['Other', 'Other']
];
let categories = [];
let institutions = [];
let stockCurrentPage = 1;
const STOCKS_PER_PAGE = 10;

const $ = id => document.getElementById(id);
const now = () => new Date().toISOString();
const money = (value, currency = Storage.getBaseCurrency()) => formatMoney(value, currency);

async function ensureCategories() {
  const existing = await Storage.getAll(Storage.STORES.categories);
  if (existing.length) return existing;
  await Promise.all(defaults.map(([name, category_type]) => Storage.setItem(Storage.STORES.categories, {
    id: crypto.randomUUID(), name, category_type, is_default: true, created_at: now()
  })));
  return Storage.getAll(Storage.STORES.categories);
}

function fillCurrencies() {
  const select = $('generic-currency');
  if (select) {
    select.replaceChildren();
    currencies.forEach(c => select.add(new Option(c, c)));
    select.value = Storage.getBaseCurrency();
  }
}

function fillNseDirectory() {
  const select = $('nse-ticker');
  if (select) {
    select.replaceChildren(new Option('Choose NSE security', ''));
    NSE_SECURITIES.slice().sort((a, b) => a.ticker.localeCompare(b.ticker)).forEach(stock => {
      const option = new Option(stock.ticker, stock.ticker);
      option.title = stock.name;
      select.add(option);
    });
  }
  const dir = $('nse-directory');
  if (dir) {
    dir.replaceChildren(...NSE_SECURITIES.slice().sort((a, b) => a.ticker.localeCompare(b.ticker)).map(stock => {
      const item = document.createElement('span');
      item.className = 'ticker-chip px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-xs font-mono font-semibold cursor-pointer hover:bg-teal-600 hover:text-white transition';
      item.textContent = stock.ticker;
      item.title = stock.name;
      return item;
    }));
  }
}

async function fillInstitutions() {
  institutions = await API.getInstitutions();
  const select = $('mmf-fund');
  if (select) {
    select.replaceChildren(new Option('Choose fund', ''));
    institutions.forEach(item => {
      const option = new Option(item.institution, item.fund_name);
      option.dataset.yield = item.yield_percentage;
      select.add(option);
    });
  }
}

function setAssetType(type) {
  $('asset-type').value = type;

  // Update button card styling
  document.querySelectorAll('.asset-card-btn').forEach(btn => {
    const isSelected = btn.dataset.type === type;
    btn.classList.toggle('border-teal-600', isSelected);
    btn.classList.toggle('bg-teal-50', isSelected);
    btn.classList.toggle('dark:bg-teal-900/20', isSelected);
    btn.classList.toggle('border-gray-200', !isSelected);
    btn.classList.toggle('dark:border-gray-700', !isSelected);
  });

  ['nse', 'us', 'mmf', 'generic'].forEach(name => {
    const el = $(name + '-fields');
    if (el) el.classList.toggle('hidden', name !== type);
  });

  const labels = { nse: 'NSE security', us: 'US ticker', mmf: 'Fund name', generic: 'Asset name' };
  if ($('holding-name')) {
    $('holding-name').placeholder = labels[type] || 'Asset name';
    $('holding-name').value = '';
  }
  if (type === 'nse' && $('generic-currency')) $('generic-currency').value = 'KES';
}

async function fetchPrice(ticker, exchange, target, statusId) {
  const symbol = String(ticker || '').trim().toUpperCase();
  if (!symbol) return;
  const status = $(statusId);
  if (status) status.textContent = 'Fetching…';
  try {
    const data = exchange === 'NSE'
      ? await API.getStockPrice(symbol, 'NSE')
      : await fetch('/api/us-market/quote?ticker=' + encodeURIComponent(symbol)).then(async r => {
          const d = await r.json();
          if (!r.ok) throw new Error(d.detail || 'Price lookup failed');
          return d;
        });
    $(target).value = data.price ?? data.current_price;
    if (status) status.textContent = 'Updated ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (error) {
    if (status) status.textContent = error.message;
    window.showToast?.(error.message, 'error');
  }
}

function renderUsPreview() {
  const invested = amount($('us-invested')?.value);
  const buy = amount($('us-buy')?.value);
  const sharesInput = amount($('us-shares')?.value);
  const box = $('us-shares-preview');
  if (!box) return;

  let shares = 0;
  if (invested > 0 && buy > 0) shares = invested / buy;
  else if (sharesInput > 0) shares = sharesInput;

  if (shares > 0 && buy > 0) {
    box.classList.remove('hidden');
    box.textContent = `${shares.toFixed(6)} shares at ${money(buy, 'USD')} per share (${money(shares * buy, 'USD')} total)`;
  } else box.classList.add('hidden');
}

function renderHoldingForm() {
  const type = $('asset-type').value;
  if (type === 'nse') {
    const ticker = $('nse-ticker').value;
    const stock = NSE_STOCKS_BY_TICKER[ticker];
    if (stock) {
      $('holding-name').value = stock.ticker;
      if ($('nse-company')) $('nse-company').textContent = stock.name + ' · ' + stock.sector;
    }
  }
  if (type === 'mmf') {
    const option = $('mmf-fund').selectedOptions[0];
    if (option?.value) {
      $('holding-name').value = option.value;
      if ($('mmf-yield')) $('mmf-yield').value = option.dataset.yield ? option.dataset.yield + '% p.a.' : '—';
    }
  }
}

async function saveStock(type) {
  if (type === 'nse') {
    const ticker = $('nse-ticker').value, units = amount($('stock-units').value), buy = amount($('stock-buy').value);
    const current = amount($('stock-current').value) || buy;
    if (!ticker || !units || !buy) throw new Error('Ticker, shares and average buy price are required.');
    const data = await API.createStock({ ticker, exchange: 'NSE', shares_owned: units, average_buy_price: buy, current_price: current });
    const category = categories.find(c => c.name === 'NSE Stocks') || categories[0];
    await Storage.setItem(Storage.STORES.holdings, {
      id: crypto.randomUUID(), name: ticker, category_id: category?.id, amount: data.current_value,
      currency: 'KES', units: data.shares_owned, average_buy_price: data.average_buy_price,
      current_price: data.current_price, exchange: 'NSE', backend_stock_id: data.id,
      notes: $('holding-notes').value.trim(), created_at: now(), updated_at: now()
    });
    return;
  }

  const ticker = $('us-ticker').value.trim().toUpperCase();
  const buy = amount($('us-buy').value);
  const invested = amount($('us-invested').value);
  const sharesInput = amount($('us-shares').value);
  const currentPrice = amount($('us-current').value);

  let shares = 0;
  if (invested > 0 && buy > 0) shares = invested / buy;
  else if (sharesInput > 0) shares = sharesInput;

  if (!ticker || shares <= 0 || buy <= 0) {
    throw new Error('US ticker, buy price, and shares or amount invested are required.');
  }

  const payload = {
    ticker,
    exchange: 'US',
    shares_owned: shares,
    average_buy_price: buy,
    ...(currentPrice > 0 ? { current_price: currentPrice } : {})
  };

  const data = await fetch('/api/us-market/stocks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(async r => {
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Could not save US stock position');
    return d;
  });

  const category = categories.find(c => c.name === 'US Stocks') || categories[0];
  await Storage.setItem(Storage.STORES.holdings, {
    id: crypto.randomUUID(), name: ticker, category_id: category?.id, amount: data.current_value,
    currency: 'USD', units: data.shares_owned, average_buy_price: data.average_buy_price,
    current_price: data.current_price, exchange: 'US', backend_stock_id: data.id,
    notes: $('holding-notes').value.trim(), created_at: now(), updated_at: now()
  });
}

async function saveMMF() {
  const fund = $('mmf-fund').value || $('holding-name').value.trim();
  const amountValue = amount($('mmf-amount').value);
  const investmentDate = $('mmf-date').value || new Date().toISOString().split('T')[0];

  if (!fund || amountValue <= 0) throw new Error('Fund name and positive initial deposit amount are required.');

  let data;
  try {
    data = await API.createMMFAccount({ fund_name: fund, current_principal_balance: amountValue, investment_date: investmentDate });
  } catch (err) {
    console.warn('Backend MMF creation fallback:', err);
    data = { id: crypto.randomUUID(), fund_name: fund, current_balance: amountValue };
  }

  const category = categories.find(c => c.name === 'Money Market Fund') || categories[0];
  await Storage.setItem(Storage.STORES.holdings, {
    id: crypto.randomUUID(), name: fund, category_id: category?.id, amount: amountValue,
    currency: 'KES', backend_mmf_id: data.id, notes: $('holding-notes').value.trim(),
    created_at: now(), updated_at: now()
  });
}

async function saveGeneric(type) {
  const value = amount($('generic-value').value);
  const name = $('holding-name').value.trim();
  const selectedCatId = $('generic-category')?.value;

  if (!name || value <= 0) throw new Error('Asset name and positive estimated value are required.');

  const category = categories.find(c => c.id === selectedCatId) || categories.find(c => c.name === 'Other') || categories[0];
  await Storage.setItem(Storage.STORES.holdings, {
    id: crypto.randomUUID(), name, category_id: category?.id, amount: value,
    currency: $('generic-currency')?.value || Storage.getBaseCurrency(), notes: $('holding-notes').value.trim(),
    created_at: now(), updated_at: now()
  });
}

async function submitHolding(event) {
  event.preventDefault();
  const type = $('asset-type').value;
  try {
    if (type === 'nse' || type === 'us') await saveStock(type);
    else if (type === 'mmf') await saveMMF();
    else await saveGeneric(type);
    event.currentTarget.reset();
    setAssetType('nse');
    await render();
    window.showToast?.('Holding added successfully.');
  } catch (error) { window.showToast?.(error.message, 'error'); }
}

async function deleteHolding(holding) {
  if (!confirm('Delete ' + holding.name + '?')) return;
  await Storage.deleteItem(Storage.STORES.holdings, holding.id);
  if (holding.backend_stock_id) try { await API.deleteStock(holding.backend_stock_id); } catch { }
  if (holding.backend_mmf_id) try { await API.deleteMMFAccount(holding.backend_mmf_id); } catch { }
  render();
}

async function renderHoldings() {
  const holdings = await Storage.getAll(Storage.STORES.holdings);
  const filter = $('category-filter').value;
  const visible = filter ? holdings.filter(h => h.category_id === filter) : holdings;
  const body = $('holdings-body');
  body.replaceChildren();

  visible.forEach(h => {
    const category = categories.find(c => c.id === h.category_id);
    const pl = (h.units && h.average_buy_price && h.current_price) ? (h.units * h.current_price) - (h.units * h.average_buy_price) : null;
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50';

    const exchangeBadge = h.exchange === 'US'
      ? `<span class="ml-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">US</span>`
      : h.exchange === 'NSE'
        ? `<span class="ml-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300">NSE</span>`
        : '';

    tr.innerHTML = `
      <td class="py-2.5 px-3 font-semibold text-gray-900 dark:text-white">${h.name} ${exchangeBadge}</td>
      <td class="py-2.5 px-3 text-gray-500">${category?.name || 'Unknown'}</td>
      <td class="py-2.5 px-3 text-right font-mono">${h.units ? Number(h.units).toLocaleString(undefined, { maximumFractionDigits: 4 }) : '—'}</td>
      <td class="py-2.5 px-3 text-right font-mono font-bold">${money(h.amount, h.currency)}</td>
      <td class="py-2.5 px-3 text-right font-mono font-semibold ${pl !== null ? (pl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400') : ''}">
        ${pl !== null ? money(pl, h.currency) : '—'}
      </td>
      <td class="py-2.5 px-3 font-mono font-semibold text-gray-400">${h.currency}</td>
      <td class="py-2.5 px-3 text-right"></td>
    `;

    const actionTd = tr.cells[tr.cells.length - 1];
    actionTd.appendChild(button('Delete', 'px-2 py-1 bg-rose-50 hover:bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 text-xs font-semibold rounded', () => deleteHolding(h)));
    body.appendChild(tr);
  });

  $('holdings-wrap').hidden = !visible.length;
  if (!visible.length) emptyState($('holdings-empty'), 'No holdings recorded.', 'Add your first asset above.');
  else $('holdings-empty').replaceChildren();

  return holdings;
}

async function renderAllocation(holdings) {
  if (!holdings.length) {
    $('allocation-content').hidden = true;
    emptyState($('allocation-empty'), 'No allocation data.', 'Add holdings to view breakdown.');
    return;
  }
  const values = await Promise.all(holdings.map(async h => ({
    name: categories.find(c => c.id === h.category_id)?.name || 'Other',
    value: await totalInBase([h], API)
  })));

  const map = new Map();
  values.forEach(({ name, value }) => map.set(name, (map.get(name) || 0) + value));
  const entries = [...map.entries()].sort((a, b) => b[1] - a[1]), total = entries.reduce((s, [, v]) => s + v, 0);
  const colors = ['#0f766e', '#14b8a6', '#d97706', '#2563eb', '#7c3aed', '#db2777', '#475569'];

  let offset = 0;
  $('allocation-chart').style.background = 'conic-gradient(' + entries.map(([name, value], i) => {
    const start = offset;
    offset += total ? value / total * 100 : 0;
    return colors[i % colors.length] + ' ' + start + '% ' + offset + '%';
  }).join(',') + ')';
  $('allocation-total').textContent = money(total);

  const legend = $('allocation-legend');
  legend.replaceChildren(...entries.map(([name, value], i) => {
    const item = document.createElement('div');
    item.className = 'flex items-center justify-between py-1 border-b border-gray-100 dark:border-gray-700/50';
    item.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full" style="background:${colors[i % colors.length]}"></span>
        <span class="font-semibold text-gray-700 dark:text-gray-300">${name}</span>
      </div>
      <strong class="font-mono text-gray-900 dark:text-white">${money(value)} (${total ? ((value / total) * 100).toFixed(0) : 0}%)</strong>
    `;
    return item;
  }));

  $('allocation-content').hidden = false;
  $('allocation-empty').replaceChildren();
}

async function renderMarketTables() {
  const [stocks, mmfs] = await Promise.all([API.getStocks(), API.getMMFAccounts()]);

  // Paginated Stocks Table
  const stockBody = $('stocks-body');
  stockBody.replaceChildren();

  const totalStockPages = Math.ceil(stocks.length / STOCKS_PER_PAGE) || 1;
  stockCurrentPage = Math.min(stockCurrentPage, totalStockPages);
  const startIdx = (stockCurrentPage - 1) * STOCKS_PER_PAGE;
  const pageStocks = stocks.slice(startIdx, startIdx + STOCKS_PER_PAGE);

  pageStocks.forEach(s => {
    const currency = s.currency || (s.exchange === 'US' ? 'USD' : 'KES');
    const pl = s.profit_loss || 0;
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50';

    const exchangeBadge = s.exchange === 'US'
      ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">US Stock</span>`
      : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300">NSE Kenya</span>`;

    tr.innerHTML = `
      <td class="py-2.5 px-3 font-bold font-mono text-gray-900 dark:text-white">${s.ticker}</td>
      <td class="py-2.5 px-3">${exchangeBadge}</td>
      <td class="py-2.5 px-3 text-right font-mono">${Number(s.shares_owned).toLocaleString(undefined, { maximumFractionDigits: 6 })}</td>
      <td class="py-2.5 px-3 text-right font-mono">${money(s.average_buy_price, currency)}</td>
      <td class="py-2.5 px-3 text-right font-mono font-bold">${money(s.current_price, currency)}</td>
      <td class="py-2.5 px-3 text-right font-mono font-bold">${money(s.current_value, currency)}</td>
      <td class="py-2.5 px-3 text-right font-mono font-semibold ${pl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">
        ${money(pl, currency)} (${formatPercent(s.profit_loss_percentage || 0)})
      </td>
      <td class="py-2.5 px-3 text-gray-400">${s.price_updated_at ? new Date(s.price_updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</td>
      <td class="py-2.5 px-3 text-right"></td>
    `;
    const actionTd = tr.cells[tr.cells.length - 1];
    actionTd.appendChild(button('Delete', 'px-2 py-1 bg-rose-50 hover:bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 text-xs font-semibold rounded', async () => {
      await API.deleteStock(s.id);
      await render();
    }));
    stockBody.appendChild(tr);
  });

  $('stocks-wrap').hidden = !stocks.length;
  if (!stocks.length) emptyState($('stocks-empty'), 'No stock positions.', 'Add an NSE or US stock above.');
  else $('stocks-empty').replaceChildren();

  // Render Stocks Pagination Controls
  const pagDiv = $('stocks-pagination');
  if (pagDiv) {
    if (stocks.length > STOCKS_PER_PAGE) {
      pagDiv.innerHTML = `
        <span>Showing ${startIdx + 1}–${Math.min(startIdx + STOCKS_PER_PAGE, stocks.length)} of ${stocks.length} stocks</span>
        <div class="flex items-center gap-2">
          <button id="prev-stock-page" class="px-3 py-1 bg-slate-100 dark:bg-slate-700 rounded ${stockCurrentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}" ${stockCurrentPage === 1 ? 'disabled' : ''}>Previous</button>
          <span>Page ${stockCurrentPage} of ${totalStockPages}</span>
          <button id="next-stock-page" class="px-3 py-1 bg-slate-100 dark:bg-slate-700 rounded ${stockCurrentPage === totalStockPages ? 'opacity-50 cursor-not-allowed' : ''}" ${stockCurrentPage === totalStockPages ? 'disabled' : ''}>Next</button>
        </div>
      `;
      $('prev-stock-page')?.addEventListener('click', () => { if (stockCurrentPage > 1) { stockCurrentPage--; renderMarketTables(); } });
      $('next-stock-page')?.addEventListener('click', () => { if (stockCurrentPage < totalStockPages) { stockCurrentPage++; renderMarketTables(); } });
    } else {
      pagDiv.innerHTML = `<span>${stocks.length} stock position${stocks.length === 1 ? '' : 's'} tracked</span>`;
    }
  }

  // MMF Table
  const mmfBody = $('mmf-body');
  mmfBody.replaceChildren();
  mmfs.forEach(m => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50';
    tr.innerHTML = `
      <td class="py-2.5 px-3 font-semibold text-gray-900 dark:text-white">${m.short_name || m.fund_name}</td>
      <td class="py-2.5 px-3 text-gray-500">${m.investment_date || '—'}</td>
      <td class="py-2.5 px-3 text-right font-mono">${money(m.principal_balance, 'KES')}</td>
      <td class="py-2.5 px-3 text-right font-mono font-bold">${money(m.current_balance, 'KES')}</td>
      <td class="py-2.5 px-3 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">+${money(m.total_interest_accrued, 'KES')}</td>
      <td class="py-2.5 px-3 text-right font-mono font-semibold text-indigo-600">${m.annual_yield_percentage}%</td>
      <td class="py-2.5 px-3 text-right font-mono text-gray-500">${money(m.today_estimated_interest, 'KES')}</td>
      <td class="py-2.5 px-3 text-gray-400">${m.last_accrued_on || '—'}</td>
      <td class="py-2.5 px-3 text-right"></td>
    `;
    const actionTd = tr.cells[tr.cells.length - 1];
    actionTd.appendChild(button('Delete', 'px-2 py-1 bg-rose-50 hover:bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 text-xs font-semibold rounded', async () => {
      await API.deleteMMFAccount(m.id);
      await render();
    }));
    mmfBody.appendChild(tr);
  });
  $('mmf-wrap').hidden = !mmfs.length;
  if (!mmfs.length) emptyState($('mmf-empty'), 'No MMF accounts.', 'Add a money market fund above.');
  else $('mmf-empty').replaceChildren();
}

function fillGenericCategories() {
  const select = $('generic-category');
  if (select && categories.length) {
    select.replaceChildren();
    categories.forEach(c => select.add(new Option(c.name, c.id)));
  }
}

async function render() {
  categories = await ensureCategories();
  fillCurrencies();
  fillGenericCategories();
  const select = $('category-filter'), previous = select ? select.value : '';
  if (select) {
    select.replaceChildren(new Option('All categories', ''), ...categories.map(c => new Option(c.name, c.id)));
    select.value = previous;
  }
  await renderHoldings().then(renderAllocation);
  await renderMarketTables();
}

// Setup Asset Type Card Listeners
document.querySelectorAll('.asset-card-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const type = e.currentTarget.dataset.type;
    setAssetType(type);
  });
});

$('nse-ticker')?.addEventListener('change', () => { renderHoldingForm(); fetchPrice($('nse-ticker').value, 'NSE', 'stock-current', 'nse-price-status'); });
$('mmf-fund')?.addEventListener('change', renderHoldingForm);
$('fetch-nse-price')?.addEventListener('click', () => fetchPrice($('nse-ticker').value, 'NSE', 'stock-current', 'nse-price-status'));
$('fetch-us-price')?.addEventListener('click', () => fetchPrice($('us-ticker').value, 'US', 'us-current', 'us-price-status'));

$('us-invested')?.addEventListener('input', () => {
  const invested = amount($('us-invested').value);
  const buy = amount($('us-buy').value);
  if (invested > 0 && buy > 0) {
    $('us-shares').value = (invested / buy).toFixed(6);
  }
  renderUsPreview();
});

$('us-shares')?.addEventListener('input', () => {
  const shares = amount($('us-shares').value);
  const buy = amount($('us-buy').value);
  if (shares > 0 && buy > 0) {
    $('us-invested').value = (shares * buy).toFixed(2);
  }
  renderUsPreview();
});

$('us-buy')?.addEventListener('input', () => {
  const buy = amount($('us-buy').value);
  const invested = amount($('us-invested').value);
  const shares = amount($('us-shares').value);
  if (invested > 0 && buy > 0) {
    $('us-shares').value = (invested / buy).toFixed(6);
  } else if (shares > 0 && buy > 0) {
    $('us-invested').value = (shares * buy).toFixed(2);
  }
  renderUsPreview();
});

$('holding-form')?.addEventListener('submit', submitHolding);
$('category-filter')?.addEventListener('change', render);

$('refresh-stocks')?.addEventListener('click', async () => {
  try {
    const results = await Promise.allSettled([API.refreshAllStocks(), API.refreshAllUSStocks()]);
    const failed = results.filter(r => r.status === 'rejected');
    await render();
    window.showToast?.(failed.length ? 'Some quotes could not be refreshed.' : 'Market quotes refreshed!');
  } catch (e) { window.showToast?.(e.message, 'error'); }
});

$('scrape-yields')?.addEventListener('click', async () => {
  try { await API.scrapeMMFYields(); await render(); window.showToast?.('Daily MMF yields updated.'); }
  catch (e) { window.showToast?.(e.message, 'error'); }
});

$('accrue-mmf')?.addEventListener('click', async () => {
  try { await API.accrueMMF(); await render(); window.showToast?.('Completed MMF interest accrued!'); }
  catch (e) { window.showToast?.(e.message, 'error'); }
});

fillNseDirectory();
fillInstitutions().catch(() => { });
render().catch(error => emptyState($('holdings-empty'), 'Portfolio unavailable', error.message));
