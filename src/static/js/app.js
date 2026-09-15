/**
 * Main application script
 */

import Storage from './storage.js';
import API from './api.js';

// Initialize storage on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Initialize storage
        await Storage.init();

        // Health check (silent, no console logging in production)
        const health = await API.healthCheck();
        if (!health) throw new Error('API unhealthy');

        // Get user preferences
        const baseCurrency = Storage.getBaseCurrency();
        document.querySelectorAll('[data-base-currency]').forEach(el => {
            el.textContent = baseCurrency;
        });
        const theme = Storage.getPreference('theme', 'light');
        document.documentElement.dataset.theme = theme === 'auto'
            ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
            : theme;

        // Mark app as initialized
        document.body.classList.add('app-ready');
    } catch (error) {
        // Keep the interface usable offline; pages can surface actionable errors locally.
        document.body.classList.add('app-error');
    }

    // Mobile navigation control
    const menuButton = document.querySelector('.mobile-menu');
    const sidebar = document.querySelector('.sidebar');
    if (menuButton && sidebar) {
        menuButton.addEventListener('click', () => {
            const isOpen = sidebar.classList.toggle('is-open');
            menuButton.setAttribute('aria-expanded', String(isOpen));
        });
        // Close sidebar when nav item is clicked
        sidebar.querySelectorAll('.nav-item').forEach(link => {
            link.addEventListener('click', () => {
                sidebar.classList.remove('is-open');
                menuButton.setAttribute('aria-expanded', 'false');
            });
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && sidebar.classList.contains('is-open')) {
                sidebar.classList.remove('is-open');
                menuButton.setAttribute('aria-expanded', 'false');
                menuButton.focus();
            }
        });
    }
});

// Export for use in other modules
window.Storage = Storage;
window.API = API;
window.showToast = (message, type = 'success') => {
    const toast = document.getElementById('app-toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    toast.hidden = false;
    clearTimeout(window.__akibaToastTimer);
    window.__akibaToastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
};
