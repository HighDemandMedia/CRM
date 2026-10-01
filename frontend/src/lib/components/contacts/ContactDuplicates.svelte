<script>
  import { resolve } from '$app/paths';
  /** @type {{name?:string, email?:string, phone?:string, exclude?:string}} */
  let { name = '', email = '', phone = '', exclude = '' } = $props();
  let matches = $state([]),
    checking = $state(false),
    error = $state('');
  $effect(() => {
    const query = new URLSearchParams({
      name: name.trim(),
      email: email.trim(),
      phone: phone.trim()
    });
    if (exclude) query.set('exclude', exclude);
    matches = [];
    error = '';
    if (name.trim().length < 3 && !email.includes('@') && phone.replace(/\D/g, '').length < 7) {
      checking = false;
      return;
    }
    const controller = new AbortController();
    checking = true;
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/contacts/duplicates?${query}`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error('Could not check existing contacts.');
        const data = await response.json();
        if (!controller.signal.aborted) matches = data.results || [];
      } catch (err) {
        if (!controller.signal.aborted) error = 'Could not check existing contacts.';
      } finally {
        if (!controller.signal.aborted) checking = false;
      }
    }, 450);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });
</script>

{#if matches.length}
  <aside class="matches" aria-label="Possible existing contacts">
    <strong>This contact may already exist</strong>
    {#each matches as contact (contact.id)}
      <a data-open-record href={resolve(`/contacts/${contact.id}`)}>
        <span class="match-name"
          >{contact.name || 'Contact'}<span class="open">Open contact →</span></span
        >
        <span class="details">{[contact.email, contact.phone].filter(Boolean).join(' · ')}</span>
        <span class="reasons">{contact.reasons.join(' · ')}</span>
      </a>
    {/each}
  </aside>
{:else if checking}<p class="lookup-status" role="status">Checking existing contacts…</p>
{:else if error}<p class="lookup-status" role="status">{error}</p>{/if}

<style>
  .matches {
    grid-column: 1/-1;
    border: 1px solid #e3c994;
    background: #fffaf0;
    border-radius: 10px;
    padding: 12px 14px;
  }
  .matches > strong {
    display: block;
    font-size: 13px;
    color: #694b20;
    margin-bottom: 4px;
  }
  a {
    display: block;
    color: var(--v2-ink);
    text-decoration: none;
    padding: 9px 0;
  }
  a + a {
    border-top: 1px solid #eee0c5;
  }
  a:hover .match-name {
    text-decoration: underline;
  }
  .match-name {
    display: flex;
    align-items: baseline;
    gap: 10px;
    justify-content: space-between;
    font-weight: 600;
    font-size: 13px;
  }
  .open {
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
  }
  .details,
  .reasons {
    display: block;
    font-size: 12px;
    overflow-wrap: anywhere;
    margin-top: 3px;
  }
  .details {
    color: var(--v2-slate);
  }
  .reasons {
    color: #775720;
  }
  .lookup-status {
    grid-column: 1/-1;
    font-size: 12px;
    color: var(--v2-slate);
    margin: 0;
  }
</style>
