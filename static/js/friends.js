async function addFriend() {
    const input = document.getElementById('friend-username');
    const msgEl = document.getElementById('add-message');
    const username = input.value.trim();

    if (!username) return;

    msgEl.textContent = '';
    msgEl.style.color = '';

    try {
        const resp = await fetch('/friends/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username }),
        });
        const data = await resp.json();

        if (resp.ok) {
            msgEl.style.color = '#2ecc71';
            msgEl.textContent = data.message;
            input.value = '';
        } else {
            msgEl.style.color = '#e74c3c';
            msgEl.textContent = data.error;
        }
    } catch (err) {
        msgEl.style.color = '#e74c3c';
        msgEl.textContent = '网络错误，请重试';
    }
}

async function acceptFriend(friendshipId) {
    try {
        const resp = await fetch(`/friends/accept/${friendshipId}`, { method: 'POST' });
        const data = await resp.json();

        if (resp.ok) {
            location.reload();
        } else {
            alert(data.error);
        }
    } catch (err) {
        alert('网络错误，请重试');
    }
}

async function rejectFriend(friendshipId) {
    try {
        const resp = await fetch(`/friends/reject/${friendshipId}`, { method: 'POST' });
        const data = await resp.json();

        if (resp.ok) {
            const el = document.getElementById(`pending-${friendshipId}`);
            if (el) el.remove();
        } else {
            alert(data.error);
        }
    } catch (err) {
        alert('网络错误，请重试');
    }
}
