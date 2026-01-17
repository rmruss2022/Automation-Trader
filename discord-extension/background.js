const os = require('os');

const DEFAULT_SETTINGS = {
    heliusApiKey: os.getenv("HELIUS_API_KEY"),
    tradeApiBaseUrl: "https://apihelios.xyz",
    buyAmountSol: "0.00015",
    pricePollSeconds: 60,
    maxHoldSeconds: 1800,
    timeExitMultiplier: 1.2,
    trailingStartMultiplier: 2.0,
    trailingStopFactor: 0.75,
    hardStopFactor: 0.7,
    takeProfitLevels: [
        { multiplier: 2.0, targetSold: 0.3 },
        { multiplier: 5.0, targetSold: 0.6 },
        { multiplier: 10.0, targetSold: 0.9 }
    ]
};

const CONTRACT_REGEX = /\b[A-HJ-NP-Za-km-z1-9]{32,44}\b/g;

const getSettings = () => {
    return new Promise(resolve => {
        chrome.storage.local.get(DEFAULT_SETTINGS, resolve);
    });
};

const getState = () => {
    return new Promise(resolve => {
        chrome.storage.local.get({ trades: {}, seenContracts: [] }, resolve);
    });
};

const saveState = (state) => {
    return new Promise(resolve => {
        chrome.storage.local.set(state, resolve);
    });
};

const extractContracts = (message) => {
    if (!message) return [];
    const matches = message.match(CONTRACT_REGEX);
    return matches ? Array.from(new Set(matches)) : [];
};

const fetchPrice = async (contract, heliusApiKey) => {
    if (!heliusApiKey) return 0;
    const response = await fetch(`https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            id: "price",
            method: "getAsset",
            params: { id: contract }
        })
    });
    if (!response.ok) {
        throw new Error(`Helius request failed: ${response.status}`);
    }
    const data = await response.json();
    const price = data?.result?.token_info?.price_info?.price_per_token;
    return price ? Number(price) : 0;
};

const executeTrade = async (action, contract, payload, settings) => {
    if (!settings.tradeApiBaseUrl) {
        console.warn("Trade API base URL not configured. Skipping trade execution.");
        return;
    }
    const response = await fetch(`${settings.tradeApiBaseUrl}/trade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            action,
            contract,
            ...payload
        })
    });
    if (!response.ok) {
        throw new Error(`Trade API failed: ${response.status}`);
    }
};

const buyToken = async (contract, settings, trades) => {
    if (!trades[contract]) {
        const entryPrice = await fetchPrice(contract, settings.heliusApiKey);
        trades[contract] = {
            entry: entryPrice || 0,
            high: entryPrice || 0,
            sold: 0,
            openedAt: Date.now(),
            lastPrice: entryPrice || 0
        };
    }
    await executeTrade("buy", contract, { amountSol: settings.buyAmountSol }, settings);
    console.log(`✅ Buy triggered for ${contract}`);
};

const sellToken = async (contract, percentage, reason, settings, trades) => {
    const trade = trades[contract];
    if (!trade || trade.sold >= 1) return;
    await executeTrade("sell", contract, { percentage, reason }, settings);
    trade.sold += percentage / 100;
    trade.sold = Math.min(trade.sold, 1);
    console.log(`✅ Sell ${percentage}% for ${contract} | ${reason}`);
};

const evaluateSell = async (contract, currentPrice, settings, trades) => {
    const trade = trades[contract];
    if (!trade || trade.entry <= 0) return;

    const multiplier = currentPrice / trade.entry;
    for (const level of settings.takeProfitLevels) {
        if (multiplier >= level.multiplier && trade.sold < level.targetSold) {
            const sellPct = Math.round((level.targetSold - trade.sold) * 100);
            if (sellPct > 0) {
                await sellToken(contract, sellPct, `${level.multiplier}x take profit`, settings, trades);
            }
            return;
        }
    }

    if (multiplier >= settings.trailingStartMultiplier) {
        if (currentPrice <= trade.high * settings.trailingStopFactor && trade.sold < 1) {
            const remaining = Math.round((1 - trade.sold) * 100);
            if (remaining > 0) {
                await sellToken(contract, remaining, "Trailing stop hit", settings, trades);
            }
            return;
        }
    }

    if (currentPrice <= trade.entry * settings.hardStopFactor && trade.sold < 1) {
        const remaining = Math.round((1 - trade.sold) * 100);
        if (remaining > 0) {
            await sellToken(contract, remaining, "Hard stop loss", settings, trades);
        }
        return;
    }

    const heldMs = Date.now() - trade.openedAt;
    if (heldMs > settings.maxHoldSeconds * 1000 && multiplier < settings.timeExitMultiplier) {
        const remaining = Math.round((1 - trade.sold) * 100);
        if (remaining > 0) {
            await sellToken(contract, remaining, "Time-based exit", settings, trades);
        }
    }
};

const monitorTrades = async () => {
    const settings = await getSettings();
    const state = await getState();
    const trades = state.trades || {};

    const contracts = Object.keys(trades);
    for (const contract of contracts) {
        const trade = trades[contract];
        if (!trade || trade.sold >= 1) continue;

        let currentPrice = 0;
        try {
            currentPrice = await fetchPrice(contract, settings.heliusApiKey);
        } catch (err) {
            console.warn("Price fetch failed:", err);
            continue;
        }

        if (currentPrice <= 0) continue;
        if (trade.entry <= 0) {
            trade.entry = currentPrice;
            trade.high = currentPrice;
        }
        trade.high = Math.max(trade.high, currentPrice);
        trade.lastPrice = currentPrice;

        await evaluateSell(contract, currentPrice, settings, trades);
    }

    await saveState({ trades });
};

chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === "monitorTrades") {
        monitorTrades().catch(err => console.error("Monitor error:", err));
    }
});

chrome.runtime.onInstalled.addListener(() => {
    chrome.alarms.create("monitorTrades", { periodInMinutes: 1 });
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    (async () => {
        console.log("📩 Received message from content script:", msg);

        if (!msg.message) {
            sendResponse({ status: "No message provided." });
            return;
        }

        const { messages } = await new Promise(resolve => {
            chrome.storage.local.get({ messages: [] }, resolve);
        });
        messages.push(msg);
        await saveState({ messages });

        const settings = await getSettings();
        const state = await getState();
        const seenContracts = new Set(state.seenContracts || []);
        const trades = state.trades || {};

        const contracts = extractContracts(msg.message);
        for (const contract of contracts) {
            if (seenContracts.has(contract)) continue;
            seenContracts.add(contract);
            try {
                await buyToken(contract, settings, trades);
            } catch (err) {
                console.error("Buy failed:", err);
            }
        }

        await saveState({
            trades,
            seenContracts: Array.from(seenContracts),
            messages
        });

        sendResponse({ status: "✅ Message processed." });
    })();

    return true;
});
