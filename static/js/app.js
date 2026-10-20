document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  toggle?.addEventListener('click', () => {
    const open = document.querySelector('#main-nav').classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
    toggle.textContent = open ? '×' : '☰';
  });
  document.querySelectorAll('.mobile-bottom a').forEach(a => {
    const path = new URL(a.href).pathname;
    if (location.pathname === path || (path !== '/' && location.pathname.startsWith(path))) a.classList.add('active');
  });
  document.querySelectorAll('[data-favorite]').forEach(form => form.addEventListener('submit', async e => {
    e.preventDefault();
    const button = form.querySelector('button');
    button.disabled = true;
    try {
      const response = await fetch(form.action, {method:'POST', body:new FormData(form), headers:{'X-Requested-With':'XMLHttpRequest'}});
      if (!response.ok || response.redirected) { window.location.href = form.action; return; }
      const data = await response.json();
      button.textContent = data.saved ? '♥ В избранном' : '♡ Добавить в избранное';
    } catch { button.textContent = 'Не удалось сохранить. Повторить'; }
    finally { button.disabled = false; }
  }));
  const log = document.querySelector('.chat-log');
  if (log) log.scrollTop = log.scrollHeight;
});