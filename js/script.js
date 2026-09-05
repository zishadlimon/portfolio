  // Active nav highlighting
  const navLinks = document.querySelectorAll('#nav a');
  const sections = [...document.querySelectorAll('main section')];

  function setActive(){
    let current = sections[0].id;
    const scrollPos = window.scrollY + 140;
    const atBottom = (window.innerHeight + window.scrollY) >= (document.documentElement.scrollHeight - 4);

    if(atBottom){
      current = sections[sections.length - 1].id;
    } else {
      for(const s of sections){
        if(s.offsetTop <= scrollPos) current = s.id;
      }
    }
    navLinks.forEach(a=>{
      a.classList.toggle('active', a.getAttribute('href') === '#'+current);
    });
  }
  window.addEventListener('scroll', setActive, {passive:true});
  window.addEventListener('resize', setActive);
  setActive();

  navLinks.forEach(a=>{
    a.addEventListener('click', ()=>{
      navLinks.forEach(l=>l.classList.remove('active'));
      a.classList.add('active');
    });
  });

  // Hero stat count-up animation
  (function(){
    const nodes = document.querySelectorAll('.count-up');
    if(!nodes.length) return;

    function easeOutCubic(t){
      return 1 - Math.pow(1 - t, 3);
    }

    function animate(el){
      const target = parseFloat(el.getAttribute('data-target'));
      const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
      if(isNaN(target)) return;

      const duration = 1800;
      const start = performance.now();

      function step(now){
        const elapsed = now - start;
        const t = Math.min(1, elapsed / duration);
        const eased = easeOutCubic(t);
        const value = target * eased;
        el.textContent = value.toFixed(decimals);
        if(t < 1){
          requestAnimationFrame(step);
        } else {
          el.textContent = target.toFixed(decimals);
        }
      }
      requestAnimationFrame(step);
    }

    const observer = new IntersectionObserver((entries)=>{
      entries.forEach(entry=>{
        if(entry.isIntersecting){
          animate(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, {threshold:0});

    nodes.forEach(n=> observer.observe(n));
  })();
