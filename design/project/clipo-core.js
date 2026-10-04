(function () {
  const PLATFORMS = [
    { id: 'youtube', name: 'YouTube', mono: 'YT', re: /youtu\.?be/, sample: 'https://youtube.com/playlist?list=PLx9mR2', ph: 'youtube.com/watch?v=…' },
    { id: 'instagram', name: 'Instagram', mono: 'IG', re: /instagram|instagr\.am/, sample: 'https://www.instagram.com/reel/C8kPz1sLq/', ph: 'instagram.com/reel/…' },
    { id: 'facebook', name: 'Facebook', mono: 'FB', re: /facebook|fb\.watch/, sample: 'https://fb.watch/q2Lk9vN0/', ph: 'fb.watch/…' },
    { id: 'tiktok', name: 'TikTok', mono: 'TT', re: /tiktok/, sample: 'https://www.tiktok.com/@cocina.rapida/video/73912', ph: 'tiktok.com/@usuario/video/…' },
    { id: 'x', name: 'X', mono: 'X', re: /(^|\/\/|\.)(x|twitter)\.com/, sample: 'https://x.com/espacio/status/18233', ph: 'x.com/usuario/status/…' },
    { id: 'vimeo', name: 'Vimeo', mono: 'VI', re: /vimeo/, sample: 'https://vimeo.com/824155', ph: 'vimeo.com/…' },
    { id: 'reddit', name: 'Reddit', mono: 'RD', re: /reddit|redd\.it/, sample: 'https://www.reddit.com/r/videos/comments/1f2x', ph: 'reddit.com/r/…' },
    { id: 'soundcloud', name: 'SoundCloud', mono: 'SC', re: /soundcloud/, sample: 'https://soundcloud.com/trio/sesion-en-vivo', ph: 'soundcloud.com/…' },
    { id: 'other', name: 'Otros', mono: '+', re: null, sample: 'https://www.twitch.tv/videos/21933', ph: 'Cualquier enlace compatible' },
  ];
  const SINGLE_YT = 'https://youtu.be/dQx7Lm2Kp9A';
  const META = {
    youtube: { title: 'Cómo hacer pan de masa madre en casa', author: 'Hornea Conmigo', duration: '18:42', mb: 1 },
    instagram: { title: 'Atardecer en Valle de Bravo', author: '@viajes.mx · Reel', duration: '0:34', mb: 0.05 },
    facebook: { title: 'Resumen del partido: goles y mejores jugadas', author: 'Deportes Hoy', duration: '4:12', mb: 0.25 },
    tiktok: { title: 'Tacos al pastor en 60 segundos', author: '@cocina.rapida', duration: '0:58', mb: 0.07 },
    x: { title: 'Lanzamiento visto desde la estación', author: '@espacio', duration: '1:20', mb: 0.1 },
    vimeo: { title: 'Cortometraje: La última estación', author: 'Estudio Ámbar', duration: '12:05', mb: 0.7 },
    reddit: { title: 'Mi gato aprendió a abrir la puerta', author: 'r/videos', duration: '0:45', mb: 0.05 },
    soundcloud: { title: 'Sesión en vivo — Noches de Jazz', author: 'Trío Nocturno', duration: '42:10', mb: 0 },
    other: { title: 'Directo: maratón de diseño', author: 'twitch.tv', duration: '2:14:00', mb: 3 },
  };
  const PLAYLIST = {
    title: 'Panadería desde cero', author: 'Hornea Conmigo · Playlist', mb: 0.6,
    items: [
      ['Masa madre: día 1', '12:10'], ['Alimentar el fermento', '8:32'], ['Harinas y hidratación', '15:04'],
      ['Amasado sin máquina', '10:47'], ['Formado de hogazas', '13:20'], ['Horneado en olla', '9:55'],
      ['Baguettes caseras', '17:38'], ['Errores comunes', '11:02'],
    ],
  };
  const VQ = [
    { id: '2160', label: '2160p', sub: '4K', base: 1450 },
    { id: '1080', label: '1080p', sub: 'Full HD', base: 420, note: 'Recomendado' },
    { id: '720', label: '720p', sub: 'HD', base: 190 },
    { id: '480', label: '480p', sub: 'SD', base: 95 },
  ];
  const AQ = [
    { id: '320', label: '320 kbps', sub: 'Máxima', base: 44, note: 'Recomendado' },
    { id: '192', label: '192 kbps', sub: 'Alta', base: 26 },
    { id: '128', label: '128 kbps', sub: 'Ligera', base: 17 },
  ];
  const VF = ['MP4', 'WEBM', 'MKV'];
  const AF = ['MP3', 'M4A', 'OPUS'];
  const CONC = 2;

  const DEFAULTS = {
    tab: 'home', view: 'home', url: '', platform: null, analyzing: false, sampleIdx: 0,
    mode: 'video', quality: '1080', format: 'MP4', playlist: false, plSel: PLAYLIST.items.map(() => true),
    detailId: null, toast: null,
    queue: [
      { id: 1, mono: 'YT', title: 'Lo-fi para estudiar — 3 horas', spec: '320 kbps · MP3', size: 412, progress: 100, status: 'done', mode: 'audio' },
      { id: 2, mono: 'TT', title: 'Receta de chilaquiles verdes', spec: '1080p · MP4', size: 38, progress: 100, status: 'done', mode: 'video' },
    ],
  };

  const detect = url => {
    if (!url) return null;
    const p = PLATFORMS.find(p => p.re && p.re.test(url.toLowerCase()));
    return p ? p.id : 'other';
  };
  const fmtMB = v => v >= 1000 ? (v / 1000).toFixed(1).replace('.', ',') + ' GB' : Math.max(1, Math.round(v)) + ' MB';
  const st = self => Object.assign({}, DEFAULTS, self.state);

  function stagesFor(q) {
    const p = q.progress;
    const list = q.mode === 'audio'
      ? [['Extrayendo información', 0, 8], ['Descargando audio', 8, 85], ['Convirtiendo', 85, 100]]
      : [['Extrayendo información', 0, 8], ['Descargando video', 8, 70], ['Descargando audio', 70, 90], ['Uniendo con ffmpeg', 90, 100]];
    return list.map(([label, a, b]) => ({ label, state: p >= b || q.status === 'done' ? 'done' : p >= a && q.status !== 'waiting' ? 'active' : 'pending' }));
  }

  function start(self) {
    const sp = self.props && self.props.startScreen;
    if (sp === 'options') analyze(self, PLATFORMS[0].sample, true);
    if (sp === 'queue') self.setState({ tab: 'queue' });
    self.forceUpdate();
    return setInterval(() => {
      const s = st(self);
      if (!s.queue.some(q => q.status === 'running' || q.status === 'waiting')) return;
      let q = s.queue.map(q => {
        if (q.status !== 'running') return q;
        const p = Math.min(100, q.progress + 1.5 + Math.random() * 4.5);
        return Object.assign({}, q, { progress: p, speed: (2 + Math.random() * 4).toFixed(1).replace('.', ','), status: p >= 100 ? 'done' : 'running' });
      });
      let running = q.filter(x => x.status === 'running').length;
      const promote = new Set(q.filter(x => x.status === 'waiting').sort((a, b) => a.id - b.id).slice(0, Math.max(0, CONC - running)).map(x => x.id));
      q = q.map(x => promote.has(x.id) ? Object.assign({}, x, { status: 'running' }) : x);
      self.setState({ queue: q });
    }, 450);
  }

  function flash(self, msg) {
    clearTimeout(self._tt);
    self.setState({ toast: msg });
    self._tt = setTimeout(() => self.setState({ toast: null }), 2200);
  }

  function analyze(self, url, instant) {
    const platform = detect(url);
    const audio = platform === 'soundcloud';
    const playlist = /list=|\/sets\//.test(url);
    const go = () => self.setState({ analyzing: false, view: 'options', playlist, plSel: PLAYLIST.items.map(() => true),
      mode: audio ? 'audio' : 'video', quality: audio ? '320' : '1080', format: audio ? 'MP3' : 'MP4' });
    self.setState({ url, platform, analyzing: !instant });
    if (instant) go(); else setTimeout(go, 1100);
  }

  function vals(self, T) {
    const s = st(self);
    const pick = (group, on) => (T[group] || {})[on ? 'on' : 'off'] || {};
    const div = i => i === 0 ? 'none' : (T.divider || '1px solid currentColor');
    const pl = PLATFORMS.find(p => p.id === s.platform);
    const m0 = META[s.platform || 'youtube'];
    const mbFactor = s.playlist ? PLAYLIST.mb : m0.mb;
    const selCount = s.plSel.filter(Boolean).length;
    const nItems = s.playlist ? selCount : 1;
    const qs = s.mode === 'video' ? VQ : AQ;
    const fs = s.mode === 'video' ? VF : AF;
    const qSel = qs.find(q => q.id === s.quality) || qs[0];
    const sizeOne = base => s.mode === 'audio' ? base * Math.max(mbFactor, 0.4) : base * mbFactor;
    const spec = (s.mode === 'video' ? s.quality + 'p' : s.quality + ' kbps') + ' · ' + s.format;
    const active = s.queue.filter(q => q.status !== 'done');
    const done = s.queue.filter(q => q.status === 'done');
    const screen = s.tab === 'home' ? s.view : (s.detailId ? 'progress' : 'queue');
    const detail = s.queue.find(q => q.id === s.detailId) || s.queue[0];
    const setQ = (id, fn) => self.setState(x => ({ queue: st({ state: x }).queue.map(q => q.id === id ? Object.assign({}, q, fn(q)) : q) }));
    const togglePause = q => setQ(q.id, x => ({ status: x.status === 'paused' ? 'running' : (x.status === 'running' || x.status === 'waiting') ? 'paused' : x.status }));
    const cancel = q => { self.setState(x => ({ queue: st({ state: x }).queue.filter(y => y.id !== q.id), detailId: null })); flash(self, 'Descarga cancelada'); };
    const statusLabel = q => q.status === 'done' ? 'Completado' : q.status === 'paused' ? 'En pausa' : q.status === 'waiting' ? 'En espera' : q.speed ? q.speed + ' MB/s' : 'Iniciando…';
    const eta = q => {
      if (q.status === 'done') return 'Listo';
      if (q.status !== 'running' || !q.speed) return '—';
      const secs = Math.max(1, Math.round((q.size * (100 - q.progress) / 100) / parseFloat(q.speed.replace(',', '.'))));
      return secs >= 60 ? Math.floor(secs / 60) + ' min ' + (secs % 60) + ' s' : secs + ' s';
    };
    const qItem = q => Object.assign({}, q, {
      pct: Math.round(q.progress) + '%', pctNum: Math.round(q.progress),
      sizeLabel: Math.round(q.size * q.progress / 100) + ' de ' + fmtMB(q.size),
      status: statusLabel(q), meta: q.spec, eta: eta(q),
      paused: q.status === 'paused', running: q.status === 'running', waiting: q.status === 'waiting', isDone: q.status === 'done', notDone: q.status !== 'done',
      pauseLabel: q.status === 'paused' ? 'Reanudar' : 'Pausar',
      onPause: () => togglePause(q), onCancel: () => cancel(q),
      onOpen: () => self.setState({ tab: 'queue', detailId: q.id }),
    });
    const anyRunning = active.some(q => q.status === 'running' || q.status === 'waiting');

    return {
      glow: (T.glow || {})[s.platform || 'none'],
      isHome: screen === 'home', isOptions: screen === 'options', isProgress: screen === 'progress', isQueue: screen === 'queue',
      showGrid: self.props.showPlatformGrid ?? true,
      url: s.url, hasUrl: !!s.url,
      placeholder: pl ? pl.ph : 'Pega un enlace o playlist',
      onUrl: e => { const url = e.target.value; self.setState({ url, platform: detect(url) }); },
      onPaste: () => {
        const p = s.platform && !s.url ? PLATFORMS.find(x => x.id === s.platform) : PLATFORMS[s.sampleIdx % PLATFORMS.length];
        const url = p.id === 'youtube' && s.sampleIdx % 2 ? SINGLE_YT : p.sample;
        self.setState({ url, platform: detect(url), sampleIdx: s.sampleIdx + 1 });
      },
      onClear: () => self.setState({ url: '', platform: null }),
      detected: !!s.url && !!pl,
      detectedName: pl ? (pl.id === 'other' ? 'Sitio compatible con yt-dlp' : pl.name) + (/list=|\/sets\//.test(s.url) ? ' · Playlist' : '') : '',
      cantAnalyze: !s.url || s.analyzing, analyzing: s.analyzing,
      analyzeLabel: s.analyzing ? 'Analizando enlace…' : 'Analizar enlace',
      onAnalyze: () => analyze(self, s.url),
      platforms: PLATFORMS.map(p => Object.assign({}, p, pick('tile', s.platform === p.id), {
        on: s.platform === p.id,
        onClick: () => self.setState({ platform: p.id, url: s.url && detect(s.url) === p.id ? s.url : '' }),
      })),
      onBack: () => self.setState({ view: 'home' }),
      meta: s.playlist
        ? { title: PLAYLIST.title, author: PLAYLIST.author, duration: PLAYLIST.items.length + ' videos', platformName: 'YouTube', mono: 'YT' }
        : Object.assign({}, m0, { platformName: pl ? pl.name : 'YouTube', mono: pl ? pl.mono : 'YT' }),
      isPlaylist: s.playlist, notPlaylist: !s.playlist,
      plItems: PLAYLIST.items.map(([title, duration], i) => Object.assign({ title, duration, n: String(i + 1).padStart(2, '0'), on: s.plSel[i], divider: div(i),
        onClick: () => self.setState({ plSel: s.plSel.map((v, j) => j === i ? !v : v) }) }, pick('check', s.plSel[i]))),
      plSelLabel: selCount + ' de ' + PLAYLIST.items.length + ' seleccionados',
      plAllLabel: selCount === PLAYLIST.items.length ? 'Ninguno' : 'Todos',
      onPlAll: () => self.setState({ plSel: PLAYLIST.items.map(() => selCount !== PLAYLIST.items.length) }),
      modes: [['video', 'Video'], ['audio', 'Solo audio']].map(([id, label]) => Object.assign({ label, on: s.mode === id,
        onClick: () => self.setState({ mode: id, quality: id === 'video' ? '1080' : '320', format: id === 'video' ? 'MP4' : 'MP3' }) }, pick('mode', s.mode === id))),
      qualities: qs.map((q, i) => Object.assign({ label: q.label, sub: q.sub, size: fmtMB(sizeOne(q.base) * nItems), hasNote: !!q.note, note: q.note, on: q.id === qSel.id, divider: div(i),
        onClick: () => self.setState({ quality: q.id }) }, pick('q', q.id === qSel.id))),
      formats: fs.map((f, i) => Object.assign({ label: f, on: s.format === f, divider: div(i), onClick: () => self.setState({ format: f }) }, pick('fmt', s.format === f))),
      summary: spec + ' · ' + fmtMB(sizeOne(qSel.base) * nItems),
      dlLabel: s.playlist ? 'Descargar ' + nItems + (nItems === 1 ? ' video' : ' videos') : 'Descargar',
      cantDownload: nItems === 0,
      onDownload: () => {
        const base = Date.now();
        const make = (title, k) => ({ id: base + k, mono: pl ? pl.mono : 'YT', title, spec, mode: s.mode, size: sizeOne(qSel.base) * (0.7 + Math.random() * 0.6), progress: 0, status: 'waiting' });
        const items = s.playlist ? PLAYLIST.items.filter((_, i) => s.plSel[i]).map(([t], k) => make(t, k)) : [make(m0.title, 0)];
        self.setState(x => ({ queue: items.concat(st({ state: x }).queue), tab: s.playlist ? 'queue' : 'queue', detailId: s.playlist ? null : items[0].id, view: 'home', url: '', platform: null }));
        flash(self, s.playlist ? items.length + ' videos añadidos a la cola' : 'Descarga iniciada');
      },
      pd: detail ? qItem(detail) : {},
      stages: detail ? stagesFor(detail).map((g, i) => Object.assign({ label: g.label, n: i + 1, isDone: g.state === 'done', isActive: g.state === 'active', isPending: g.state === 'pending' }, (T.stage || {})[g.state] || {})) : [],
      onCloseDetail: () => self.setState({ detailId: null }),
      onNew: () => self.setState({ tab: 'home', view: 'home', detailId: null }),
      active: active.map((q, i) => Object.assign(qItem(q), { divider: div(i) })),
      activeCount: active.length, noActive: active.length === 0, hasActive: active.length > 0,
      done: done.map((q, i) => Object.assign(qItem(q), { divider: div(i), meta: q.spec + ' · ' + fmtMB(q.size) })),
      doneCount: done.length, hasDone: done.length > 0,
      pauseAllLabel: anyRunning ? 'Pausar todo' : 'Reanudar todo',
      onPauseAll: () => self.setState(x => ({ queue: st({ state: x }).queue.map(q => q.status === 'done' ? q : Object.assign({}, q, { status: anyRunning ? 'paused' : 'waiting' })) })),
      onClearDone: () => self.setState(x => ({ queue: st({ state: x }).queue.filter(q => q.status !== 'done') })),
      hasToast: !!s.toast, toast: s.toast,
      tabs: [['home', 'Inicio'], ['queue', 'Cola']].map(([id, label]) => Object.assign({ label, on: s.tab === id, isHome: id === 'home', isQueue: id === 'queue',
        hasBadge: id === 'queue' && active.length > 0, badge: active.length,
        onClick: () => self.setState({ tab: id, detailId: null, view: id === 'home' && s.tab === 'home' ? 'home' : s.view }) }, pick('tab', s.tab === id))),
    };
  }

  window.ClipoCore = { start, vals };
})();
