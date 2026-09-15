/** Local-first persistence boundary. Financial records never leave this database. */
const DB_NAME = 'portfolio-tracker';
const DB_VERSION = 2;
const SCHEMA_VERSION = 2;
const STORES = Object.freeze({
    categories: 'categories', holdings: 'holdings', income_sources: 'income_sources',
    expenses: 'expenses', planned_allocations: 'planned_allocations', assets: 'assets',
    liabilities: 'liabilities',
});
const CURRENCIES = new Set(['KES', 'USD', 'EUR', 'GBP', 'ZAR', 'UGX', 'TZS']);
let db;

function assertStore(store) { if (!Object.values(STORES).includes(store)) throw new Error('Unknown data store'); }
function validRecord(record) { return record && typeof record === 'object' && typeof record.id === 'string' && record.id.length > 0; }
function validBackup(value) {
    if (!value || typeof value !== 'object' || value.schema_version !== SCHEMA_VERSION || !value.data || typeof value.data !== 'object') return false;
    if (value.settings && typeof value.settings !== 'object') return false;
    return Object.keys(value.data).every(key => key in STORES && Array.isArray(value.data[key]) && value.data[key].every(validRecord));
}
function open() {
    if (db) return Promise.resolve(db);
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onerror = () => reject(request.error || new Error('Could not open local storage'));
        request.onblocked = () => reject(new Error('Close other Akiba Finance tabs and try again.'));
        request.onupgradeneeded = event => {
            const database = event.target.result;
            Object.values(STORES).forEach(name => { if (!database.objectStoreNames.contains(name)) database.createObjectStore(name, { keyPath: 'id' }); });
        };
        request.onsuccess = () => { db = request.result; db.onversionchange = () => { db.close(); db = undefined; }; resolve(db); };
    });
}
async function transaction(store, mode, action) {
    assertStore(store); const database = await open();
    return new Promise((resolve, reject) => {
        const tx = database.transaction(store, mode); const request = action(tx.objectStore(store));
        tx.onabort = () => reject(tx.error || new Error('Local storage operation failed'));
        tx.onerror = () => reject(tx.error || new Error('Local storage operation failed'));
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}
const getAll = store => transaction(store, 'readonly', objectStore => objectStore.getAll());
const getItem = (store, id) => transaction(store, 'readonly', objectStore => objectStore.get(id));
async function setItem(store, item) { assertStore(store); if (!validRecord(item)) throw new Error('A record needs a non-empty id.'); return transaction(store, 'readwrite', objectStore => objectStore.put(item)); }
const deleteItem = (store, id) => transaction(store, 'readwrite', objectStore => objectStore.delete(id));
const clearStore = store => transaction(store, 'readwrite', objectStore => objectStore.clear());
async function exportData() {
    const data = {}; for (const [key, store] of Object.entries(STORES)) data[key] = await getAll(store);
    return { schema_version: SCHEMA_VERSION, exported_at: new Date().toISOString(), settings: { base_currency: getBaseCurrency(), theme: getPreference('theme', 'light') }, data };
}
async function importData(backup) {
    if (!validBackup(backup)) throw new Error(`Invalid or unsupported backup. Expected Akiba Finance schema v${SCHEMA_VERSION}.`);
    const database = await open();
    await new Promise((resolve, reject) => {
        const tx = database.transaction(Object.values(STORES), 'readwrite');
        Object.entries(STORES).forEach(([key, store]) => { const target = tx.objectStore(store); target.clear(); backup.data[key].forEach(item => target.put(item)); });
        tx.oncomplete = resolve; tx.onerror = () => reject(tx.error || new Error('Import failed; your existing data was kept.')); tx.onabort = () => reject(tx.error || new Error('Import failed; your existing data was kept.'));
    });
    if (backup.settings.base_currency && CURRENCIES.has(backup.settings.base_currency)) setBaseCurrency(backup.settings.base_currency);
    if (typeof backup.settings.theme === 'string') setPreference('theme', backup.settings.theme);
}
async function deleteAllData() {
    if (db) { db.close(); db = undefined; }
    await new Promise((resolve, reject) => { const request = indexedDB.deleteDatabase(DB_NAME); request.onsuccess = resolve; request.onerror = () => reject(request.error); request.onblocked = () => reject(new Error('Close other Akiba Finance tabs and try again.')); });
    localStorage.removeItem('akiba:base_currency'); localStorage.removeItem('akiba:theme');
}
const getPreference = (key, fallback = null) => localStorage.getItem(`akiba:${key}`) ?? fallback;
const setPreference = (key, value) => localStorage.setItem(`akiba:${key}`, value);
const getBaseCurrency = () => getPreference('base_currency', 'KES');
function setBaseCurrency(currency) { if (!CURRENCIES.has(currency)) throw new Error('Unsupported base currency'); setPreference('base_currency', currency); }
const Storage = { init: open, getAll, getItem, setItem, deleteItem, clearStore, deleteAllData, exportData, importData, getPreference, setPreference, getBaseCurrency, setBaseCurrency, STORES, SCHEMA_VERSION, CURRENCIES };
export default Storage;
