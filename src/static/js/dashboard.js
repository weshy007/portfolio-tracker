import Storage from './storage.js';
import API from './api.js';
import { formatMoney, totalInBase } from './ui.js';

const $ = id => document.getElementById(id);

function renderPositionsDetailModal(stocks, mmfs, holdings, categories, base) {
  const detailBody = $('detail-positions-body');
  if (!detailBody) return;
  detailBody.innerHTML = '';

  const rows = [];

  stocks.forEach(s => {
    const currency = s.currency || (s.exchange === 'US' ? 'USD' : 'KES');
    const pl = s.profit_loss || 0;
    const plPct = s.profit_loss_percentage || 0;
    rows.push({
      name: s.ticker,
      type: s.exchange === 'US' ? 'US Stock' : 'NSE Stock',
      shares: Number(s.shares_owned).toLocaleString(undefined, { maximumFractionDigits: 6 }),
      buyPrice: formatMoney(s.average_buy_price, currency),
      currPrice: formatMoney(s.current_price, currency),
      costBasis: formatMoney(s.cost_basis, currency),
      marketValue: formatMoney(s.current_value, currency),
      plHtml: `<span class="${pl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">${pl >= 0 ? '+' : ''}${formatMoney(pl, currency)} (${plPct >= 0 ? '+' : ''}${plPct.toFixed(2)}%)</span>`
    });
  });

  mmfs.forEach(m => {
    rows.push({
      name: m.short_name || m.fund_name,
      type: 'MMF Fund',
      shares: '—',
      buyPrice: '—',
      currPrice: `${m.annual_yield_percentage}% p.a.`,
      costBasis: formatMoney(m.principal_balance, 'KES'),
      marketValue: formatMoney(m.current_balance, 'KES'),
      plHtml: `<span class="text-emerald-600 dark:text-emerald-400">+${formatMoney(m.total_interest_accrued, 'KES')} Interest</span>`
    });
  });

  const excludedCategoryNames = new Set(['NSE Stocks', 'US Stocks', 'Money Market Fund']);
  holdings.forEach(h => {
    const catName = categories.find(c => c.id === h.category_id)?.name || 'Other';
    if (excludedCategoryNames.has(catName)) return;

    const currency = h.currency || base;
    const shares = h.units ? Number(h.units).toLocaleString(undefined, { maximumFractionDigits: 6 }) : '—';
    const buyPrice = h.average_buy_price ? formatMoney(h.average_buy_price, currency) : '—';
    const currPrice = h.current_price ? formatMoney(h.current_price, currency) : '—';
    const costBasis = (h.units && h.average_buy_price) ? formatMoney(h.units * h.average_buy_price, currency) : formatMoney(h.amount, currency);
    const marketValue = formatMoney(h.amount, currency);

    let plHtml = '—';
    if (h.units && h.average_buy_price && h.current_price) {
      const pl = (h.units * h.current_price) - (h.units * h.average_buy_price);
      plHtml = `<span class="${pl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">${pl >= 0 ? '+' : ''}${formatMoney(pl, currency)}</span>`;
    }

    rows.push({
      name: h.name,
      type: catName,
      shares,
      buyPrice,
      currPrice,
      costBasis,
      marketValue,
      plHtml
    });
  });

  if (rows.length === 0) {
    detailBody.innerHTML = `<tr><td colspan="8" class="py-8 text-center text-slate-400">No active positions found in portfolio.</td></tr>`;
  } else {
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50';
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-bold text-slate-900 dark:text-white font-sans">${r.name}</td>
        <td class="py-2.5 px-3 font-sans"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">${r.type}</span></td>
        <td class="py-2.5 px-3 text-right font-mono">${r.shares}</td>
        <td class="py-2.5 px-3 text-right font-mono">${r.buyPrice}</td>
        <td class="py-2.5 px-3 text-right font-mono font-semibold text-slate-900 dark:text-white">${r.currPrice}</td>
        <td class="py-2.5 px-3 text-right font-mono text-slate-500">${r.costBasis}</td>
        <td class="py-2.5 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">${r.marketValue}</td>
        <td class="py-2.5 px-3 text-right font-mono font-semibold">${r.plHtml}</td>
      `;
      detailBody.appendChild(tr);
    });
  }

  if ($('detail-modal-summary')) {
    $('detail-modal-summary').textContent = `Total active positions tracked: ${rows.length}`;
  }
}

async function renderDashboard() {
  const base = Storage.getBaseCurrency();
  const [stocks, mmfs, holdings, assets, liabilities, incomes, expenses, categories] = await Promise.all([
    API.getStocks(),
    API.getMMFAccounts(),
    Storage.getAll(Storage.STORES.holdings),
    Storage.getAll(Storage.STORES.assets),
    Storage.getAll(Storage.STORES.liabilities),
    Storage.getAll(Storage.STORES.income_sources),
    Storage.getAll(Storage.STORES.expenses),
    Storage.getAll(Storage.STORES.categories)
  ]);

  const excluded = new Set(['NSE Stocks', 'US Stocks', 'Money Market Fund']);
  const other = holdings.filter(h => !excluded.has(categories.find(c => c.id === h.category_id)?.name));

  const [stockValue, stockCost, mmfValue, mmfInterest, otherValue, assetValue, liabilityValue, incomeValue, expenseValue] = await Promise.all([
    totalInBase(stocks.map(s => ({ amount: s.current_value, currency: s.currency || 'KES' })), API),
    totalInBase(stocks.map(s => ({ amount: s.cost_basis, currency: s.currency || 'KES' })), API),
    totalInBase(mmfs.map(m => ({ amount: m.current_balance, currency: 'KES' })), API),
    totalInBase(mmfs.map(m => ({ amount: m.total_interest_accrued, currency: 'KES' })), API),
    totalInBase(other, API),
    totalInBase(assets, API),
    totalInBase(liabilities, API),
    totalInBase(incomes.filter(x => x.active !== false), API),
    totalInBase(expenses.filter(x => x.active !== false), API)
  ]);

  const portfolio = stockValue + mmfValue + otherValue;
  const cost = stockCost + otherValue;
  const pl = stockValue - stockCost;
  const surplus = incomeValue - expenseValue;
  const networth = portfolio + assetValue - liabilityValue;

  // Headline Cards
  if ($('portfolio-total')) $('portfolio-total').textContent = formatMoney(portfolio, base);
  if ($('portfolio-note')) $('portfolio-note').textContent = `${stocks.length + mmfs.length + holdings.length} tracked positions · ${base}`;
  if ($('cost-total')) $('cost-total').textContent = formatMoney(cost, base);
  
  if ($('pl-total')) {
    $('pl-total').textContent = formatMoney(pl, base);
    $('pl-total').className = 'text-2xl font-bold font-mono block mb-1 ' + (pl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400');
  }
  if ($('pl-note')) $('pl-note').textContent = stockCost ? ((pl / stockCost) * 100).toFixed(2) + '% on market positions' : 'No quoted market cost basis yet';

  if ($('interest-total')) $('interest-total').textContent = formatMoney(mmfInterest, base);
  if ($('interest-note')) $('interest-note').textContent = mmfs.length ? `${mmfs.length} MMF account${mmfs.length === 1 ? '' : 's'}` : 'No MMF accounts';

  if ($('surplus-total')) {
    $('surplus-total').textContent = formatMoney(surplus, base);
    $('surplus-total').className = 'text-2xl font-bold font-mono block mb-1 ' + (surplus >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400');
  }
  if ($('surplus-note')) $('surplus-note').textContent = incomeValue ? formatMoney(incomeValue, base) + ' income · ' + formatMoney(expenseValue, base) + ' expenses' : 'Add income in Budget';

  if ($('networth-total')) $('networth-total').textContent = formatMoney(networth, base);
  if ($('networth-note')) $('networth-note').textContent = `${formatMoney(assetValue, base)} assets · ${formatMoney(liabilityValue, base)} liabilities`;

  // Allocation Stacked Bar Calculation
  if ($('allocation-stacked-bar')) {
    const totalAlloc = portfolio || 1;
    const stocksPct = (stockValue / totalAlloc) * 100;
    const mmfPct = (mmfValue / totalAlloc) * 100;
    const otherPct = (otherValue / totalAlloc) * 100;

    const barChildren = $('allocation-stacked-bar').children;
    if (barChildren[0]) barChildren[0].style.width = stocksPct.toFixed(1) + '%';
    if (barChildren[1]) barChildren[1].style.width = mmfPct.toFixed(1) + '%';
    if (barChildren[2]) barChildren[2].style.width = otherPct.toFixed(1) + '%';

    if ($('alloc-stocks-val')) $('alloc-stocks-val').textContent = `${formatMoney(stockValue, base)} (${stocksPct.toFixed(0)}%)`;
    if ($('alloc-mmf-val')) $('alloc-mmf-val').textContent = `${formatMoney(mmfValue, base)} (${mmfPct.toFixed(0)}%)`;
    if ($('alloc-other-val')) $('alloc-other-val').textContent = `${formatMoney(otherValue, base)} (${otherPct.toFixed(0)}%)`;
  }

  // Financial Health Checks
  if ($('health-savings-rate')) {
    const savingsRate = incomeValue > 0 ? Math.max(0, (surplus / incomeValue) * 100) : 0;
    $('health-savings-rate').textContent = savingsRate.toFixed(1) + '%';
    if ($('health-savings-bar')) $('health-savings-bar').style.width = Math.min(100, savingsRate) + '%';
  }

  if ($('health-emergency-months')) {
    const essentialExpenses = expenses.filter(x => x.essential && x.active !== false);
    const essentialTotal = await totalInBase(essentialExpenses, API);
    const emergencyMonths = essentialTotal > 0 ? (mmfValue / essentialTotal) : 0;
    $('health-emergency-months').textContent = emergencyMonths.toFixed(1) + ' mos';
  }

  if ($('health-debt-ratio')) {
    const totalAssets = portfolio + assetValue;
    const debtRatio = totalAssets > 0 ? (liabilityValue / totalAssets) * 100 : 0;
    $('health-debt-ratio').textContent = debtRatio.toFixed(1) + '%';
  }

  // Quick Active Positions Table
  if ($('quick-positions-body')) {
    const positionsBody = $('quick-positions-body');
    positionsBody.innerHTML = '';

    const allPositions = [
      ...stocks.map(s => ({
        name: `${s.ticker} (${s.exchange || 'NSE'})`,
        type: s.exchange === 'US' ? 'US Stock' : 'NSE Stock',
        value: s.current_value,
        sub: s.profit_loss >= 0 ? `+${formatMoney(s.profit_loss, s.currency || (s.exchange === 'US' ? 'USD' : 'KES'))}` : formatMoney(s.profit_loss, s.currency || (s.exchange === 'US' ? 'USD' : 'KES')),
        isPositive: (s.profit_loss || 0) >= 0
      })),
      ...mmfs.map(m => ({
        name: m.fund_name,
        type: 'MMF Fund',
        value: m.current_balance,
        sub: `+${formatMoney(m.total_interest_accrued, 'KES')} interest`,
        isPositive: true
      }))
    ];

    if (allPositions.length === 0) {
      positionsBody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-gray-400">No active stock or MMF holdings added yet. Click "+ Add Holding" above.</td></tr>`;
    } else {
      allPositions.slice(0, 5).forEach(pos => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer';
        tr.innerHTML = `
          <td class="py-2.5 px-3 font-semibold text-gray-900 dark:text-white">${pos.name}</td>
          <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">${pos.type}</span></td>
          <td class="py-2.5 px-3 text-right font-mono font-bold">${formatMoney(pos.value, base)}</td>
          <td class="py-2.5 px-3 text-right font-mono font-semibold ${pos.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">${pos.sub}</td>
        `;
        positionsBody.appendChild(tr);
      });
    }
  }

  // Populate floating detailed positions modal
  renderPositionsDetailModal(stocks, mmfs, holdings, categories, base);

  if ($('dashboard-updated')) {
    $('dashboard-updated').textContent = 'Updated ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}

function updateModalFormVisibility(type) {
  const stockFields = $('modal-fields-stock');
  const mmfFields = $('modal-fields-mmf');
  const genericFields = $('modal-fields-generic');

  if (stockFields) stockFields.classList.toggle('hidden', type !== 'NSE' && type !== 'US');
  if (mmfFields) mmfFields.classList.toggle('hidden', type !== 'MMF');
  if (genericFields) genericFields.classList.toggle('hidden', type !== 'GENERIC');
}

// Dialog Modal Handlers
function setupModal() {
  const dialog = $('add-asset-dialog');
  const openBtn = $('open-add-modal');
  const closeBtn = $('close-add-modal');
  const cancelBtn = $('cancel-add-modal');
  const assetTypeSelect = $('modal-asset-type');

  if (!dialog || !openBtn) return;

  openBtn.addEventListener('click', () => {
    if (assetTypeSelect) updateModalFormVisibility(assetTypeSelect.value);
    dialog.showModal();
  });
  const closeDialog = () => dialog.close();
  if (closeBtn) closeBtn.addEventListener('click', closeDialog);
  if (cancelBtn) cancelBtn.addEventListener('click', closeDialog);

  if (assetTypeSelect) {
    assetTypeSelect.addEventListener('change', (e) => {
      updateModalFormVisibility(e.target.value);
    });
  }

  // Quick add form submission
  const quickForm = $('quick-add-form');
  if (quickForm) {
    quickForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const type = $('modal-asset-type').value;

      try {
        if (type === 'NSE' || type === 'US') {
          const ticker = $('modal-stock-ticker').value.trim().toUpperCase();
          const shares = parseFloat($('modal-stock-shares').value) || 0;
          const price = parseFloat($('modal-stock-price').value) || 0;

          if (!ticker || shares <= 0) {
            alert('Please enter valid ticker and shares owned.');
            return;
          }

          if (type === 'NSE') {
            await API.createStock({ ticker, exchange: 'NSE', shares_owned: shares, average_buy_price: price });
          } else {
            await fetch('/api/us-market/stocks', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ticker, exchange: 'US', shares_owned: shares, average_buy_price: price })
            });
          }
        } else if (type === 'MMF') {
          const name = $('modal-mmf-name').value.trim();
          const balance = parseFloat($('modal-mmf-balance').value) || 0;
          if (!name || balance <= 0) {
            alert('Please enter MMF institution name and balance.');
            return;
          }
          await API.createMMFAccount({ fund_name: name, current_principal_balance: balance, investment_date: new Date().toISOString().split('T')[0] });
        } else {
          const name = $('modal-generic-name').value.trim();
          const val = parseFloat($('modal-generic-value').value) || 0;
          if (!name || val <= 0) {
            alert('Please enter asset name and value.');
            return;
          }
          await Storage.setItem(Storage.STORES.assets, {
            id: crypto.randomUUID(),
            name,
            value: val,
            currency: Storage.getBaseCurrency(),
            created_at: new Date().toISOString()
          });
        }

        dialog.close();
        quickForm.reset();
        window.showToast?.('Investment saved successfully!');
        renderDashboard();
      } catch (err) {
        alert('Error saving investment: ' + err.message);
      }
    });
  }
}

function setupPositionsDetailModal() {
  const dialog = $('positions-detail-dialog');
  const viewBtn = $('btn-view-detailed-positions');
  const closeBtn = $('close-detail-modal');
  const quickTable = $('quick-positions-table');

  if (!dialog) return;

  const openModal = () => dialog.showModal();
  if (viewBtn) viewBtn.addEventListener('click', openModal);
  if (quickTable) quickTable.addEventListener('click', (e) => {
    if (e.target.closest('a')) return; // Allow links to navigate
    openModal();
  });
  if (closeBtn) closeBtn.addEventListener('click', () => dialog.close());
}

// Daily MMF Interest Accrual Action
function setupAccrueMMF() {
  const btn = $('btn-accrue-mmf');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    try {
      btn.disabled = true;
      btn.textContent = 'Accruing Daily Interest...';
      const result = await API.accrueDailyMMFInterest();
      window.showToast?.(`MMF Interest Accrued! total accrued: ${formatMoney(result.total_accrued_today || 0)}`);
      await renderDashboard();
    } catch (err) {
      alert('MMF Accrual failed: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ Accrue Daily MMF Interest';
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupModal();
  setupPositionsDetailModal();
  setupAccrueMMF();
  renderDashboard().catch(e => {
    if ($('dashboard-updated')) $('dashboard-updated').textContent = e.message;
  });
});
