<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

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
      >{spec.label}{#if !spec.required}<small>{ui('Optional')}</small>{/if}</span
    >
    {#if spec.options}
      <select class="v2-input" name={key} required={spec.required} bind:value={draft[key]}>
        <option value="">{ui('Select…')}</option>
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
      <h2>{ui('How can we help?')}</h2>
      <div class="request-types" role="group" aria-label={ui('Request type')}>
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
          ><strong>{ui('Explore the knowledge base')}</strong><small
            >{ui('Step-by-step guides for your CRM.')}</small
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
              ? ui('Captured in the local test inbox')
              : ui('Request sent')}
          </h2>
          <p>
            {form.receipt.delivery_mode === 'local_test'
              ? `This local environment captured the message addressed to ${form.receipt.recipient}. It has not been delivered to the external mailbox.`
              : `Your request was accepted by the email service for ${form.receipt.recipient}. Replies will go to ${data.support.reply_to}.`}
          </p>
          <span class="reference">{ui('Reference:')} {form.receipt.reference}</span><a
            class="v2-btn"
            href={resolve('/help')}
            data-sveltekit-reload>{ui('New request')}</a
          >
        </div>
      {:else}
        <div class="form-heading">
          <h2>{current.title}</h2>
          <p>{current.introduction}</p>
        </div>
        {#if data.support.delivery_mode === 'local_test'}<p class="delivery-note">
            {ui(
              'Local test mode · Requests are captured in the test inbox. External email delivery is not active.'
            )}
          </p>{:else if data.support.delivery_mode === 'unavailable'}<p
            class="delivery-note"
            role="status"
          >
            {ui('Email delivery is not configured. Contact')}
            <a href={`mailto:${data.support.recipient}`}>{data.support.recipient}</a>
            {ui('directly.')}
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
                  <h3><span class="step">1</span> {ui('Locate the problem')}</h3>
                  {@render areaField('Where did it happen?')}
                  {@render subjectField()}
                </div>
                <div class="form-section">
                  <h3><span class="step">2</span> {ui('Describe the difference')}</h3>
                  <div class="field-pair">{@render field('actual')}{@render field('expected')}</div>
                </div>
                <div class="form-section">
                  <h3><span class="step">3</span> {ui('Help us investigate')}</h3>
                  <div class="field-pair">
                    {@render field('impact')}{@render field('frequency')}
                  </div>
                  <details open={Boolean(draft.steps || draft.record_link)}>
                    <summary>{ui('Add steps or a page link')} <span>{ui('Optional')}</span></summary
                    >
                    <div class="optional-fields">
                      {@render field('steps')}{@render field('record_link')}
                    </div>
                  </details>
                </div>
              {:else if kind === 'feature'}
                {@render subjectField()}
                {@render areaField('Which part of the CRM would improve?')}
                <div class="idea-story">
                  <div>
                    <span class="story-label">{ui('Today')}</span>{@render field('problem')}
                  </div>
                  <div>
                    <span class="story-label">{ui('Better outcome')}</span>{@render field(
                      'benefit'
                    )}
                  </div>
                </div>
                {@render field('audience')}
                <details open={Boolean(draft.suggestion)}>
                  <summary>{ui('Have a solution in mind?')} <span>{ui('Optional')}</span></summary>
                  <div class="optional-fields">{@render field('suggestion', 4)}</div>
                </details>
              {:else}
                {@render areaField('What is your question about?')}
                {@render field('question', 5)}
                {#if suggestedGuides.length}
                  <div class="suggested-guides">
                    <h3><BookOpen size={16} /> {ui('These guides may help')}</h3>
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
                  <summary>{ui('Add more context')} <span>{ui('Optional')}</span></summary>
                  <div class="optional-fields">{@render field('tried')}</div>
                </details>
              {/if}
            {/key}
          </fieldset>
          <div class="sender">
            <span
              >{ui('Sending as')} <strong>{data.support.name}</strong> · {data.support
                .organization}</span
            ><span>{ui('Reply email:')} {data.support.reply_to}</span>
          </div>
          {#if form?.error}<div class="form-error" role="alert">{ui(form.error)}</div>{/if}
          <div class="form-footer">
            <span>{ui('To')} {data.support.recipient}</span><button
              class="v2-btn v2-btn-primary"
              type="submit"
              disabled={busy || data.support.delivery_mode === 'unavailable'}
              >{busy ? ui('Sending…') : current.action}</button
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
    padding: 26px 28px var(--crm-space-10);
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 30px;
    align-items: start;
  }
  h2 {
    font-size: var(--crm-text-lg);
    font-weight: 650;
    margin: 0;
  }
  .request-sidebar h2 {
    font-size: var(--crm-text-sm);
    margin-bottom: var(--crm-space-4);
  }
  .request-types {
    display: grid;
    gap: 10px;
  }
  .request-types button {
    display: flex;
    align-items: center;
    gap: var(--crm-space-3);
    text-align: left;
    background: var(--v2-surface, var(--crm-surface));
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    padding: var(--crm-space-4) 13px;
    color: var(--v2-slate);
  }
  .request-types button.active {
    border-color: var(--crm-focus);
    background: var(--crm-surface-selected);
    color: var(--crm-text);
  }
  .request-types button > span {
    flex: 1;
    min-width: 0;
  }
  .request-types strong,
  .guide-link strong {
    display: block;
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  .request-types small,
  .guide-link small {
    display: block;
    font-size: var(--crm-text-xs);
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
    gap: var(--crm-space-3);
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
    font-size: var(--crm-text-xs);
    line-height: 1.7;
    margin-top: var(--crm-space-3);
  }
  .support-address a {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .request-panel {
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-lg);
    background: var(--v2-surface, var(--crm-surface));
    padding: 26px;
    min-width: 0;
  }
  .form-heading p {
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
    margin: 7px 0 var(--crm-space-6);
  }
  .delivery-note {
    font-size: var(--crm-text-xs);
    line-height: 1.6;
    background: var(--crm-warning-bg);
    border-radius: var(--crm-radius-md);
    padding: 10px 13px;
    margin: 0 0 var(--crm-space-5);
    color: var(--crm-warning);
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
    gap: var(--crm-space-2);
    font-size: var(--crm-text-sm);
    font-weight: 500;
  }
  label > span {
    display: flex;
    justify-content: space-between;
    gap: 10px;
  }
  label small {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    font-weight: 400;
  }
  .v2-input {
    width: 100%;
    font-size: var(--crm-text-sm);
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
    font-size: var(--crm-text-xs);
    margin-top: var(--crm-space-6);
  }
  .sender strong {
    font-weight: 500;
  }
  .form-footer {
    display: flex;
    gap: 15px;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--crm-space-5);
    padding-top: var(--crm-space-5);
    border-top: 1px solid var(--v2-line);
  }
  .form-footer > span {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  .form-error {
    padding: var(--crm-space-3);
    background: var(--crm-danger-bg);
    color: var(--crm-danger);
    font-size: var(--crm-text-sm);
    border-radius: var(--crm-radius-md);
    margin-top: 18px;
  }
  .success {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--crm-space-4);
    padding: var(--crm-space-5) 0;
  }
  .success :global(svg) {
    color: var(--crm-success);
  }
  .success p {
    font-size: var(--crm-text-sm);
    color: var(--v2-slate);
    line-height: 1.7;
    margin: 0;
  }
  .reference {
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
  }
  button:disabled {
    opacity: 0.6;
  }
  button:focus-visible,
  a:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 3px;
  }
  .form-section {
    display: grid;
    gap: var(--crm-space-4);
  }
  .form-section + .form-section {
    border-top: 1px solid var(--v2-line);
    padding-top: var(--crm-space-5);
  }
  h3 {
    font-size: var(--crm-text-sm);
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
    background: var(--crm-surface-selected);
    color: var(--crm-text-muted);
    font-size: var(--crm-text-xs);
  }
  .field-pair {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--crm-space-4);
  }
  .idea-story {
    border-left: 2px solid var(--crm-text-muted);
    padding-left: 18px;
    display: grid;
    gap: var(--crm-space-6);
  }
  .story-label {
    display: block;
    font-size: var(--crm-text-xs);
    color: var(--crm-text-muted);
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
    font-size: var(--crm-text-sm);
    font-weight: 500;
  }
  summary span {
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    font-weight: 400;
    margin-left: var(--crm-space-2);
  }
  summary:focus-visible {
    outline: 2px solid var(--crm-focus);
    outline-offset: 4px;
  }
  .optional-fields {
    display: grid;
    gap: var(--crm-space-4);
    padding-top: var(--crm-space-4);
  }
  .suggested-guides {
    border-radius: var(--crm-radius-md);
    padding: var(--crm-space-4);
    background: var(--crm-canvas);
  }
  .suggested-guides h3 {
    margin-bottom: 9px;
    color: var(--crm-text-muted);
  }
  .suggested-guides a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--crm-space-3);
    font-size: var(--crm-text-xs);
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
      margin-top: var(--crm-space-3);
    }
    .support-address {
      display: none;
    }
  }
  @media (max-width: 640px) {
    .help-layout {
      padding: var(--crm-space-5) var(--crm-space-4);
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
