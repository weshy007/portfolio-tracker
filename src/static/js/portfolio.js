import Storage from './storage.js';
import API from './api.js';
import { NSE_SECURITIES, NSE_STOCKS_BY_TICKER, nseCompanyName } from './nse_catalog.js';
import { amount, button, currencies, emptyState, formatMoney, formatPercent, row, totalInBase } from './ui.js';

const defaults = [
  ['NSE Stocks','Equities'],['US Stocks','Equities'],['Money Market Fund','Fixed Income'],
  ['REITs','Real Estate'],['Government Bonds','Fixed Income'],['Treasury Bills','Fixed Income'],
  ['Cash & Bank','Cash'],['Emergency Fund','Safety'],['SACCO','Other'],['Pension','Retirement'],
  ['Business','Business'],['Crypto','Alternative'],['Other','Other']
];
let categories = [];
let institutions = [];

const $ = id => document.getElementById(id);
const now = () => new Date().toISOString();
const money = (value,currency=Storage.getBaseCurrency()) => formatMoney(value,currency);
const marketCategory = name => /Stocks|Equities/i.test(name || '');
const nativeStock = h => h.exchange === 'NSE' || h.exchange === 'US';

async function ensureCategories() {
  const existing = await Storage.getAll(Storage.STORES.categories);
  if (existing.length) return existing;
  await Promise.all(defaults.map(([name,category_type]) => Storage.setItem(Storage.STORES.categories,{
    id:crypto.randomUUID(),name,category_type,is_default:true,created_at:now()
  })));
  return Storage.getAll(Storage.STORES.categories);
}

function fillCurrencies() {
  const select=$('generic-currency');
  currencies.forEach(c=>select.add(new Option(c,c)));
  select.value=Storage.getBaseCurrency();
}

function fillNseTickers() {
  const select = $('nse-ticker');
  select.replaceChildren(new Option('Choose NSE security',''));
  NSE_SECURITIES.slice().sort((x,y)=>x.ticker.localeCompare(y.ticker)).forEach(stock=>{
    const option = new Option(`${stock.ticker} — ${stock.name}`, stock.ticker);
    option.title = stock.name;
    select.add(option);
  });
}

async function fillInstitutions() {
  institutions=await API.getInstitutions();
  const select=$('mmf-fund');
  select.replaceChildren(new Option('Choose fund',''));
  institutions.forEach(item=>{
    const option=new Option(item.institution, item.fund_name);
    option.dataset.yield=item.yield_percentage;
    select.add(option);
  });
}

function setAssetType(type) {
  ['nse','us','mmf','generic'].forEach(name=>$(name+'-fields').hidden=name!==type);
  if(type==='nse') $('generic-currency').value='KES';
}

async function fetchPrice(ticker, exchange, target, statusId) {
  const symbol=String(ticker||'').trim().toUpperCase();
  if(!symbol) return;
  const status=$(statusId);
  status.textContent='Fetching…';
  try {
    const data=exchange==='NSE'
      ? await API.getStockPrice(symbol,'NSE')
      : await fetch('/api/us-market/quote?ticker='+encodeURIComponent(symbol)).then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.detail||'Price lookup failed');return d;});
    $(target).value=data.price ?? data.current_price;
    status.textContent='Updated '+new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  } catch(error) {
    status.textContent=error.message;
    window.showToast?.(error.message,'error');
  }
}

function renderUsPreview() {
  const invested=amount($('us-invested').value), buy=amount($('us-buy').value), box=$('us-shares-preview');
  if(invested>0 && buy>0) {
    const shares=invested/buy;
    box.hidden=false;
    box.textContent=`${shares.toFixed(6)} shares at ${money(buy,'USD')} per share`;
  } else box.hidden=true;
}

function renderHoldingForm() {
  const type=$('asset-type').value;
  if(type==='nse') {
    const ticker=$('nse-ticker').value;
    const stock=NSE_STOCKS_BY_TICKER[ticker];
    if(stock) {
      $('nse-company').textContent=stock.name+' · '+stock.sector;
    }
  }
  if(type==='mmf') {
    const option=$('mmf-fund').selectedOptions[0];
    if(option?.value) {
      $('mmf-yield').value=option.dataset.yield ? option.dataset.yield+'% p.a.' : '—';
    }
  }
}

async function saveStock(type) {
  if(type==='nse') {
    const ticker=$('nse-ticker').value, units=amount($('stock-units').value), buy=amount($('stock-buy').value);
    const current=amount($('stock-current').value)||buy;
    if(!ticker||!units||!buy) throw new Error('Ticker, shares and average buy price are required.');
    const data=await API.createStock({ticker,exchange:'NSE',shares_owned:units,average_buy_price:buy,current_price:current});
    const category=categories.find(c=>c.name==='NSE Stocks');
    await Storage.setItem(Storage.STORES.holdings,{id:crypto.randomUUID(),name:ticker,category_id:category.id,amount:data.current_value,currency:'KES',units:data.shares_owned,average_buy_price:data.average_buy_price,current_price:data.current_price,exchange:'NSE',backend_stock_id:data.id,notes:$('holding-notes').value.trim(),created_at:now(),updated_at:now()});
    return;
  }
  const ticker=$('us-ticker').value.trim().toUpperCase(), invested=amount($('us-invested').value), buy=amount($('us-buy').value);
  if(!ticker||!invested||!buy) throw new Error('US ticker, invested amount and buy price are required.');
  const shares=invested/buy;
  const data=await fetch('/api/us-market/stocks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticker,shares_owned:shares,average_buy_price:buy})}).then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.detail||'Could not save US stock');return d;});
  const category=categories.find(c=>c.name==='US Stocks');
  await Storage.setItem(Storage.STORES.holdings,{id:crypto.randomUUID(),name:ticker,category_id:category.id,amount:data.current_value,currency:'USD',units:data.shares_owned,average_buy_price:data.average_buy_price,current_price:data.current_price,exchange:'US',backend_stock_id:data.id,notes:$('holding-notes').value.trim(),created_at:now(),updated_at:now()});
}

async function saveMMF() {
  const fund=$('mmf-fund').value, amountValue=amount($('mmf-amount').value), investmentDate=$('mmf-date').value;
  if(!fund||!amountValue||!investmentDate) throw new Error('Fund, amount and investment date are required.');
  const data=await API.createMMFAccount({fund_name:fund,current_principal_balance:amountValue,investment_date:investmentDate});
  const category=categories.find(c=>c.name==='Money Market Fund');
  await Storage.setItem(Storage.STORES.holdings,{id:crypto.randomUUID(),name:fund,category_id:category.id,amount:amountValue,currency:'KES',backend_mmf_id:data.id,notes:$('holding-notes').value.trim(),created_at:now(),updated_at:now()});
}

async function saveGeneric(type) {
  const value=amount($('generic-value').value), name=$('holding-name').value.trim();
  if(!name||value<0) throw new Error('Asset name and value are required.');
  const categoryName=type==='reit'?'REITs':type==='bond'?'Government Bonds':type==='t-bill'?'Treasury Bills':'Cash & Bank';
  const category=categories.find(c=>c.name===categoryName);
  await Storage.setItem(Storage.STORES.holdings,{id:crypto.randomUUID(),name,category_id:category.id,amount:value,currency:$('generic-currency').value,notes:$('holding-notes').value.trim(),created_at:now(),updated_at:now()});
}

async function submitHolding(event) {
  event.preventDefault();
  const type=$('asset-type').value;
  try {
    if(type==='nse'||type==='us') await saveStock(type);
    else if(type==='mmf') await saveMMF();
    else await saveGeneric(type);
    event.currentTarget.reset();
    $('asset-type').value='nse';
    setAssetType('nse');
    $('nse-date')?.remove();
    await render();
    window.showToast?.('Holding added.');
  } catch(error) { window.showToast?.(error.message,'error'); }
}

async function deleteHolding(holding) {
  if(!confirm('Delete '+holding.name+'?')) return;
  await Storage.deleteItem(Storage.STORES.holdings,holding.id);
  if(holding.backend_stock_id) try { await API.deleteStock(holding.backend_stock_id); } catch {}
  if(holding.backend_mmf_id) try { await API.deleteMMFAccount(holding.backend_mmf_id); } catch {}
  render();
}

async function renderHoldings() {
  const holdings=await Storage.getAll(Storage.STORES.holdings);
  const filter=$('category-filter').value;
  const visible=filter?holdings.filter(h=>h.category_id===filter):holdings;
  const body=$('holdings-body');
  body.replaceChildren();
  visible.forEach(h=>{
    const category=categories.find(c=>c.id===h.category_id);
    const tr=row([
      {value:h.name},
      {value:category?.name||'Unknown'},
      {value:h.units?Number(h.units).toLocaleString(undefined,{maximumFractionDigits:4}):'—',className:'numeric'},
      {value:money(h.amount,h.currency),className:'numeric'},
      {value:h.units&&h.average_buy_price&&h.current_price?money((h.units*h.current_price)-(h.units*h.average_buy_price),h.currency):'—',className:'numeric '+(h.current_price>=h.average_buy_price?'text-positive':'text-negative')},
      {value:h.currency}
    ]);
    if(h.exchange==='NSE') tr.cells[0].title=nseCompanyName(h.name);
    if(h.exchange==='US') tr.cells[0].title='US listed security';
    const action=document.createElement('td');
    action.append(button('Delete','btn btn-sm btn-danger',()=>deleteHolding(h)));
    tr.append(action); body.append(tr);
  });
  $('holdings-wrap').hidden=!visible.length;
  if(!visible.length) emptyState($('holdings-empty'),'No holdings yet.','Add your first position above.');
  else $('holdings-empty').replaceChildren();

  const filterEl=$('category-filter');
  filterEl.replaceChildren(new Option('All categories',''),...categories.map(c=>new Option(c.name,c.id)));
  filterEl.value=filter;
  return holdings;
}

async function renderAllocation(holdings) {
  if(!holdings.length){$('allocation-content').hidden=true;emptyState($('allocation-empty'),'No allocation yet.','Add a holding to see exposure.');return;}
  const values=await Promise.all(holdings.map(async h=>({name:categories.find(c=>c.id===h.category_id)?.name||'Other',value:await totalInBase([h],API)})));
  const map=new Map();
  values.forEach(({name,value})=>map.set(name,(map.get(name)||0)+value));
  const entries=[...map.entries()].sort((a,b)=>b[1]-a[1]), total=entries.reduce((s,[,v])=>s+v,0);
  const colors=['#0f766e','#14b8a6','#d97706','#2563eb','#7c3aed','#db2777','#475569'];
  let offset=0;
  $('allocation-chart').style.background='conic-gradient('+entries.map(([name,value],i)=>{const start=offset;offset+=total?value/total*100:0;return colors[i%colors.length]+' '+start+'% '+offset+'%';}).join(',')+')';
  $('allocation-total').textContent=money(total);
  const legend=$('allocation-legend');
  legend.replaceChildren(...entries.map(([name,value])=>{
    const item=document.createElement('div'); item.className='allocation-row';
    const label=document.createElement('span'); label.textContent=name;
    const totalEl=document.createElement('strong'); totalEl.textContent=money(value);
    item.append(label,totalEl); return item;
  }));
  $('allocation-content').hidden=false;$('allocation-empty').replaceChildren();
}

async function renderMarketTables() {
  const [stocks,mmfs]=await Promise.all([API.getStocks(),API.getMMFAccounts()]);
  const stockBody=$('stocks-body');stockBody.replaceChildren();
  stocks.forEach(s=>{
    const currency=s.currency|| (s.exchange==='US'?'USD':'KES');
    const tr=row([
      {value:s.ticker},{value:s.exchange},{value:Number(s.shares_owned).toLocaleString(undefined,{maximumFractionDigits:6}),className:'numeric'},
      {value:money(s.average_buy_price,currency),className:'numeric'},{value:money(s.current_price,currency),className:'numeric'},
      {value:money(s.current_value,currency),className:'numeric'},
      {value:money(s.profit_loss,currency)+' ('+formatPercent(s.profit_loss_percentage)+')',className:'numeric '+(s.profit_loss>=0?'text-positive':'text-negative')},
      {value:s.price_updated_at?new Date(s.price_updated_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'—'}
    ]);
    tr.cells[0].title=s.exchange==='NSE'?nseCompanyName(s.ticker):'US listed security';
    const action=document.createElement('td');action.append(button('Delete','btn btn-sm btn-danger',async()=>{await API.deleteStock(s.id);await render();}));tr.append(action);stockBody.append(tr);
  });
  $('stocks-wrap').hidden=!stocks.length;
  if(!stocks.length) emptyState($('stocks-empty'),'No market positions.','Add an NSE or US stock above.'); else $('stocks-empty').replaceChildren();

  const mmfBody=$('mmf-body');mmfBody.replaceChildren();
  mmfs.forEach(m=>{
    const tr=row([
      {value:m.short_name||m.fund_name},{value:m.investment_date||'—'},
      {value:money(m.principal_balance,'KES'),className:'numeric'},{value:money(m.current_balance,'KES'),className:'numeric'},
      {value:money(m.total_interest_accrued,'KES'),className:'numeric text-positive'},
      {value:m.annual_yield_percentage+'%',className:'numeric'},{value:money(m.today_estimated_interest,'KES'),className:'numeric'},
      {value:m.last_accrued_on||'—'}
    ]);
    tr.cells[0].title=m.fund_name;
    const action=document.createElement('td');action.append(button('Delete','btn btn-sm btn-danger',async()=>{await API.deleteMMFAccount(m.id);await render();}));tr.append(action);mmfBody.append(tr);
  });
  $('mmf-wrap').hidden=!mmfs.length;
  if(!mmfs.length) emptyState($('mmf-empty'),'No MMF accounts.','Add a money market fund above.'); else $('mmf-empty').replaceChildren();
}

async function render() {
  categories=await ensureCategories();
  fillCurrencies();
  const select=$('category-filter'), previous=select.value;
  select.replaceChildren(new Option('All categories',''),...categories.map(c=>new Option(c.name,c.id)));
  select.value=previous;
  await renderHoldings().then(renderAllocation);
  await renderMarketTables();
}

$('asset-type').addEventListener('change',e=>setAssetType(e.target.value));
$('nse-ticker').addEventListener('change',()=>{renderHoldingForm();fetchPrice($('nse-ticker').value,'NSE','stock-current','nse-price-status');});
$('mmf-fund').addEventListener('change',renderHoldingForm);
$('fetch-nse-price').addEventListener('click',()=>fetchPrice($('nse-ticker').value,'NSE','stock-current','nse-price-status'));
$('fetch-us-price').addEventListener('click',()=>fetchPrice($('us-ticker').value,'US','us-current','us-price-status'));
['us-invested','us-buy'].forEach(id=>$(id).addEventListener('input',renderUsPreview));
$('holding-form').addEventListener('submit',submitHolding);
$('category-filter').addEventListener('change',render);
$('refresh-stocks').addEventListener('click',async()=>{
  try {
    const results=await Promise.allSettled([API.refreshAllStocks(),API.refreshAllUSStocks()]);
    const failed=results.filter(r=>r.status==='rejected');
    await render();
    window.showToast?.(failed.length?'Some quotes could not be refreshed.':'Quotes refreshed.');
  } catch(e) { window.showToast?.(e.message,'error'); }
});
$('scrape-yields').addEventListener('click',async()=>{try{await API.scrapeMMFYields();await render();window.showToast?.('Daily yields updated.');}catch(e){window.showToast?.(e.message,'error');}});
$('accrue-mmf').addEventListener('click',async()=>{try{await API.accrueMMF();await render();window.showToast?.('Completed MMF days accrued.');}catch(e){window.showToast?.(e.message,'error');}});
$('asset-type').value='nse';setAssetType('nse');
fillNseTickers();
fillInstitutions().catch(()=>{});
render().catch(error=>emptyState($('holdings-empty'),'Portfolio unavailable',error.message));
