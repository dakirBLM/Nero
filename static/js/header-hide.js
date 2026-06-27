// Shared header hide/show script using requestAnimationFrame
(function(){
  if (typeof window === 'undefined') return;
  let lastScroll = window.scrollY || 0;
  let ticking = false;
  const header = document.querySelector('.main-header');
  if (!header) return;
  const DEADZONE = 8; // ignore tiny moves
  const SHOW_THRESHOLD = 120; // require this much scroll up to force show

  function onScroll(){
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(() => {
      const current = window.scrollY || 0;
      const delta = current - lastScroll;
      if (Math.abs(delta) <= DEADZONE) {
        ticking = false; return;
      }
      if (delta > 0 && current > 40) {
        header.classList.add('main-header--hidden');
        header.classList.remove('main-header--visible');
      } else {
        // scrolling up
        if (lastScroll - current > SHOW_THRESHOLD || current < 40) {
          header.classList.remove('main-header--hidden');
          header.classList.add('main-header--visible');
        }
      }
      lastScroll = current;
      ticking = false;
    });
  }

  window.addEventListener('scroll', onScroll, {passive: true});
  // ensure initial visible class
  header.classList.add('main-header--visible');
})();
