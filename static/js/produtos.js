/* Detalhes do produto: gráfico de evolução do estoque; formulário: prévia de imagem */
(function () {
  const el = document.getElementById('chartEvolucao');
  if (el && window.Chart) {
    const box = el.parentElement, msg = box.querySelector('.chart-msg');
    box.classList.add('skeleton');
    fetch(`/api/produtos/${el.dataset.id}/evolucao`).then((r) => { if (!r.ok) throw 0; return r.json(); }).then((pts) => {
      box.classList.remove('skeleton');
      if (!pts.length) { msg.style.display = 'grid'; el.style.display = 'none'; return; }
      new Chart(el, {
        type: 'line',
        data: { labels: pts.map((p) => p.data.slice(8, 10) + '/' + p.data.slice(5, 7)), datasets: [{ label: 'Estoque', data: pts.map((p) => p.estoque), borderColor: '#2563EB', backgroundColor: '#2563EB22', fill: true, stepped: true, pointRadius: 2 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, grid: { color: '#EEF2F7' }, ticks: { precision: 0 } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } } } },
      });
    }).catch(() => { box.classList.remove('skeleton'); msg.textContent = 'Não foi possível carregar o gráfico.'; msg.style.display = 'grid'; el.style.display = 'none'; });
  }
  const input = document.getElementById('imagem'), prev = document.getElementById('imgPreview');
  if (input && prev) input.addEventListener('change', () => { const f = input.files[0]; if (f) { prev.src = URL.createObjectURL(f); prev.style.display = 'block'; } });
})();
