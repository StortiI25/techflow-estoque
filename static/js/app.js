/* TechFlow Estoque - comportamento global */
(function () {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const toggle = (open) => {
    if (!sidebar) return;
    sidebar.classList.toggle('open', open);
    backdrop.classList.toggle('show', open);
  };
  document.getElementById('menuBtn')?.addEventListener('click', () => toggle(!sidebar.classList.contains('open')));
  backdrop?.addEventListener('click', () => toggle(false));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') toggle(false); });

  document.getElementById('searchToggle')?.addEventListener('click', () => {
    const box = document.getElementById('globalSearch');
    box.classList.toggle('show-mobile');
    if (box.classList.contains('show-mobile')) box.querySelector('input').focus();
  });

  // Confirmação em modal para ações destrutivas: <form data-confirm="Mensagem">
  const modalEl = document.getElementById('confirmModal');
  if (modalEl && window.bootstrap) {
    const modal = new bootstrap.Modal(modalEl);
    let formAlvo = null;
    document.addEventListener('submit', (e) => {
      const f = e.target;
      if (f.dataset.confirm && !f.dataset.confirmado) {
        e.preventDefault();
        formAlvo = f;
        document.getElementById('confirmTitle').textContent = f.dataset.confirmTitle || 'Confirmar ação';
        document.getElementById('confirmText').textContent = f.dataset.confirm;
        modal.show();
      }
    }, true);
    document.getElementById('confirmOk').addEventListener('click', () => {
      if (formAlvo) { formAlvo.dataset.confirmado = '1'; modal.hide(); formAlvo.requestSubmit(); }
    });
  }

  // Estado de carregamento: evita duplo envio
  document.addEventListener('submit', (e) => {
    const f = e.target;
    if (e.defaultPrevented || f.method.toLowerCase() !== 'post') return;
    const btn = f.querySelector('button[type=submit]:not([data-no-loading])');
    if (btn && !btn.classList.contains('btn-loading')) {
      btn.classList.add('btn-loading');
      btn.dataset.label = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Salvando...';
      setTimeout(() => { btn.classList.remove('btn-loading'); btn.innerHTML = btn.dataset.label; }, 15000);
    }
  });

  // Mensagens de sucesso somem sozinhas
  document.querySelectorAll('.alert-success').forEach((el) => setTimeout(() => window.bootstrap?.Alert.getOrCreateInstance(el).close(), 6000));

  // Validação nativa do navegador com estilo Bootstrap
  document.querySelectorAll('form.needs-validation').forEach((form) => {
    form.addEventListener('submit', (e) => { if (!form.checkValidity()) { e.preventDefault(); e.stopPropagation(); } form.classList.add('was-validated'); });
  });
})();
