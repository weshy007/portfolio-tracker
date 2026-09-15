/** Shared rendering and money helpers. Use DOM nodes for user-provided text, never HTML interpolation. */
import Storage from './storage.js';

export const currencies = ['KES', 'USD', 'EUR', 'GBP', 'ZAR', 'UGX', 'TZS'];
export function amount(value) { const number = Number(value); return Number.isFinite(number) ? number : 0; }
export function formatMoney(value, currency = Storage.getBaseCurrency()) {
    return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(amount(value));
}
export function formatPercent(value, showSign = true) {
    const num = amount(value);
    const sign = showSign && num > 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
}
export function setText(id, value) { const node = document.getElementById(id); if (node) node.textContent = value; }
export function emptyState(container, title, detail, href, action) {
    container.replaceChildren(); const heading = document.createElement('h3'); heading.textContent = title;
    const copy = document.createElement('p'); copy.textContent = detail; container.append(heading, copy);
    if (href && action) { const link = document.createElement('a'); link.className = 'btn btn-primary'; link.href = href; link.textContent = action; container.append(link); }
}
export function row(cells) { const tr = document.createElement('tr'); cells.forEach(({ value, className }) => { const td = document.createElement('td'); td.textContent = value; if (className) td.className = className; tr.append(td); }); return tr; }
export function button(label, className, handler) { const item = document.createElement('button'); item.type = 'button'; item.className = className; item.textContent = label; item.addEventListener('click', handler); return item; }
export function renderList(container, records, describe, onDelete) {
    container.replaceChildren(); records.forEach(record => { const line = document.createElement('div'); line.className = 'record-line'; const text = document.createElement('span'); text.textContent = describe(record); line.append(text, button('Delete', 'btn btn-sm btn-danger', () => onDelete(record.id))); container.append(line); });
}
export async function baseAmount(record, api) {
    const value = amount(record.amount); const base = Storage.getBaseCurrency(); const currency = record.currency || base;
    if (currency === base) return value;
    const quote = await api.getRate(currency, base); return value * amount(quote.rate);
}
export async function totalInBase(records, api) { return (await Promise.all(records.map(record => baseAmount(record, api)))).reduce((total, value) => total + value, 0); }
