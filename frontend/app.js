const pointsEl = document.getElementById('points');
const tapBtn = document.getElementById('tapBtn');
const msgEl = document.getElementById('msg');

tapBtn.addEventListener('click', async () => {
  try {
    const init_data = window.Telegram?.WebApp?.initData;
    const platform = window.Telegram?.WebApp?.platform || 'unknown';

    if (!init_data) {
      msgEl.innerText = 'Error: Telegram initData missing';
      return;
    }

    const res = await axios.post(`${API_BASE}/tap`, {
      init_data,
      platform,
    });

    pointsEl.innerText = res.data.points;
    msgEl.innerText = '';
  } catch (err) {
    if (err.response) {
      msgEl.innerText = 'Error: ' + (err.response.data.error || err.response.statusText);
    } else {
      msgEl.innerText = 'Network error';
    }
  }
});
