(() => {
  const form = document.getElementById('scan-form');
  const input = document.getElementById('isbn-input');
  const status = document.getElementById('scan-status');
  const titleAuthorEl = document.getElementById('book-title-author');
  const dispositionTextEl = document.getElementById('disposition-text');
  const dispositionEl = document.getElementById('disposition');
  const recentScansTable = document.getElementById('recent-scans');
  const recentScansTbody = document.getElementById('recent-scans-body');

  const maxRecentRows = parseInt(recentScansTable.dataset.maxRows, 10) || 3;

  let recentScans = [];

  let inFlight = false;

  // Kiosk-only exception to normal focus-management: this page has
  // exactly one legitimate interactive element (the scanner-fed input).
  function focusInput() {
    if (document.activeElement !== input) input.focus();
  }

  // Single seam to edit if the /api/scan response shape changes.
  function parseScanResponse(json) {
    const r = json.result ?? {};
    const authors = Array.isArray(r.authors) ? r.authors.join(', ') : (r.authors ?? '');
    return {
      title: r.title ?? '(title unknown)',
      authors,
      dispositionLabel: r.disposition ?? 'Unknown',
      dispositionKind: classifyDisposition(r.source, r.disposition),
    };
  }

  // TODO refactor to just send disposition classification from server
  function classifyDisposition(source, label) {
    if (source === 'local') return 'in-collection';
    if (source === 'not_found') return 'not-found';
    if (source) return 'needs-review'; // any configured remote catalog name
    const s = String(label || '').toLowerCase();
    if (s.includes('not found') || s.includes('invalid')) return 'not-found';
    if (s.includes('already in')) return 'in-collection';
    return 'needs-review';
  }

  function renderResult({ title, authors, dispositionLabel, dispositionKind }) {
    titleAuthorEl.textContent = authors ? `${title} — ${authors}` : title;
    dispositionTextEl.textContent = dispositionLabel;
    dispositionEl.dataset.kind = dispositionKind;
  }

  function clearResult() {
    titleAuthorEl.textContent = '';
    dispositionTextEl.textContent = '';
    delete dispositionEl.dataset.kind;
  }

  function renderRecent() {
    recentScansTbody.innerHTML = '';
    recentScans.forEach((row) => {
      const tr = document.createElement('tr');

      const titleTd = document.createElement('td');
      titleTd.textContent = row.title;

      const authorTd = document.createElement('td');
      authorTd.textContent = row.authors;

      const dispositionTd = document.createElement('td');
      dispositionTd.textContent = row.dispositionLabel;

      tr.append(titleTd, authorTd, dispositionTd);
      recentScansTbody.appendChild(tr);
    });
  }

  function addToRecent(parsed) {
    recentScans.unshift(parsed);
    recentScans = recentScans.slice(0, maxRecentRows);
    renderRecent();
  }

  function setStatus(text) {
    status.textContent = text;
  }

  function setPending(isPending) {
    document.body.classList.toggle('is-pending', isPending);
  }

  function setError(message) {
    dispositionEl.dataset.kind = 'error';
    dispositionTextEl.textContent = message;
    titleAuthorEl.textContent = '';
    setStatus(message);
  }

  async function submitIsbn(isbn) {

    // TODO race condition?
    if (inFlight) return;
    inFlight = true;

    clearResult();
    setPending(true);
    setStatus('Looking up scanned item…');

    try {
      const resp = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isbn }),
      });

      const json = await resp.json();

      if (!resp.ok || !json.ok) {
        throw new Error(json.message || `Server error (${resp.status})`);
      }

      const parsed = parseScanResponse(json);
      renderResult(parsed);
      addToRecent(parsed);
      setStatus(`Result: ${parsed.dispositionLabel}`);
    } catch (err) {
      setError('Scan failed — please scan again.');
    } finally {
      inFlight = false;
      setPending(false);
      input.value = '';
      focusInput();
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const isbn = input.value.trim();
    input.value = '';
    if (!isbn) {
      focusInput();
      return;
    }
    submitIsbn(isbn);
  });

  window.addEventListener('load', focusInput);
  document.addEventListener('click', focusInput);
  window.addEventListener('focus', focusInput);
  input.addEventListener('blur', () => {
    setTimeout(focusInput, 50);
  });
})();
