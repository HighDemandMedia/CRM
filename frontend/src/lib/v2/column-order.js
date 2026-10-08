/** Move a column to a gap in the original order (before 0 through after length). */
export function insertColumn(keys, key, gap) {
  const source = keys.indexOf(key);
  if (source < 0 || gap < 0 || gap > keys.length) return keys;
  const next = keys.filter((value) => value !== key);
  next.splice(gap > source ? gap - 1 : gap, 0, key);
  return next;
}

/**
 * Reorder data columns inside a scroll region. Selection/action columns are
 * intentionally excluded. Persist through the caller's existing preferences.
 * @param {HTMLElement} node
 * @param {{keys: string[], onChange: (keys: string[]) => void}} options
 */
export function columnOrder(node, options) {
  let dragging = '';
  let suppressClick = false;
  let resetTimer;
  const headers = () => Array.from(node.querySelectorAll('th[data-column]'));
  function clearMarkers() {
    for (const header of headers()) {
      header.removeAttribute('data-column-source');
      header.removeAttribute('data-column-insert');
    }
  }
  function finish() {
    dragging = '';
    clearMarkers();
    clearTimeout(resetTimer);
    resetTimer = setTimeout(() => (suppressClick = false), 0);
  }
  function headerFor(event) {
    return event.target instanceof Element ? event.target.closest('th[data-column]') : null;
  }
  function start(event) {
    const header = headerFor(event);
    const key = header?.getAttribute('data-column');
    if (!key || !options.keys.includes(key)) return;
    dragging = key;
    suppressClick = true;
    header.setAttribute('data-column-source', 'true');
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', key);
    }
  }
  function position(event) {
    const cells = headers();
    const index = cells.findIndex((cell) => {
      const rect = cell.getBoundingClientRect();
      return event.clientX < rect.left + rect.width / 2;
    });
    return index < 0 ? cells.length : index;
  }
  function over(event) {
    if (!dragging) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    const cells = headers();
    const gap = position(event);
    for (const cell of cells) cell.removeAttribute('data-column-insert');
    (cells[gap] ?? cells.at(-1))?.setAttribute(
      'data-column-insert',
      gap === cells.length ? 'after' : 'before'
    );
    const rect = node.getBoundingClientRect();
    if (event.clientX > rect.right - 30) node.scrollLeft += 18;
    else if (event.clientX < rect.left + 30) node.scrollLeft -= 18;
  }
  function drop(event) {
    if (!dragging) return;
    event.preventDefault();
    options.onChange(insertColumn(options.keys, dragging, position(event)));
    finish();
  }
  function keyboard(event) {
    if (!event.altKey || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    const key = headerFor(event)?.getAttribute('data-column');
    const index = options.keys.indexOf(key);
    if (index < 0) return;
    event.preventDefault();
    const gap = index + (event.key === 'ArrowLeft' ? -1 : 2);
    options.onChange(insertColumn(options.keys, key, gap));
  }
  function click(event) {
    // A drag must not also activate Ticket's click-to-sort handler.
    if (suppressClick && headerFor(event)) {
      event.preventDefault();
      event.stopPropagation();
    }
  }
  const handlers = { dragstart: start, dragover: over, drop, dragend: finish, keydown: keyboard };
  for (const [name, handler] of Object.entries(handlers)) node.addEventListener(name, handler);
  node.addEventListener('click', click, true);
  return {
    update(next) {
      options = next;
    },
    destroy() {
      clearTimeout(resetTimer);
      for (const [name, handler] of Object.entries(handlers))
        node.removeEventListener(name, handler);
      node.removeEventListener('click', click, true);
      clearMarkers();
    }
  };
}
