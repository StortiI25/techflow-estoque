/* Prévia "Estoque atual -> quantidade -> novo estoque" antes de confirmar a movimentação */
(function () {
  const box = document.getElementById('previewBox');
  if (!box) return;
  const tipo = box.dataset.tipo; // entrada | saida | ajuste
  const sel = document.getElementById('produto_id');
  const qtd = document.getElementById(tipo === 'ajuste' ? 'novo_estoque' : 'quantidade');
  const aviso = document.getElementById('previewAviso');
  const btn = document.getElementById('btnConfirmar');
  const f = (id) => document.getElementById(id);
  let atual = null, unidade = '';

  async function carregarProduto() {
    atual = null;
    if (!sel.value) { render(); return; }
    try {
      const r = await fetch(`/api/produtos/${sel.value}`);
      if (!r.ok) throw 0;
      const p = await r.json();
      atual = p.estoque; unidade = p.unidade;
    } catch (e) { aviso.textContent = 'Não foi possível consultar o estoque atual.'; }
    render();
  }

  function render() {
    const q = parseInt(qtd.value, 10);
    f('pvAtual').textContent = atual === null ? '—' : `${atual} ${unidade}`;
    let delta = null, novo = null, erro = '';
    if (atual !== null && !isNaN(q)) {
      if (tipo === 'ajuste') { delta = q - atual; novo = q; if (q < 0) erro = 'O estoque não pode ficar negativo.'; else if (delta === 0) erro = 'O novo estoque é igual ao atual.'; }
      else if (tipo === 'entrada') { delta = q; novo = atual + q; if (q <= 0) erro = 'Informe uma quantidade maior que zero.'; }
      else { delta = -q; novo = atual - q; if (q <= 0) erro = 'Informe uma quantidade maior que zero.'; else if (q > atual) erro = `Estoque insuficiente. Disponível: ${atual} unidades.`; }
    }
    f('pvQtd').textContent = delta === null ? '—' : (delta > 0 ? '+' : '') + delta;
    f('pvNovo').textContent = novo === null || erro ? '—' : `${novo} ${unidade}`;
    aviso.textContent = erro;
    box.classList.toggle('invalid', !!erro);
    btn.disabled = !!erro || atual === null || isNaN(q);
  }
  sel.addEventListener('change', carregarProduto);
  qtd.addEventListener('input', render);
  carregarProduto();
})();
