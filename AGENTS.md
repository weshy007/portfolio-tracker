# 🤖 Portfolio Tracker: Agent Architecture

This document defines the agent architecture for the Akiba Finance portfolio and financial allocation tracker. Because the application is strictly local-first and built on Python 3.12+, FastAPI, and IndexedDB[cite: 2], all agents must operate locally without transmitting sensitive financial data to remote servers[cite: 2].

## 🏗️ Core Agents

### 1. 📡 Currency & Sync Agent
* This agent operates entirely within the FastAPI backend using the currency provider abstraction[cite: 1, 2]. 
* It fetches and caches exchange rates for supported base currencies like KES, USD, EUR, and GBP[cite: 2]. 
* It guarantees that only source and destination currency codes are sent to external APIs, ensuring user investment amounts remain private[cite: 1, 2]. 
* It provides graceful fallbacks to cached rates or issues explicit failure responses if the external API is unavailable[cite: 1, 2].

### 2. 📊 Budget & FI Analysis Agent
* This agent normalizes multi-currency income, expenses, and holdings into the user's selected base currency[cite: 1, 2]. 
* It calculates the split between essential and non-essential monthly expenses to determine accurate emergency fund targets[cite: 2]. 
* It computes the Financial Independence (FI) Number incorporating a Kenya 10% inflation model[cite: 1]. 
* It determines the exact monthly surplus, savings rate, and investment rate[cite: 1, 2].

### 3. 🧠 Allocation Advisory Agent
* This agent continuously evaluates planned monthly allocations against actual monthly income[cite: 2]. 
* It automatically flags overallocation states if the planned budget exceeds 100% of the user's income[cite: 1, 2]. 
* It strictly separates and compares current existing portfolio holdings against future planned monthly investments[cite: 1, 2]. 
* It calculates a contribution-only projection for future portfolio value without guaranteeing speculative investment returns[cite: 2].

### 4. 🛡️ Local-First Data Interceptor
* This agent enforces the architectural rule that financial data must remain on the user's device by default[cite: 2]. 
* It interacts with the frontend `storage.js` abstraction to manage local IndexedDB backups and versioned schema exports[cite: 1, 2]. 
* It validates imported JSON data schemas before clearing or overwriting existing local databases to prevent corruption[cite: 1, 2].