/* Gráficos do dashboard: dados reais vindos das APIs do backend */
(function () {
  const COLORS = ['#2563EB', '#16A34A', '#F59E0B', '#6366F1', '#06B6D4', '#EF4444', '#84CC16', '#EC4899'];
  const elMov = document.getElementById('chartMov');
  const elCat = document.getElementById('chartCat');
  if (!window.Chart) {
    document.querySelectorAll('.chart-error').forEach((e) => (e.style.display = 'grid'));
    return;
  }
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.color = '#64748B';

  let chartMov;
  async function carregarMov(dias) {
    const box = elMov.parentElement, erro = box.querySelector('.chart-error');
    box.classList.add('skeleton'); erro.style.display = 'none';
    try {
      const r = await fetch(`/api/dashboard/movimentacoes?dias=${dias}`, { headers: { Accept: 'application/json' } });
      if (!r.ok) throw new Error(r.status);
      const d = await r.json();
      box.classList.remove('skeleton');
      const ctx = elMov.getContext('2d');
      const grad = (cor) => { const g = ctx.createLinearGradient(0, 0, 0, 260); g.addColorStop(0, cor + '33'); g.addColorStop(1, cor + '00'); return g; };
      const ds = [
        { label: 'Entradas', data: d.entradas, borderColor: '#16A34A', backgroundColor: grad('#16A34A'), fill: true, tension: .35, pointRadius: dias > 7 ? 0 : 4, pointBackgroundColor: '#16A34A' },
        { label: 'Saídas', data: d.saidas, borderColor: '#EF4444', backgroundColor: grad('#EF4444'), fill: true, tension: .35, pointRadius: dias > 7 ? 0 : 4, pointBackgroundColor: '#EF4444' },
      ];
      if (chartMov) { chartMov.data.labels = d.rotulos; chartMov.data.datasets = ds; chartMov.update(); return; }
      chartMov = new Chart(ctx, {
        type: 'line', data: { labels: d.rotulos, datasets: ds },
        options: {
          responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
          plugins: { legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 8 } } },
          scales: { y: { beginAtZero: true, grid: { color: '#EEF2F7' }, ticks: { precision: 0 } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } } },
        },
      });
    } catch (e) { box.classList.remove('skeleton'); erro.style.display = 'grid'; }
  }
  if (elMov) {
    carregarMov(7);
    document.getElementById('periodoMov')?.addEventListener('change', (e) => carregarMov(parseInt(e.target.value, 10)));
  }

  if (elCat) {
    const dados = JSON.parse(elCat.dataset.dados || '[]');
    if (dados.length) {
      new Chart(elCat, {
        type: 'doughnut',
        data: { labels: dados.map((d) => d.nome), datasets: [{ data: dados.map((d) => d.produtos), backgroundColor: COLORS, borderWidth: 2, borderColor: '#fff' }] },
        options: { cutout: '68%', plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.parsed} produtos` } } } },
      });
    }
  }
})();
