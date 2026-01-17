document.addEventListener("DOMContentLoaded", () => {
    chrome.storage.local.get("messages", data => {
        let messages = data.messages || [];
        console.log("📥 Messages retrieved in popup:", messages);

        let messageContainer = document.getElementById("messages");
        messageContainer.innerHTML = "";

        if (messages.length === 0) {
            messageContainer.innerHTML = "<p>No messages found.</p>";
            return;
        }

        messages.slice(-10).forEach(msg => {
            let msgDiv = document.createElement("div");
            msgDiv.classList.add("message");
            msgDiv.innerHTML = `<strong>${msg.username}</strong>: ${msg.message}`;
            messageContainer.appendChild(msgDiv);
        });
    });
});
