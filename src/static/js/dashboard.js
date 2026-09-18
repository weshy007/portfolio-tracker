import Storage from './storage.js';
import API from './api.js';
import { formatMoney, totalInBase } from './ui.js';

const $=id=>document.getElementById(id);
const localTotal=async(store,filter=()=>true)=>totalInBase((await Storage.getAll(store)).filter(filter),API);
async function renderDashboard(){
  const base=Storage.getBaseCurrency();
  const [stocks,mmfs,holdings,assets,liabilities,incomes,expenses]=await Promise.all([
    API.getStocks(),API.getMMFAccounts(),
    Storage.getAll(Storage.STORES.holdings),Storage.getAll(Storage.STORES.assets),
    Storage.getAll(Storage.STORES.liabilities),Storage.getAll(Storage.STORES.income_sources),
    Storage.getAll(Storage.STORES.expenses)
  ]);
  const excluded=new Set(['NSE Stocks','US Stocks','Money Market Fund']);
  const categories=await Storage.getAll(Storage.STORES.categories);
  const other=holdings.filter(h=>!excluded.has(categories.find(c=>c.id===h.category_id)?.name));
  const [stockValue,stockCost,mmfValue,mmfInterest,otherValue,assetValue,liabilityValue,incomeValue,expenseValue]=await Promise.all([
    totalInBase(stocks.map(s=>({amount:s.current_value,currency:s.currency||'KES'})),API),
    totalInBase(stocks.map(s=>({amount:s.cost_basis,currency:s.currency||'KES'})),API),
    totalInBase(mmfs.map(m=>({amount:m.current_balance,currency:'KES'})),API),
    totalInBase(mmfs.map(m=>({amount:m.total_interest_accrued,currency:'KES'})),API),
    totalInBase(other,API),totalInBase(assets,API),totalInBase(liabilities,API),
    totalInBase(incomes.filter(x=>x.active!==false),API),totalInBase(expenses.filter(x=>x.active!==false),API)
  ]);
  const portfolio=stockValue+mmfValue+otherValue, cost=stockCost+otherValue, pl=stockValue-stockCost;
  const surplus=incomeValue-expenseValue, networth=portfolio+assetValue-liabilityValue;
  $('portfolio-total').textContent=formatMoney(portfolio,base);
  $('portfolio-note').textContent=`${stocks.length+mmfs.length+holdings.length} tracked positions · ${base}`;
  $('cost-total').textContent=formatMoney(cost,base);
  $('pl-total').textContent=formatMoney(pl,base);
  $('pl-total').className='metric-value '+(pl>=0?'text-positive':'text-negative');
  $('pl-note').textContent=stockCost?((pl/stockCost)*100).toFixed(2)+'% on market positions':'No quoted market cost basis yet';
  $('interest-total').textContent=formatMoney(mmfInterest,base);
  $('interest-note').textContent=mmfs.length?`${mmfs.length} MMF account${mmfs.length===1?'':'s'}`:'No MMF accounts';
  $('surplus-total').textContent=formatMoney(surplus,base);
  $('surplus-total').className='metric-value '+(surplus>=0?'text-positive':'text-negative');
  $('surplus-note').textContent=incomeValue?formatMoney(incomeValue,base)+' income · '+formatMoney(expenseValue,base)+' expenses':'Add income in Budget';
  $('networth-total').textContent=formatMoney(networth,base);
  $('networth-note').textContent=`${formatMoney(assetValue,base)} assets · ${formatMoney(liabilityValue,base)} liabilities`;
  $('dashboard-updated').textContent='Updated '+new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}
document.addEventListener('DOMContentLoaded',()=>renderDashboard().catch(e=>$('dashboard-updated').textContent=e.message));
