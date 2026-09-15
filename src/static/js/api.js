/**
 * API client for communicating with FastAPI backend
 */

const API_BASE = '/api';

/**
 * Make API request
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = `${API_BASE}${endpoint}`;
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) { throw error; }
}

/**
 * Calculate emergency fund
 */
async function calculateEmergencyFund(essentialExpenses, targetMonths = 6, currentFund = 0) {
    return apiRequest('/calculate/emergency-fund', 'POST', {
        essential_monthly_expenses: essentialExpenses,
        target_months: targetMonths,
        current_emergency_fund: currentFund,
    });
}

/**
 * Calculate allocation
 */
async function calculateAllocation(income, expenses, savings, investments, debt = 0, other = 0) {
    return apiRequest('/calculate/allocation', 'POST', {
        total_income: income,
        expenses,
        savings,
        investments,
        debt,
        other,
    });
}

/**
 * Calculate projection
 */
async function calculateProjection(monthlyContribution, annualReturn = 0, years = 1) {
    return apiRequest('/calculate/projection', 'POST', {
        monthly_contribution: monthlyContribution,
        annual_return_percent: annualReturn,
        years,
    });
}

/**
 * Calculate savings rate
 */
async function calculateSavingsRate(savingsAmount, totalIncome) {
    return apiRequest('/calculate/savings-rate', 'POST', {
        savings_amount: savingsAmount,
        total_income: totalIncome,
    });
}

/**
 * Calculate net worth
 */
async function calculateNetWorth(assets, liabilities) {
    return apiRequest('/calculate/net-worth', 'POST', {
        total_assets: assets,
        total_liabilities: liabilities,
    });
}

/**
 * Health check
 */
async function healthCheck() {
    return apiRequest('/health', 'GET');
}

/** Requests only a currency pair; no user financial amount is transmitted. */
async function getRate(fromCurrency, toCurrency) {
    return apiRequest(`/currency/rate?from_currency=${encodeURIComponent(fromCurrency)}&to_currency=${encodeURIComponent(toCurrency)}`);
}

/** Market Tracking: Mansa Stock API & PesaCalc MMF Engine */
async function getMarketSummary() {
    return apiRequest('/market/summary');
}

async function getStocks() {
    return apiRequest('/market/stocks');
}

async function getNSETickers(exchange = 'NSE') {
    return apiRequest(`/market/stocks/nse-tickers?exchange=${encodeURIComponent(exchange)}`);
}

async function getStockPrice(ticker, exchange = 'NSE') {
    return apiRequest(`/market/stocks/price?ticker=${encodeURIComponent(ticker)}&exchange=${encodeURIComponent(exchange)}`);
}

async function createStock(payload) {
    return apiRequest('/market/stocks', 'POST', payload);
}

async function refreshStock(positionId) {
    return apiRequest(`/market/stocks/${encodeURIComponent(positionId)}/refresh`, 'POST');
}

async function refreshAllStocks() {
    return apiRequest('/market/stocks/refresh-all', 'POST');
}

async function deleteStock(positionId) {
    return apiRequest(`/market/stocks/${encodeURIComponent(positionId)}`, 'DELETE');
}

async function getMMFAccounts() {
    return apiRequest('/market/mmfs');
}

async function createMMFAccount(payload) {
    return apiRequest('/market/mmfs', 'POST', payload);
}

async function accrueMMF() {
    return apiRequest('/market/mmfs/accrue', 'POST');
}

async function deleteMMFAccount(accountId) {
    return apiRequest(`/market/mmfs/${encodeURIComponent(accountId)}`, 'DELETE');
}

async function getMMFYields() {
    return apiRequest('/market/yields');
}

async function scrapeMMFYields() {
    return apiRequest('/market/yields/scrape', 'POST');
}

async function getInstitutions() {
    return apiRequest('/market/institutions');
}

async function matchInstitution(query) {
    return apiRequest(`/market/institutions/match?query=${encodeURIComponent(query)}`);
}

const API = {
    calculateEmergencyFund,
    calculateAllocation,
    calculateProjection,
    calculateSavingsRate,
    calculateNetWorth,
    healthCheck,
    getRate,
    getMarketSummary,
    getStocks,
    getNSETickers,
    getStockPrice,
    createStock,
    refreshStock,
    refreshAllStocks,
    deleteStock,
    getMMFAccounts,
    createMMFAccount,
    accrueMMF,
    deleteMMFAccount,
    getMMFYields,
    scrapeMMFYields,
    getInstitutions,
    matchInstitution,
};

export default API;

