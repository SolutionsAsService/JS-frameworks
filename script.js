/* The light and dark toggle from the first version of this site. The page already has its theme before it paints
   (a tiny inline script in the head); this wires the button and remembers the choice in this browser only. */
(function () {
  var root = document.documentElement, btn = document.getElementById('theme-toggle');
  if (!btn) return;
  function apply(theme) {
    root.setAttribute('data-theme', theme);
    btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    btn.querySelector('.lbl').textContent = theme === 'dark' ? 'Light' : 'Dark';
  }
  apply(root.getAttribute('data-theme') || 'light');
  btn.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('theme', next); } catch (e) { /* storage blocked: the choice lasts for this page */ }
    apply(next);
  });
})();
