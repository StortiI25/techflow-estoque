/* Filtros no backend: selects enviam o formulário ao mudar; busca com pequeno atraso */
document.querySelectorAll('form.filter-bar').forEach((form) => {
  form.querySelectorAll('select, input[type=date]').forEach((el) => el.addEventListener('change', () => form.requestSubmit()));
  const busca = form.querySelector('input[type=search]');
  if (busca) {
    let t;
    busca.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => form.requestSubmit(), 600); });
    if (busca.value) { busca.focus(); busca.setSelectionRange(busca.value.length, busca.value.length); }
  }
});
