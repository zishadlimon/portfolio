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

  // Pull live Google Scholar stats (papers / h-index / citations) from
  // data/citations.json, which is kept fresh by a scheduled GitHub Action
  // (see .github/workflows/update-citations.yml). If the fetch fails for
  // any reason, the hardcoded data-target values already in the HTML are
  // used as a fallback, so the page never breaks or shows blanks.
  async function loadLiveCitationStats(){
    try{
      const res = await fetch('data/citations.json', {cache: 'no-store'});
      if(!res.ok) throw new Error('citations.json fetch failed: ' + res.status);
      const data = await res.json();

      const fieldByStat = {papers: 'papers', hindex: 'h_index', citations: 'citations'};
      document.querySelectorAll('.count-up[data-stat]').forEach((el) => {
        const field = fieldByStat[el.getAttribute('data-stat')];
        const value = field ? data[field] : undefined;
        if(typeof value === 'number' && !Number.isNaN(value)){
          el.setAttribute('data-target', value);
        }
      });

      const citationCountEl = document.getElementById('citation-count');
      if(citationCountEl && typeof data.citations === 'number'){
        citationCountEl.textContent = data.citations;
      }

      const updatedEl = document.getElementById('stats-updated');
      if(updatedEl && data.updated_at){
        const d = new Date(data.updated_at);
        if(!Number.isNaN(d.getTime())){
          const formatted = d.toLocaleDateString('en-US', {year: 'numeric', month: 'short', day: 'numeric'});
          updatedEl.textContent = 'Stats auto-updated from Google Scholar · ' + formatted;
        }
      }
    } catch(err){
      console.warn('Live citation stats unavailable, showing fallback values.', err);
    }
  }

  // Hero stat count-up animation
  (async function(){
    // Wait for (or fail past) the live-stats fetch before reading
    // data-target, so the animation counts up to the current numbers
    // rather than the hardcoded fallback and then silently jumping.
    await loadLiveCitationStats();

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
