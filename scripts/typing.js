(() => {
  const target = document.getElementById('typing-text');
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (!target) return;
  const phrases = [
    'Building AI & data solutions',
    'Connecting tech with finance',
    'Solving business problems',
  ];
  let phrase = 0;
  let length = phrases[0].length;
  let deleting = true;
  let timer;
  function tick() {
    if (deleting) {
      length--;
      target.textContent = phrases[phrase].slice(0, length);
      if (length === 0) {
        phrase = (phrase + 1) % phrases.length;
        deleting = false;
        timer = setTimeout(tick, 300);
        return;
      }
    } else {
      length++;
      target.textContent = phrases[phrase].slice(0, length);
      if (length === phrases[phrase].length) {
        deleting = true;
        timer = setTimeout(tick, 2000);
        return;
      }
    }
    timer = setTimeout(tick, deleting ? 35 : 75);
  }
  function reset() {
    clearTimeout(timer);
    phrase = 0;
    length = phrases[0].length;
    deleting = true;
    target.textContent = phrases[0];
    if (!motion.matches) timer = setTimeout(tick, 2200);
  }
  motion.addEventListener('change', reset);
  reset();
})();
