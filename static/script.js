const form = document.querySelector('#trip-form');
const input = document.querySelector('#user-input');
const submit = document.querySelector('#submit-button');
const loading = document.querySelector('#loading');
const error = document.querySelector('#error');
const results = document.querySelector('#results');
let currentAnswer = '';
let busy = false;

input.addEventListener('input', () => {
  document.querySelector('#char-count').textContent = `${input.value.length} / 4000`;
  input.setCustomValidity('');
});
document.querySelectorAll('[data-prompt]').forEach(button => {
  button.addEventListener('click', () => {
    input.value = button.dataset.prompt;
    input.dispatchEvent(new Event('input'));
    input.focus();
  });
});

// Render a small Markdown subset using text nodes only. Agent HTML is never executed.
function inlineText(element, text) {
  const fragments = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  for (const fragment of fragments) {
    if (fragment.startsWith('**') && fragment.endsWith('**')) {
      const strong = document.createElement('strong');
      strong.textContent = fragment.slice(2, -2);
      element.append(strong);
    } else if (fragment.startsWith('`') && fragment.endsWith('`')) {
      const code = document.createElement('code');
      code.textContent = fragment.slice(1, -1);
      element.append(code);
    } else element.append(document.createTextNode(fragment));
  }
}
function renderAnswer(text) {
  const container = document.querySelector('#answer');
  container.replaceChildren();
  let list = null;
  const lines = text.split('\n');
  const cells = line => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    if (line.includes('|') && lines[index + 1]?.includes('|') && cells(lines[index + 1]).every(cell => /^:?-{3,}:?$/.test(cell))) {
      list = null;
      const wrapper = document.createElement('div');
      wrapper.className = 'table-scroll';
      wrapper.tabIndex = 0;
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', 'Trip details table; scroll horizontally to see all columns');
      const table = document.createElement('table');
      const header = table.createTHead().insertRow();
      for (const cell of cells(line)) {
        const th = document.createElement('th');
        th.scope = 'col';
        inlineText(th, cell); header.append(th);
      }
      const body = table.createTBody();
      index += 2;
      while (index < lines.length && lines[index].trim().includes('|')) {
        const row = body.insertRow();
        for (const cell of cells(lines[index])) inlineText(row.insertCell(), cell);
        index++;
      }
      index--;
      wrapper.append(table); container.append(wrapper);
      continue;
    }
    if (!line.trim()) { list = null; continue; }
    const heading = line.match(/^#{1,6}\s+(.+)$/);
    const item = line.match(/^\s*(?:[-*+] |\d+[.)] )(.+)$/);
    if (item) {
      const tag = /^\s*\d/.test(line) ? 'ol' : 'ul';
      if (!list || list.tagName.toLowerCase() !== tag) {
        list = document.createElement(tag);
        if (tag === 'ol') list.start = Number(line.trim().match(/^\d+/)[0]);
        container.append(list);
      }
      const li = document.createElement('li');
      inlineText(li, item[1]); list.append(li); continue;
    }
    list = null;
    if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) { container.append(document.createElement('hr')); continue; }
    const element = document.createElement(heading ? 'h3' : 'p');
    inlineText(element, heading ? heading[1] : line);
    container.append(element);
  }
}
function searchText(value) {
  return typeof value === 'string' ? value : value ? JSON.stringify(value, null, 2) : 'No results supplied.';
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  const query = input.value.trim();
  if (query.length < 3) {
    input.setCustomValidity('Please describe your trip in at least 3 characters.');
    input.reportValidity(); return;
  }
  busy = true;
  error.hidden = true;
  results.hidden = true;
  loading.hidden = false;
  form.setAttribute('aria-busy', 'true');
  submit.querySelector('span').textContent = 'Planning your trip';
  form.querySelectorAll('button, textarea').forEach(element => { element.disabled = true; });
  document.querySelector('#loading-text').textContent = 'Your trip is being planned. This may take a minute or two.';
  const started = Date.now();
  const timer = setInterval(() => {
    const seconds = Math.floor((Date.now() - started) / 1000);
    document.querySelector('#loading-text').textContent = `Still working on your trip · ${seconds}s elapsed. Keep this page open.`;
  }, 10000);
  try {
    const response = await fetch('/api/plan', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: query }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(typeof data?.detail === 'string' ? data.detail : 'We couldn’t process this trip. Please check your input and try again.');
    }
    if (typeof data?.answer !== 'string' || !data.answer.trim()) throw new Error('The agent returned an empty plan. Please try again.');
    currentAnswer = data.answer;
    renderAnswer(currentAnswer);
    document.querySelector('#result-query').textContent = query;
    document.querySelector('#flight-results').textContent = searchText(data.flight_results);
    document.querySelector('#hotel-results').textContent = searchText(data.hotel_results);
    results.hidden = false;
    document.querySelector('#results-title').focus({ preventScroll: true });
    results.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
    document.querySelector('#announcement').textContent = 'Your travel plan is ready.';
  } catch (failure) {
    error.textContent = failure instanceof TypeError ? 'Couldn’t reach the server. Check your connection and try again.' : failure.message;
    error.hidden = false;
  } finally {
    clearInterval(timer);
    loading.hidden = true;
    busy = false;
    form.setAttribute('aria-busy', 'false');
    form.querySelectorAll('button, textarea').forEach(element => { element.disabled = false; });
    submit.querySelector('span').textContent = 'Plan my trip';
  }
});

document.querySelector('#copy-button').addEventListener('click', async () => {
  const announcement = document.querySelector('#announcement');
  try {
    await navigator.clipboard.writeText(currentAnswer);
    document.querySelector('#copy-button').textContent = 'Copied ✓';
    announcement.textContent = 'Plan copied to clipboard.';
    setTimeout(() => { document.querySelector('#copy-button').textContent = 'Copy plan'; }, 2000);
  } catch {
    announcement.textContent = 'Clipboard access unavailable. Select the plan text to copy it.';
    document.querySelector('#copy-button').textContent = 'Select text to copy';
  }
});
