console.log("✅ Discord Message Listener Injected!");

// Function to observe new messages
const observeMessages = () => {
    const chatContainer = document.querySelector('[data-list-id="chat-messages"]');

    if (!chatContainer) {
        console.warn("⚠️ Chat container not found. Retrying...");
        setTimeout(observeMessages, 1000);
        return;
    }

    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1 && node.querySelector) {
                    let username = node.querySelector("h3 span")?.innerText.trim() || "Unknown";
                    let messageElement = node.querySelector("div[id^='message-content-']");
                    let messageText = messageElement ? messageElement.innerText.trim() : "";

                    if (messageText) {
                        console.log(`📩 New Message - [${username}]: ${messageText}`);

                        // ✅ Ensure `background.js` exists before sending message
                        chrome.runtime.sendMessage({
                            username: username,
                            message: messageText
                        }).catch(err => {
                            console.error("❌ Failed to send message to background script:", err);
                        });
                    }
                }
            });
        });
    });

    observer.observe(chatContainer, { childList: true, subtree: true });
};

// Start observing messages
observeMessages();
