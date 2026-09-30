/**
 * Main application script - Handles theme initialization, mobile navigation drawer, and local storage state.
 */

import Storage from './storage.js';
import API from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Initialize local IndexedDB storage
        await Storage.init();

        // Health check
        const health = await API.healthCheck().catch(() => null);

        // Get user preferences
        const baseCurrency = Storage.getBaseCurrency();
        document.querySelectorAll('[data-base-currency]').forEach(el => {
            el.textContent = baseCurrency;
        });

        // Theme management: Default theme is DARK
        const theme = Storage.getPreference('theme', 'dark');
        const isDark = theme === 'dark' || (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);

        document.documentElement.classList.toggle('dark', isDark);
        document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
        document.body.setAttribute('data-theme', isDark ? 'dark' : 'light');

        // Mark app as ready
        document.body.classList.add('app-ready');
    } catch (error) {
        document.body.classList.add('app-error');
    }

    // Mobile Navigation Drawer Control
    const menuButton = document.querySelector('.mobile-menu');
    const sidebar = document.querySelector('.sidebar');

    if (menuButton && sidebar) {
        menuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = sidebar.classList.toggle('is-open');
            menuButton.setAttribute('aria-expanded', String(isOpen));
        });

        // Close sidebar when clicking links
        sidebar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                sidebar.classList.remove('is-open');
                menuButton.setAttribute('aria-expanded', 'false');
            });
        });

        // Close when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 1024 && sidebar.classList.contains('is-open') && !sidebar.contains(e.target) && !menuButton.contains(e.target)) {
                sidebar.classList.remove('is-open');
                menuButton.setAttribute('aria-expanded', 'false');
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
                sidebar.classList.remove('is-open');
                menuButton.setAttribute('aria-expanded', 'false');
            }
        });
    }
});

