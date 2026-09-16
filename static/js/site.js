const menu = document.querySelector('.menu-button');
const navigation = document.querySelector('#navigation');
const scrim = document.querySelector('.nav-scrim');
const closeButton = document.querySelector('.rail-close');

function setMenu(open) {
  menu?.setAttribute('aria-expanded', String(open));
  navigation?.classList.toggle('is-open', open);
  scrim?.classList.toggle('is-open', open);
  document.body.classList.toggle('nav-open', open);
}
menu?.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
closeButton?.addEventListener('click', () => setMenu(false));
scrim?.addEventListener('click', () => setMenu(false));
window.addEventListener('keydown', (event) => { if (event.key === 'Escape') setMenu(false); });

document.querySelector('.copy-link')?.addEventListener('click', async (event) => {
  try { await navigator.clipboard.writeText(location.href); event.target.textContent = 'Link copied'; }
  catch { event.target.textContent = 'Copy the address from your browser'; }
});
