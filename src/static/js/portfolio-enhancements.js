import Storage from './storage.js';

const $ = (selector, root = document) => root.querySelector(selector);
const asOf = value => value ? `As of ${new Date(value).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} - ${new Date(value).toLocaleDateString('en-GB')}` : 'As of —';

async function category(name, type) {
    const categories = await Storage.getAll(Storage.STORES.categories);
    let item = categories.find(row => row.name === name);
    if (!item) {
        item = {id:crypto.randomUUID(), name, category_type:type, is_default:false, created_at:new Date().toISOString()};
        await Storage.setItem(Storage.STORES.categories, item);
    }
    return item;
}

async function localHolding(data) {
    await Storage.setItem(Storage.STORES.holdings, {id:crypto.randomUUID(), ...data, created_at:new Date().toISOString(), updated_at:new Date().toISOString()});
}

const field = (label,id,type='text',attrs='') => `<div class="form-group"><label for="${id}">${label}</label><input id="${id}" type="${type}" ${attrs}></div>`;

function assetMarkup() {
    return `<div class="asset-adder"><div class="asset-adder-intro"><div><p class="eyebrow">Portfolio</p><h2 class="card-title">Add asset</h2><p class="text-muted">Choose the asset type. The form changes to match it.</p></div><span class="asset-adder-note">Market values are estimates and may differ from final statements.</span></div><div class="form-group"><label for="asset-kind">Asset type</label><select id="asset-kind"><option value="nse">NSE Stock</option><option value="us">US Stock</option><option value="mmf">Money Market Fund</option><option value="reit">REIT</option><option value="bond">Government Bond</option><option value="t-bill">T-Bill</option><option value="cash">Cash / Other</option></select></div><form id="adaptive-asset-form" class="grid grid-2"></form></div>`;
}

async function loadNse(select) {
    try {
        const response=await fetch('/api/market/stocks/nse-tickers');
        const stocks=await response.json();
        (Array.isArray(stocks)?stocks:[]).filter(s=>!/^ACORN|FAHR/i.test(String(s.ticker||''))).forEach(s=>select.add(new Option(`${s.ticker} — ${s.name||''}`,s.ticker)));
    } catch {}
}

function renderForm(type) {
    const form=$('#adaptive-asset-form'); if(!form)return;
    let html='';
    if(type==='nse') {
        html+=`<div class="form-group grid-span-2"><label for="asset-ticker">NSE stock</label><select id="asset-ticker" required><option value="">Choose NSE stock</option></select></div>`;
        html+=field('Shares owned','asset-units','number','required min="0.000001" step="any"');
        html+=field('Average buy price (KES)','asset-buy','number','required min="0.0001" step="any"');
        html+=field('Current price (KES)','asset-current','number','required min="0.0001" step="any"');
        html+=`<div class="form-group"><button id="asset-fetch" type="button" class="btn btn-secondary">Fetch Mansa price</button></div>`;
    } else if(type==='us') {
        html+=field('US ticker','asset-ticker','text','required maxlength="20" placeholder="VST, AAPL, NVDA" style="text-transform:uppercase"');
        html+=field('Amount invested (USD)','asset-invested','number','required min="0.01" step="0.01" placeholder="e.g. 1.00"');
        html+=field('Buy price (USD / share)','asset-buy','number','required min="0.000001" step="any"');
        html+=field('Current price (USD / share)','asset-current','number','required min="0.000001" step="any"');
        html+=`<div class="form-group"><button id="asset-fetch" type="button" class="btn btn-secondary">Fetch Yahoo price</button></div><div id="fraction-preview" class="calc-preview grid-span-2" hidden></div>`;
    } else if(type==='mmf') {
        html+=field('Fund name','asset-name','text','required placeholder="e.g. CIC Money Market Fund"');
        html+=field('Investment amount (KES)','asset-amount','number','required min="0.01" step="0.01"');
        html+=`<p class="notice grid-span-2">Rates are fetched by the daily worker. Accrual runs from the investment day through EOD yesterday.</p>`;
    } else {
        html+=field(type==='reit'?'REIT / security':'Asset name','asset-name','text','required');
        html+=field(type==='reit'?'Market value (KES)':'Current value (KES)','asset-amount','number','required min="0" step="0.01"');
        if(type==='reit')html+=`<p class="notice grid-span-2">ACORN is a REIT, not an ordinary NSE stock. It is tracked separately.</p>`;
    }
    html+=field('Notes (optional)','asset-notes','text','maxlength="500"');
    html+=`<div class="form-group grid-span-2 form-actions"><button class="btn btn-primary" type="submit">Add asset</button></div>`;
    form.innerHTML=html;

    if(type==='nse') {
        loadNse($('#asset-ticker'));
        $('#asset-fetch').onclick=()=>fetchQuote(`/api/market/stocks/price?ticker=${encodeURIComponent($('#asset-ticker').value)}&exchange=NSE`,'asset-current','Fetch Mansa price');
    }
    if(type==='us') {
        const preview=()=>{const amount=Number($('#asset-invested').value)||0,buy=Number($('#asset-buy').value)||0,box=$('#fraction-preview');if(amount>0&&buy>0){const shares=amount/buy;box.hidden=false;box.innerHTML=`<strong>${shares.toFixed(6)} shares</strong><span>$${amount.toFixed(2)} buys ${shares.toFixed(6)} shares at $${buy.toFixed(4)} per share.</span>`;}else box.hidden=true;};
        $('#asset-invested').oninput=preview; $('#asset-buy').oninput=preview;
        $('#asset-fetch').onclick=()=>fetchQuote(`/api/us-market/quote?ticker=${encodeURIComponent($('#asset-ticker').value)}`,'asset-current','Fetch Yahoo price');
    }
    form.onsubmit=e=>saveAsset(e,type);
}

async function fetchQuote(url,target,label) {
    const button=$('#asset-fetch'),ticker=$('#asset-ticker').value.trim().toUpperCase(); if(!ticker)return;
    button.disabled=true;button.textContent='Fetching…';
    try {const response=await fetch(url),data=await response.json();if(!response.ok)throw new Error(data.detail||'Price lookup failed');$('#'+target).value=data.price??data.current_price;}
    catch(error){window.showToast?.(error.message,'error');}
    finally{button.disabled=false;button.textContent=label;}
}

async function saveAsset(event,type) {
    event.preventDefault();
    try {
        const name=$('#asset-name')?.value.trim(),notes=$('#asset-notes')?.value.trim()||'';
        if(type==='us') {
            const ticker=$('#asset-ticker').value.trim().toUpperCase(),invested=Number($('#asset-invested').value),buy=Number($('#asset-buy').value),current=Number($('#asset-current').value),shares=invested/buy;
            const response=await fetch('/api/us-market/stocks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticker,shares_owned:shares,average_buy_price:buy,current_price:current})});
            const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not save US stock');
            const cat=await category('US Stocks','Equities');await localHolding({name:data.ticker,category_id:cat.id,amount:data.current_value,currency:'USD',units:data.shares_owned,average_buy_price:data.average_buy_price,current_price:data.current_price,exchange:'US',backend_stock_id:data.id,notes});
        } else if(type==='nse') {
            const ticker=$('#asset-ticker').value.trim().toUpperCase();
            const response=await fetch('/api/market/stocks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticker,exchange:'NSE',shares_owned:Number($('#asset-units').value),average_buy_price:Number($('#asset-buy').value),current_price:Number($('#asset-current').value)})});
            const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not save NSE stock');
            const cat=await category('NSE Stocks','Equities');await localHolding({name:data.ticker,category_id:cat.id,amount:data.current_value,currency:'KES',units:data.shares_owned,average_buy_price:data.average_buy_price,current_price:data.current_price,exchange:'NSE',backend_stock_id:data.id,notes});
        } else if(type==='mmf') {
            const amount=Number($('#asset-amount').value);const response=await fetch('/api/market/mmfs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fund_name:name,current_principal_balance:amount})});
            const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not save MMF');
            const cat=await category('Money Market Fund','Fixed Income');await localHolding({name,category_id:cat.id,amount,currency:'KES',notes});
        } else {
            const amount=Number($('#asset-amount').value),catName=type==='reit'?'REITs':type==='bond'?'Government Bonds':type==='t-bill'?'Treasury Bills':'Cash & Bank',cat=await category(catName,type==='reit'?'Real Estate':type==='cash'?'Cash':'Fixed Income');
            await localHolding({name,category_id:cat.id,amount,currency:'KES',notes,exchange:type==='reit'?'NSE-REIT':null});
        }
        window.showToast?.('Asset added successfully');setTimeout(()=>window.location.reload(),250);
    }catch(error){window.showToast?.(error.message||'Could not add asset','error');}
}

function installAssetAdder(){const card=$('#dashboard-stock-form')?.closest('.card');if(!card||card.dataset.assetAdderInstalled)return;card.dataset.assetAdderInstalled='true';card.innerHTML=assetMarkup();$('#asset-kind').onchange=e=>renderForm(e.target.value);renderForm('nse');}

function enhanceStocks(){const body=$('#stocks-body');if(!body)return;[...body.rows].forEach(row=>{if(row.cells[1]?.textContent.trim()==='US'&&row.cells[0]&&!row.cells[0].querySelector('.market-badge'))row.cells[0].insertAdjacentHTML('beforeend',' <span class="market-badge">US · USD</span>');const updated=row.cells[9];if(updated&&!updated.dataset.formatted){const parsed=Date.parse(updated.textContent.trim());if(!Number.isNaN(parsed))updated.textContent=asOf(parsed);updated.dataset.formatted='true';}});}

function paginate(bodyId,size=10){const body=$(`#${bodyId}`);if(!body||body.dataset.paginationInstalled)return;body.dataset.paginationInstalled='true';const wrap=body.closest('.table-wrapper');if(!wrap)return;const controls=document.createElement('div');controls.className='table-pagination';wrap.after(controls);let page=1;const render=()=>{const rows=[...body.rows],pages=Math.max(1,Math.ceil(rows.length/size));page=Math.max(1,Math.min(page,pages));rows.forEach((row,i)=>row.hidden=i<(page-1)*size||i>=page*size);controls.innerHTML=`<span>Page ${page} of ${pages} · ${rows.length} items</span><div><button type="button" class="btn btn-sm btn-secondary" data-page="prev" ${page===1?'disabled':''}>Previous</button><button type="button" class="btn btn-sm btn-secondary" data-page="next" ${page===pages?'disabled':''}>Next</button></div>`;controls.querySelector('[data-page="prev"]').onclick=()=>{page--;render()};controls.querySelector('[data-page="next"]').onclick=()=>{page++;render()};};new MutationObserver(render).observe(body,{childList:true});render();}

async function decorateMmf(){const body=$('#mmf-body');if(!body)return;try{const response=await fetch('/api/mmf/rate-status');if(!response.ok)return;const statuses=await response.json();[...body.rows].forEach(row=>{const fund=row.cells[0]?.textContent.trim(),status=statuses.find(item=>fund?.toLowerCase().includes(item.fund_name.toLowerCase())||item.fund_name.toLowerCase().includes(fund?.toLowerCase()||''));if(!status||!row.cells[3]||row.cells[3].querySelector('.rate-source'))return;const source=status.source==='worker'?`Worker fetched · ${status.rate_date}`:'Benchmark fallback';row.cells[3].title=source;row.cells[3].insertAdjacentHTML('beforeend',`<small class="rate-source">${source}</small>`);});}catch{}}

function init(){installAssetAdder();paginate('stocks-body');paginate('holdings-body');enhanceStocks();decorateMmf();const body=$('#stocks-body');if(body)new MutationObserver(enhanceStocks).observe(body,{childList:true});setTimeout(()=>{installAssetAdder();paginate('stocks-body');paginate('holdings-body');enhanceStocks();decorateMmf();},700);}
document.addEventListener('DOMContentLoaded',init);
