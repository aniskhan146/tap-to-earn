const backendURL = "https://tap-to-earn-18kw.onrender.com";

document.getElementById("mineBtn").addEventListener("click", () => {
    const username = document.getElementById("username").value;
    if (!username) {
        alert("Please enter username");
        return;
    }

    fetch(`${backendURL}/mine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("status").innerText = data.message;
        document.getElementById("balance").innerText = "Balance: " + data.new_balance;
    });
});
