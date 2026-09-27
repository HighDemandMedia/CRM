<script>
  import { enhance } from '$app/forms';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import { untrack } from 'svelte';
  import {
    Bug,
    Lightbulb,
    MessageCircle,
    ArrowRight,
    CircleCheck,
    Mail,
    BookOpen
  } from '@lucide/svelte';
  import HelpHeader from '$lib/help/HelpHeader.svelte';
  import { articles } from '$lib/help/articles.js';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { requestTypes } from '$lib/help/request-types.js';
  let { data, form } = $props();
  let kind = $state(
    untrack(() =>
      requestTypes.some((t) => t.key === page.url.searchParams.get('type'))
        ? page.url.searchParams.get('type')
        : form?.values?.category || 'help'
    )
  );
  let current = $derived(requestTypes.find((type) => type.key === kind));
  let busy = $state(false);
  let requestId = $state(untrack(() => data.requestId));
  function chooseType(type) {
    if (form?.receipt) requestId = crypto.randomUUID();
    kind = type;
    form = null;
  }
  let drafts = $state(
    untrack(() =>
      Object.fromEntries(
        requestTypes.map((type) => [
          type.key,
          {
            area: 'General',
            subject: '',
            ...Object.fromEntries(type.fields.map((field) => [field.key, ''])),
            ...(form?.values?.category === type.key ? form.values : {})
          }
        ])
      )
    )
  );
  let draft = $derived(drafts[kind]);
  let suggestedGuides = $derived.by(() => {
    const words =
      `${draft.question || ''} ${draft.area === 'General' ? '' : draft.area}`
        .toLowerCase()
        .match(/[a-záéíóúñ]{4,}/g) || [];
    const ignored = new Set([
      'what',
      'with',
      'have',
      'does',
      'that',
      'this',
      'from',
      'your',
      'help',
      'need',
      'want'
    ]);
    const terms = [...new Set(words)].filter((word) => !ignored.has(word));
    if (!terms.length) return [];
    return articles
      .map((article) => {
        const heading = `${article.title} ${article.summary}`.toLowerCase();
        const content = JSON.stringify(article.sections).toLowerCase();
        return {
          article,
          score: terms.reduce(
            (score, term) => score + (heading.includes(term) ? 3 : content.includes(term) ? 1 : 0),
            0
          )
        };
      })
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map((item) => item.article);
  });
  let icons = { bug: Bug, feature: Lightbulb, help: MessageCircle };
  const submit = () => {
    busy = true;
    return async ({ update }) => {
      try {
        await update({ reset: false });
      } finally {
        busy = false;
      }
    };
  };
</script>

{#snippet areaField(label)}
  <label
    >{label}<select class="v2-input" name="area" bind:value={draft.area}>
      {#each data.support.areas as area}<option value={area}>{area}</option>{/each}
    </select></label
  >
{/snippet}

{#snippet subjectField()}
  <label
    >{current.subject}<input
      class="v2-input"
      name="subject"
      required
      maxlength="160"
      placeholder={current.subjectPlaceholder}
      bind:value={draft.subject}
    /></label
  >
{/snippet}

{#snippet field(key, rows = 3)}
  {@const spec = current.fields.find((item) => item.key === key)}
  <label
    ><span
      >{spec.label}{#if !spec.required}<small>Optional</small>{/if}</span
    >
    {#if spec.options}
      <select class="v2-input" name={key} required={spec.required} bind:value={draft[key]}>
        <option value="">Select…</option>
        {#each spec.options as option}<option value={option.value}>{option.label}</option>{/each}
      </select>
    {:else if spec.input === 'url'}
      <input
        class="v2-input"
        type="url"
        name={key}
        maxlength="2000"
        placeholder={spec.placeholder}
        bind:value={draft[key]}
      />
    {:else}
      <textarea
        class="v2-input"
        {rows}
        name={key}
        required={spec.required}
        maxlength="6000"
        placeholder={spec.placeholder}
        bind:value={draft[key]}></textarea>
    {/if}
  </label>
{/snippet}

<HelpHeader />
<div class="help-scroll">
  <div class="help-layout">
    <aside class="request-sidebar">
      <h2>How can we help?</h2>
      <div class="request-types" role="group" aria-label="Request type">
        {#each requestTypes as type}{@const Icon = icons[type.key]}<button
            type="button"
            class:active={kind === type.key}
            aria-pressed={kind === type.key}
            disabled={busy}
            onclick={() => chooseType(type.key)}
            ><Icon size={19} /><span
              ><strong>{type.title}</strong><small>{type.description}</small></span
            ><ArrowRight size={15} /></button
          >{/each}
      </div>
      <a class="guide-link" href={resolve('/help/knowledge')}
        ><BookOpen size={18} /><span
          ><strong>Explore the knowledge base</strong><small
            >Step-by-step guides for your CRM.</small
          ></span
        ></a
      >
      <div class="support-address">
        <Mail size={15} /><span
          >High Demand Media<br /><a href={`mailto:${data.support.recipient}`}
            >{data.support.recipient}</a
          ></span
        >
      </div>
    </aside>
    <section class="request-panel">
      {#if form?.receipt}
        <div class="success" role="status">
          <CircleCheck size={30} />
          <h2>
            {form.receipt.delivery_mode === 'local_test'
              ? 'Captured in the local test inbox'
              : 'Request sent'}
          </h2>
          <p>
            {form.receipt.delivery_mode === 'local_test'
              ? `This local environment captured the message addressed to ${form.receipt.recipient}. It has not been delivered to the external mailbox.`
              : `Your request was accepted by the email service for ${form.receipt.recipient}. Replies will go to ${data.support.reply_to}.`}
          </p>
          <span class="reference">Reference: {form.receipt.reference}</span><a
            class="v2-btn"
            href={resolve('/help')}
            data-sveltekit-reload>New request</a
          >
        </div>
      {:else}
        <div class="form-heading">
          <h2>{current.title}</h2>
          <p>{current.introduction}</p>
        </div>
        {#if data.support.delivery_mode === 'local_test'}<p class="delivery-note">
            Local test mode · Requests are captured in the test inbox. External email delivery is
            not active.
          </p>{:else if data.support.delivery_mode === 'unavailable'}<p
            class="delivery-note"
            role="status"
          >
            Email delivery is not configured. Contact <a href={`mailto:${data.support.recipient}`}
              >{data.support.recipient}</a
            > directly.
          </p>{/if}
        <form method="POST" use:enhance={submit}>
          <input
            type="hidden"
            name="request_id"
            value={form?.values?.request_id || requestId}
          /><input type="hidden" name="category" value={kind} />
          <fieldset disabled={busy || data.support.delivery_mode === 'unavailable'}>
            {#key kind}
              {#if kind === 'bug'}
                <div class="form-section">
                  <h3><span class="step">1</span> Locate the problem</h3>
                  {@render areaField('Where did it happen?')}
                  {@render subjectField()}
                </div>
                <div class="form-section">
                  <h3><span class="step">2</span> Describe the difference</h3>
                  <div class="field-pair">{@render field('actual')}{@render field('expected')}</div>
                </div>
                <div class="form-section">
                  <h3><span class="step">3</span> Help us investigate</h3>
                  <div class="field-pair">
                    {@render field('impact')}{@render field('frequency')}
                  </div>
                  <details open={Boolean(draft.steps || draft.record_link)}>
                    <summary>Add steps or a page link <span>Optional</span></summary>
                    <div class="optional-fields">
                      {@render field('steps')}{@render field('record_link')}
                    </div>
                  </details>
                </div>
              {:else if kind === 'feature'}
                {@render subjectField()}
                {@render areaField('Which part of the CRM would improve?')}
                <div class="idea-story">
                  <div><span class="story-label">Today</span>{@render field('problem')}</div>
                  <div>
                    <span class="story-label">Better outcome</span>{@render field('benefit')}
                  </div>
                </div>
                {@render field('audience')}
                <details open={Boolean(draft.suggestion)}>
                  <summary>Have a solution in mind? <span>Optional</span></summary>
                  <div class="optional-fields">{@render field('suggestion', 4)}</div>
                </details>
              {:else}
                {@render areaField('What is your question about?')}
                {@render field('question', 5)}
                {#if suggestedGuides.length}
                  <div class="suggested-guides">
                    <h3><BookOpen size={16} /> These guides may help</h3>
                    {#each suggestedGuides as article}
                      <a
                        href={resolve(asInternalPath(`/help/knowledge/${article.slug}`))}
                        target="_blank"
                        rel="noopener"
                        aria-label={`${article.title} (opens in a new tab)`}
                        >{article.title}<ArrowRight size={14} /></a
                      >
                    {/each}
                  </div>
                {/if}
                <details open={Boolean(draft.tried)}>
                  <summary>Add more context <span>Optional</span></summary>
                  <div class="optional-fields">{@render field('tried')}</div>
                </details>
              {/if}
            {/key}
          </fieldset>
          <div class="sender">
            <span
              >Sending as <strong>{data.support.name}</strong> · {data.support.organization}</span
            ><span>Reply email: {data.support.reply_to}</span>
          </div>
          {#if form?.error}<div class="form-error" role="alert">{form.error}</div>{/if}
          <div class="form-footer">
            <span>To {data.support.recipient}</span><button
              class="v2-btn v2-btn-primary"
              type="submit"
              disabled={busy || data.support.delivery_mode === 'unavailable'}
              >{busy ? 'Sending…' : current.action}</button
            >
          </div>
        </form>
      {/if}
    </section>
  </div>
</div>

<style>
  .help-scroll {
    overflow: auto;
    min-height: 0;
    flex: 1;
  }
  .help-layout {
    max-width: 1160px;
    margin: 0 auto;
    padding: 26px 28px 40px;
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 30px;
    align-items: start;
  }
  h2 {
    font-size: 18px;
    font-weight: 650;
    margin: 0;
  }
  .request-sidebar h2 {
    font-size: 15px;
    margin-bottom: 16px;
  }
  .request-types {
    display: grid;
    gap: 10px;
  }
  .request-types button {
    display: flex;
    align-items: center;
    gap: 12px;
    text-align: left;
    background: var(--v2-surface, #fff);
    border: 1px solid var(--v2-line);
    border-radius: 10px;
    padding: 16px 13px;
    color: var(--v2-slate);
  }
  .request-types button.active {
    border-color: #81778c;
    background: #eeebf1;
    color: #343137;
  }
  .request-types button > span {
    flex: 1;
    min-width: 0;
  }
  .request-types strong,
  .guide-link strong {
    display: block;
    font-size: 13px;
    font-weight: 600;
  }
  .request-types small,
  .guide-link small {
    display: block;
    font-size: 12px;
    line-height: 1.5;
    margin-top: 5px;
    color: var(--v2-slate);
  }
  .request-types :global(svg),
  .guide-link :global(svg) {
    flex-shrink: 0;
  }
  .guide-link {
    display: flex;
    gap: 12px;
    margin-top: 25px;
    padding: 15px 0;
    border-top: 1px solid var(--v2-line);
    color: inherit;
    text-decoration: none;
  }
  .support-address {
    display: flex;
    gap: 10px;
    color: var(--v2-slate);
    font-size: 12px;
    line-height: 1.7;
    margin-top: 12px;
  }
  .support-address a {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .request-panel {
    border: 1px solid var(--v2-line);
    border-radius: 13px;
    background: var(--v2-surface, #fff);
    padding: 26px;
    min-width: 0;
  }
  .form-heading p {
    font-size: 13px;
    color: var(--v2-slate);
    margin: 7px 0 24px;
  }
  .delivery-note {
    font-size: 12px;
    line-height: 1.6;
    background: #f5f2e9;
    border-radius: 8px;
    padding: 10px 13px;
    margin: 0 0 20px;
    color: #716143;
  }
  .delivery-note a {
    text-decoration: underline;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 19px;
  }
  label {
    display: grid;
    gap: 8px;
    font-size: 13px;
    font-weight: 500;
  }
  label > span {
    display: flex;
    justify-content: space-between;
    gap: 10px;
  }
  label small {
    color: var(--v2-slate);
    font-size: 11px;
    font-weight: 400;
  }
  .v2-input {
    width: 100%;
    font-size: 13px;
    min-height: 40px;
  }
  textarea {
    resize: vertical;
    min-height: 90px;
    line-height: 1.6;
  }
  .sender {
    display: grid;
    gap: 5px;
    color: var(--v2-slate);
    font-size: 11px;
    margin-top: 24px;
  }
  .sender strong {
    font-weight: 500;
  }
  .form-footer {
    display: flex;
    gap: 15px;
    justify-content: space-between;
    align-items: center;
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--v2-line);
  }
  .form-footer > span {
    font-size: 11px;
    color: var(--v2-slate);
  }
  .form-error {
    padding: 12px;
    background: #fff2ef;
    color: #973d32;
    font-size: 13px;
    border-radius: 8px;
    margin-top: 18px;
  }
  .success {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 20px 0;
  }
  .success :global(svg) {
    color: #55705e;
  }
  .success p {
    font-size: 14px;
    color: var(--v2-slate);
    line-height: 1.7;
    margin: 0;
  }
  .reference {
    font-size: 12px;
    color: var(--v2-slate);
  }
  button:disabled {
    opacity: 0.6;
  }
  button:focus-visible,
  a:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 3px;
  }
  .form-section {
    display: grid;
    gap: 16px;
  }
  .form-section + .form-section {
    border-top: 1px solid var(--v2-line);
    padding-top: 20px;
  }
  h3 {
    font-size: 13px;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 9px;
  }
  .step {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #eeebf1;
    color: #655c70;
    font-size: 11px;
  }
  .field-pair {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  .idea-story {
    border-left: 2px solid #b1a7bc;
    padding-left: 18px;
    display: grid;
    gap: 24px;
  }
  .story-label {
    display: block;
    font-size: 11px;
    color: #71657e;
    margin-bottom: 7px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  details {
    border-top: 1px solid var(--v2-line);
    padding-top: 15px;
  }
  summary {
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
  }
  summary span {
    color: var(--v2-slate);
    font-size: 11px;
    font-weight: 400;
    margin-left: 8px;
  }
  summary:focus-visible {
    outline: 2px solid #81778c;
    outline-offset: 4px;
  }
  .optional-fields {
    display: grid;
    gap: 16px;
    padding-top: 16px;
  }
  .suggested-guides {
    border-radius: 8px;
    padding: 16px;
    background: #f6f4f8;
  }
  .suggested-guides h3 {
    margin-bottom: 9px;
    color: #655c70;
  }
  .suggested-guides a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    font-size: 12px;
    padding: 9px 0;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .suggested-guides :global(svg) {
    flex-shrink: 0;
  }
  @media (max-width: 1000px) {
    .help-layout {
      grid-template-columns: 1fr;
    }
    .request-types {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .request-types button {
      align-items: flex-start;
    }
    .request-types button > :global(svg:last-child) {
      display: none;
    }
    .guide-link {
      margin-top: 12px;
    }
    .support-address {
      display: none;
    }
  }
  @media (max-width: 640px) {
    .help-layout {
      padding: 20px 16px;
    }
    .request-types {
      grid-template-columns: 1fr;
    }
    .field-pair {
      grid-template-columns: 1fr;
    }
    .request-panel {
      padding: 18px;
    }
    .form-footer {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
