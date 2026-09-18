import Storage from './storage.js';
import API from './api.js';
import { formatMoney, totalInBase } from './ui.js';
import { nseCompanyName } from './nse_catalog.js';

const $ = id => document.getElementById(id);
const PAGE_SIZE = 10;
const pages = { stocks: 1, mmfs: 1, other: 1 };
let state = { stocks: [], mmfs: [], other: [] };

const money = (value, currency = Storage.getBaseCurrency()) => formatMoney(value, currency);

function paginate(items, key, renderItem) {
  const page = pages[key];
  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  pages[key] = Math.min(page, totalPages);
  const start = (pages[key] - 1) * PAGE_SIZE;
  const slice = items.slice(start, start + PAGE_SIZE);
  const list = $(key + '-list');
  list.replaceChildren();

  if (!items.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-state compact';
    empty.textContent = 'Nothing tracked yet.';
    list.append(empty);
  } else {
    slice.forEach(item => list.append(renderItem(item)));
  }

  const pager = $(key + '-pagination');
  pager.replaceChildren();
  if (totalPages > 1) {
    const prev = document.createElement('button');
    prev.className = 'btn btn-sm btn-secondary';
    prev.textContent = 'Previous';
    prev.disabled = pages[key] === 1;
    prev.onclick = () => { pages[key]--; paginate(items, key, renderItem); };

    const label = document.createElement('span');
    label.className = 'pagination-label';
    label.textContent = `Page ${pages[key]} of ${totalPages}`;

    const next = document.createElement('button');
    next.className = 'btn btn-sm btn-secondary';
    next.textContent = 'Next';
    next.disabled = pages[key] === totalPages;
    next.onclick = () => { pages[key]++; paginate(items, key, renderItem); };

    pager.append(prev, label, next);
  }
}

function assetRow({ title, subtitle, value, meta, positive }) {
  const item = document.createElement('div');
  item.className = 'asset-row';
  const left = document.createElement('div');
  const name = document.createElement('strong');
  name.textContent = title;
  const detail = document.createElement('small');
  detail.textContent = subtitle;
  left.append(name, detail);
  const right = document.createElement('div');
  right.className = 'asset-row-value';
  const amount = document.createElement('strong');
  amount.textContent = value;
  const note = document.createElement('small');
  note.className = positive === undefined ? '' : (positive ? 'text-positive' : 'text-negative');
  note.textContent = meta;
  right.append(amount, note);
  item.append(left, right);
  return item;
}

function renderAllocation(entries, total) {
  $('allocation-total').textContent = money(total);
  const donut = $('allocation-donut');
  if (!total) {
    donut.style.background = '';
    donut.textContent = 'No data';
    $('allocation-legend').replaceChildren();
    return;
  }

  let offset = 0;
  const palette = ['#0f766e','#14b8a6','#2563eb','#d97706','#7c3aed','#db2777','#475569','#0891b2'];
  donut.style.background = 'conic-gradient(' + entries.map(([name, value], i) => {
    const start = offset;
    offset += (value / total) * 100;
    return `${palette[i % palette.length]} ${start}% ${offset}%`;
  }).join(',') + ')';
  donut.textContent = '';

  const legend = $('allocation-legend');
  legend.replaceChildren(...entries.map(([name, value], i) => {
    const row = document.createElement('div');
    row.className = 'chart-legend-row';
    const label = document.createElement('span');
    const dot = document.createElement('i');
    dot.className = 'legend-dot';
    dot.style.background = palette[i % palette.length];
    label.append(dot, document.createTextNode(name));
    const amount = document.createElement('strong');
    amount.textContent = money(value);
    row.append(label, amount);
    return row;
  }));
}

function renderCashflow(income, expense, surplus) {
  const max = Math.max(income, expense, 1);
  $('cashflow-chart').replaceChildren(...[
    ['Income', income, 'income'],
    ['Expenses', expense, 'expense']
  ].map(([label, value, kind]) => {
    const row = document.createElement('div');
    row.className = 'bar-row';
    const caption = document.createElement('span');
    caption.textContent = label;
    const track = document.createElement('div');
    track.className = 'bar-track';
    const bar = document.createElement('span');
    bar.className = 'bar ' + kind;
    bar.style.width = `${(value / max) * 100}%`;
    track.append(bar);
    const amount = document.createElement('strong');
    amount.textContent = money(value);
    row.append(caption, track, amount);
    return row;
  }));
  $('cashflow-surplus').textContent = `Surplus ${money(surplus)}`;
  $('cashflow-surplus').className = surplus >= 0 ? 'text-positive' : 'text-negative';
}

function renderEmergency(current, essential) {
  const three = essential * 3;
  const six = essential * 6;
  const pct3 = three ? Math.min(100, current / three * 100) : 0;
  const pct6 = six ? Math.min(100, current / six * 100) : 0;

  $('emergency-value').textContent = money(current);
  $('emergency-note').textContent = essential ? `${pct3.toFixed(1)}% of 3 month target` : 'Add essential expenses in Budget';
  $('emergency-3m').textContent = money(three);
  $('emergency-6m').textContent = money(six);
  $('emergency-3m-bar').style.width = pct3 + '%';
  $('emergency-6m-bar').style.width = pct6 + '%';
  $('emergency-3m-pct').textContent = pct3.toFixed(1) + '% funded';
  $('emergency-6m-pct').textContent = pct6.toFixed(1) + '% funded';
  $('essential-monthly').textContent = money(essential);
  $('emergency-target-note').textContent = essential
    ? `Based on essential monthly expenses. Current fund: ${money(current)}.`
    : 'Mark expenses as essential in Budget to calculate the targets.';
}

async function renderDashboard() {
  const base = Storage.getBaseCurrency();
  const [stocks, mmfs, holdings, assets, liabilities, incomes, expenses, categories] = await Promise.all([
    API.getStocks(), API.getMMFAccounts(),
    Storage.getAll(Storage.STORES.holdings), Storage.getAll(Storage.STORES.assets),
    Storage.getAll(Storage.STORES.liabilities), Storage.getAll(Storage.STORES.income_sources),
    Storage.getAll(Storage.STORES.expenses), Storage.getAll(Storage.STORES.categories)
  ]);

  const categoryName = id => categories.find(c => c.id === id)?.name || 'Other';
  const excluded = new Set(['NSE Stocks', 'US Stocks', 'Money Market Fund']);
  const otherHoldings = holdings.filter(h => !excluded.has(categoryName(h.category_id)));
  const emergency = holdings.filter(h => categoryName(h.category_id) === 'Emergency Fund');

  const [stockValue, stockCost, mmfValue, mmfInterest, otherValue, emergencyValue, assetValue, liabilityValue, incomeValue, expenseValue, essentialValue] =
    await Promise.all([
      totalInBase(stocks.map(s => ({ amount: s.current_value, currency: s.currency || (s.exchange === 'US' ? 'USD' : 'KES') })), API),
      totalInBase(stocks.map(s => ({ amount: s.cost_basis, currency: s.currency || (s.exchange === 'US' ? 'USD' : 'KES') })), API),
      totalInBase(mmfs.map(m => ({ amount: m.current_balance, currency: 'KES' })), API),
      totalInBase(mmfs.map(m => ({ amount: m.total_interest_accrued, currency: 'KES' })), API),
      totalInBase(otherHoldings, API),
      totalInBase(emergency, API),
      totalInBase(assets, API), totalInBase(liabilities, API),
      totalInBase(incomes.filter(x => x.active !== false), API),
      totalInBase(expenses.filter(x => x.active !== false), API),
      totalInBase(expenses.filter(x => x.active !== false && x.essential), API)
    ]);

  const portfolio = stockValue + mmfValue + otherValue;
  const pl = stockValue - stockCost;
  const surplus = incomeValue - expenseValue;
  const networth = portfolio + assetValue - liabilityValue;

  $('portfolio-total').textContent = money(portfolio, base);
  $('portfolio-note').textContent = `${stocks.length + mmfs.length + otherHoldings.length} tracked investments · ${base}`;
  $('pl-total').textContent = money(pl, base);
  $('pl-total').className = 'metric-value ' + (pl >= 0 ? 'text-positive' : 'text-negative');
  $('pl-note').textContent = stockCost ? `${(pl / stockCost * 100).toFixed(2)}% on quoted positions` : 'No quoted market cost basis yet';
  $('interest-total').textContent = money(mmfInterest, base);
  $('interest-note').textContent = mmfs.length ? `${mmfs.length} account${mmfs.length === 1 ? '' : 's'} · compounded from investment date` : 'No MMF accounts';
  $('surplus-total').textContent = money(surplus, base);
  $('surplus-total').className = 'metric-value ' + (surplus >= 0 ? 'text-positive' : 'text-negative');
  $('surplus-note').textContent = `${money(incomeValue, base)} income · ${money(expenseValue, base)} expenses`;
  $('networth-total').textContent = money(networth, base);
  $('networth-note').textContent = `${money(assetValue, base)} assets · ${money(liabilityValue, base)} liabilities`;

  const usValue = await totalInBase(
    stocks.filter(s => s.exchange === 'US').map(s => ({ amount: s.current_value, currency: 'USD' })), API
  );
  const nseValue = stockValue - usValue;
  const allocation = [
    ['NSE Stocks', nseValue], ['US Stocks', usValue], ['MMFs', mmfValue], ['Other', otherValue]
  ].filter(([, value]) => value > 0);
  renderAllocation(allocation, allocation.reduce((sum, [, value]) => sum + value, 0));
  renderCashflow(incomeValue, expenseValue, surplus);
  renderEmergency(emergencyValue, essentialValue);

  state.stocks = stocks;
  state.mmfs = mmfs;
  state.other = [...otherHoldings, ...assets.map(a => ({ ...a, dashboardAsset: true }))];

  $('stocks-count').textContent = stocks.length;
  $('mmfs-count').textContent = mmfs.length;
  $('other-count').textContent = state.other.length;

  paginate(stocks, 'stocks', s => assetRow({
    title: s.exchange === 'NSE' ? s.ticker + ' · ' + nseCompanyName(s.ticker) : s.ticker,
    subtitle: `${s.exchange} · ${Number(s.shares_owned).toLocaleString()} shares`,
    value: money(s.current_value, s.exchange === 'US' ? 'USD' : 'KES'),
    meta: money(s.profit_loss, s.exchange === 'US' ? 'USD' : 'KES') + ' P/L',
    positive: s.profit_loss >= 0
  }));

  paginate(mmfs, 'mmfs', m => assetRow({
    title: m.short_name || m.fund_name,
    subtitle: (m.investment_date || 'Date not set') + ' · ' + (m.annual_yield_percentage || 0) + '% p.a.',
    value: money(m.current_balance, 'KES'),
    meta: money(m.total_interest_accrued, 'KES') + ' interest',
    positive: true
  }));

  paginate(state.other, 'other', item => assetRow({
    title: item.name,
    subtitle: item.dashboardAsset ? item.category : categoryName(item.category_id),
    value: money(item.amount, item.currency || base),
    meta: item.currency || base
  }));

  $('dashboard-updated').textContent = 'Updated ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

document.addEventListener('DOMContentLoaded', () => renderDashboard().catch(error => {
  $('dashboard-updated').textContent = error.message;
}));
