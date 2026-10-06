<script>
  import { attachmentError } from '$lib/v2/attachment-policy.js';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui, longDate, relativeTime } = useI18n();

  import Attachments from '$lib/v2/components/Attachments.svelte';
  import StageRuleNotice from '$lib/components/pipelines/StageRuleNotice.svelte';
  import TicketProfile from '$lib/components/tickets/TicketProfile.svelte';
  let advanced = $state(false);
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import { shortAge } from '$lib/v2/format.js';
  import { PRIORITY_TONE, CASE_STATUS_TONE } from '$lib/v2/enums.js';
  import { cascadeSummary } from './close.js';
  import { ChevronRight, Lock, Paperclip, Pencil, Ticket, X } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let { ticket, conversation, alsoOpen, contacts, attachments, activity, canReply } =
    $derived(data);

  /*
   * Closing a parent takes a confirm step, because it can close other people's
   * tickets. `data.close` is present only when the ticket has children, so an
   * ordinary ticket keeps the one-click Close it always had.
   *
   * The checkbox starts where the org set it
   * (`auto_close_children_on_parent_close`), which is the only place that
   * setting reaches a web user, and the person closing can always move it. It
   * is disabled when nothing linked is open, since there is nothing for a
   * cascade to do.
   */
  let closePanel = $state(false);
  let cascade = $state(false);
  let hasOpenChildren = $derived((data.close?.descendants ?? []).length > 0);

  function openClosePanel() {
    cascade = hasOpenChildren && data.close?.cascade_default === true;
    closePanel = true;
  }

  /*
   * The composer owns its own text rather than reading it back from `data`, so
   * a revalidation cannot wipe a half-written reply. It is cleared only on a
   * send that actually succeeded; `update({ reset: false })` below leaves it
   * alone otherwise, which is what makes a rejected send recoverable.
   */
  let body = $state('');
  let internal = $state(false);
  let sending = $state(false);

  // The picked file's name, mirrored out of the input so the composer can show
  // and clear it. `fileInput` is the element itself. A file input's value can
  // only be cleared through the DOM, not by rebinding.
  let fileName = $state('');
  /** @type {HTMLInputElement | undefined} */
  let fileInput = $state();

  /** @param {Event} e */
  let fileError = $state('');
  function pickFile(e) {
    const input = /** @type {HTMLInputElement} */ (e.currentTarget);
    fileError = attachmentError(input.files?.[0]);
    if (fileError) {
      clearFile();
      return;
    }
    fileName = /** @type {HTMLInputElement} */ (e.currentTarget).files?.[0]?.name ?? '';
  }
  function clearFile() {
    if (fileInput) fileInput.value = '';
    fileName = '';
  }

  // A ticket accepts a file on its own, the API saves the attachment in a block
  // separate from the comment, so the composer sends when there is either text
  // or a file.
  let canSend = $derived(Boolean(body.trim() || fileName));

  /** @type {import('@sveltejs/kit').SubmitFunction} */
  const send = ({ cancel }) => {
    fileError = attachmentError(fileInput?.files?.[0]);
    if (fileError) {
      cancel();
      return;
    }
    sending = true;
    return async ({ result, update }) => {
      sending = false;
      if (result.type === 'success') {
        body = '';
        clearFile();
      }
      await update({ reset: false });
    };
  };

  /**
   * The one thing that needs a person right now, said as the state it is.
   * Ember when the ball is in our court, rust when a target has already been
   * missed. Only "needs you" states earn a banner: a ticket waiting on the
   * customer is not blocked on us, so it stays a quiet line below, and a healthy
   * open ticket gets nothing at all.
   *
   * The mock had a `next_action` sentence telling the agent what to do; nothing
   * on `Case` supports inventing that, so this states the situation and stops.
   *
   * @type {{ tone: 'ember'|'rust', label: string, text: string } | null}
   */
  let alert = $derived.by(() => {
    if (!ticket.is_open) return null;
    if (!ticket.first_response_at) {
      return ticket.first_response_breached
        ? {
            tone: 'rust',
            label: 'First reply overdue',
            text: 'Past its first-reply target and still unanswered. A reply below is the first response. It stops the clock.'
          }
        : {
            tone: 'ember',
            label: 'Needs a first reply',
            text: 'Nobody has replied yet. A reply below is the first response. It is what stops the first-reply clock.'
          };
    }
    // Waiting on the customer is not something we can act on, so it is not a
    // banner. It falls through to the quiet line below.
    if (ticket.status === 'Pending') return null;
    if (!ticket.assignee) {
      return {
        tone: 'ember',
        label: 'No owner',
        text: 'Answered, but nobody owns it. Assign someone so it does not stall between people.'
      };
    }
    return null;
  });

  let waiting = $derived(
    ticket.is_open && ticket.status === 'Pending' && Boolean(ticket.first_response_at)
  );

  /**
   * The three SLA states, in the palette's own terms: rust for missed, clay
   * for the warning band ("aging_status yellow" is exactly what clay is for),
   * and ordinary text for on track. Breached wins, because the two are
   * exclusive server-side and a tie would mean a bug worth seeing as red.
   */
  function slaColor(breached, atRisk) {
    if (breached) return 'color:var(--v2-rust)';
    if (atRisk) return 'color:var(--v2-clay)';
    return '';
  }
</script>

{#if advanced}
  <button class="v2-btn" onclick={() => (advanced = false)}>{ui('Back to ticket')}</button>
  <PageHeader title={ticket.name} record>
    {#snippet leading()}
      <!-- Whose ticket this is, at a glance. The account's mark where there is
         one; a ticket glyph where nobody is attached. -->
      {#if ticket.account}
        <Avatar name={ticket.account.name} size={42} />
      {:else}
        <span class="ticket-glyph" aria-hidden="true"><Ticket size={20} /></span>
      {/if}
    {/snippet}
    {#snippet crumb()}
      <a href={resolve('/tickets')}>{ui('Tickets')}</a>
      {#if ticket.account}
        <ChevronRight size={12} />
        <a href={resolve(`/accounts/${ticket.account.id}`)}>{ticket.account.name}</a>
      {/if}
    {/snippet}
    {#snippet actions()}
      <a class="v2-btn" href={resolve(`/tickets/${ticket.id}/edit`)}
        ><Pencil size={12} />{ui('Edit')}</a
      >
      {#if ticket.is_open}
        <form method="POST" action="?/setStatus" use:enhance style="display:contents">
          {#if ticket.status !== 'Pending'}
            <button class="v2-btn" name="status" value="Pending">{ui('Set to pending')}</button>
          {/if}
          {#if !data.close}
            <button class="v2-btn v2-btn-primary" name="status" value="Closed">{ui('Close')}</button
            >
          {/if}
        </form>
        <!-- A parent ticket closes through a confirm step, since the same click
           can close tickets belonging to other people. Outside the form above
           so this button never submits it. -->
        {#if data.close && !closePanel}
          <button class="v2-btn v2-btn-primary" type="button" onclick={openClosePanel}
            >{ui('Close')}</button
          >
        {/if}
      {:else}
        <form method="POST" action="?/setStatus" use:enhance style="display:contents">
          <button class="v2-btn" name="status" value="New">{ui('Reopen')}</button>
        </form>
      {/if}
    {/snippet}
  </PageHeader>

  <div style="display:flex;flex:1;min-height:0;overflow:hidden">
    <div class="v2-main">
      <div
        class="v2-pad"
        style="padding-top:12px;display:flex;gap:7px;align-items:center;flex-wrap:wrap;flex:none"
      >
        <Pill tone={PRIORITY_TONE[ticket.priority]}>{ticket.priority}</Pill>
        <Pill tone={CASE_STATUS_TONE[ticket.status]}>{ticket.status}</Pill>
        {#if ticket.case_type}<Pill tone="slate">{ticket.case_type}</Pill>{/if}
        <span class="v2-sub">
          <!-- There is no ticket number. `Case` has a UUID and a subject, so the
             subject is the identifier and the age is the useful fact. -->
          {ui('Opened')}
          {shortAge(ticket.opened_at)}
          {ui('ago')}
          {#if ticket.first_response_at}
            {ui('· first reply')} {relativeTime(ticket.first_response_at)}
          {/if}
          {#if ticket.escalation_count > 0}
            · <span style="color:var(--v2-rust)">{ui('escalated')} {ticket.escalation_count}×</span>
          {/if}
        </span>
      </div>

      <div class="v2-scroll">
        <div class="v2-pad" style="padding-top:14px;padding-bottom:24px">
          <StageRuleNotice issue={form?.stageRequirements} />
          {#if form?.error && !form?.stageRequirements}
            <p
              class="v2-card"
              style="padding:10px 13px;margin-bottom:16px;color:var(--v2-rust);font-size:var(--crm-text-sm)"
            >
              {ui(form.error)}
            </p>
          {/if}

          {#if form?.closed}
            <p
              class="v2-card"
              style="padding:10px 13px;margin-bottom:16px;font-size:var(--crm-text-sm)"
            >
              {form.closed}
            </p>
          {/if}

          <!--
          The confirm step for closing a parent. It names the tickets that go
          with it before anything happens, because they may belong to someone
          else and nobody is asked twice.

          The list is the subtree the API would actually close: open, active
          descendants of THIS ticket. Not the whole tree it sits in, which is
          what `/tree/` returns and what the earlier unwired version of this
          feature showed.
        -->
          {#if closePanel && data.close}
            <div class="v2-card v2-close-panel">
              <form
                method="POST"
                action="?/closeWithChildren"
                use:enhance={() =>
                  async ({ update }) => {
                    await update();
                    closePanel = false;
                  }}
              >
                <div style="font-weight:600;font-size:var(--crm-text-sm)">
                  {ui('Close')}
                  {ticket.name}
                </div>
                <p
                  class="v2-sub"
                  style="font-size:var(--crm-text-sm);margin:6px 0 0;line-height:1.5"
                >
                  {cascadeSummary({
                    count: data.close.descendants.length,
                    truncated: data.close.truncated
                  })}
                </p>

                {#if hasOpenChildren}
                  <ul class="v2-close-list">
                    {#each data.close.descendants as child (child.id)}
                      <li>
                        <span class="v2-close-name">{child.name}</span>
                        <Pill tone={CASE_STATUS_TONE[child.status]}>{child.status}</Pill>
                      </li>
                    {/each}
                  </ul>

                  <label class="v2-close-check">
                    <input type="checkbox" name="cascade" bind:checked={cascade} />
                    <span>
                      <span style="font-weight:600">{ui('Close these as well')}</span>
                      <span
                        class="v2-sub"
                        style="display:block;font-size:var(--crm-text-xs);margin-top:2px"
                      >
                        {ui(
                          'Each one gets a note saying it was closed with this ticket. Leave it unticked to close only this one.'
                        )}
                      </span>
                    </span>
                  </label>

                  <div class="v2-field" style="margin-top:12px">
                    <label for="close-comment">{ui('Why (optional)')}</label>
                    <textarea
                      id="close-comment"
                      class="v2-input"
                      name="resolution_comment"
                      rows="2"
                      maxlength="1000"
                      placeholder={ui('Recorded against every ticket closed with this one')}
                    ></textarea>
                  </div>
                {/if}

                <div style="display:flex;gap:8px;margin-top:14px">
                  <button class="v2-btn v2-btn-primary" type="submit">
                    {cascade ? ui('Close all of them') : ui('Close this ticket')}
                  </button>
                  <button class="v2-btn" type="button" onclick={() => (closePanel = false)}>
                    {ui('Cancel')}
                  </button>
                </div>
              </form>
            </div>
          {/if}

          {#if alert}
            <div style="margin-bottom:18px">
              <NextAction label={alert.label} text={alert.text} tone={alert.tone} />
            </div>
          {:else if waiting}
            <p class="v2-sub" style="margin:0 0 18px;font-size:var(--crm-text-sm)">
              {ui(
                'Waiting on the customer: the first-reply clock is paused while it sits in Pending.'
              )}
            </p>
          {/if}

          {#if ticket.description}
            <div class="v2-card" style="padding:13px 15px;margin-bottom:18px">
              <div class="v2-label" style="margin-bottom:7px">{ui('What was reported')}</div>
              <div style="font-size:var(--crm-text-sm);line-height:1.55;white-space:pre-wrap">
                {ticket.description}
              </div>
            </div>
          {/if}

          {#if conversation.length === 0}
            <p class="v2-sub" style="margin:0 0 18px;font-size:var(--crm-text-sm)">
              {ui(
                'Nothing has been said on this ticket yet. A reply below is the first response. It is what stops the first-reply clock.'
              )}
            </p>
          {/if}

          {#each conversation as m (m.id)}
            {#if m.direction === 'note'}
              <!-- An internal note is not part of the conversation with the
                 customer, so it does not sit on either side of it. -->
              <div
                class="v2-card"
                style="padding:11px 13px;margin-bottom:14px;border-style:dashed;background:transparent"
              >
                <div
                  class="v2-sub"
                  style="font-size:var(--crm-text-xs);margin-bottom:5px;display:flex;align-items:center;gap:5px"
                >
                  <Lock size={11} />
                  <b style="color:var(--v2-ink);font-weight:600">{m.author}</b>
                  {ui('· internal note ·')}
                  {shortAge(m.at)}
                  {ui('ago')}
                </div>
                <div style="font-size:var(--crm-text-sm);line-height:1.55;white-space:pre-wrap">
                  {m.body}
                </div>
              </div>
            {:else}
              <div
                style="display:flex;gap:12px;margin-bottom:14px;{m.direction === 'out'
                  ? 'flex-direction:row-reverse'
                  : ''}"
              >
                <Avatar name={m.author} size={30} />
                <div
                  class="v2-card"
                  style="padding:12px 14px;max-width:72%;{m.direction === 'out'
                    ? 'background:var(--v2-line-soft)'
                    : ''}"
                >
                  <div class="v2-sub" style="font-size:var(--crm-text-xs);margin-bottom:5px">
                    <b style="color:var(--v2-ink);font-weight:600">{m.author}</b>
                    {#if m.kind === 'email'}{ui('· email')}{/if}
                    · {shortAge(m.at)}
                    {ui('ago')}
                  </div>
                  {#if m.subject}
                    <div style="font-size:var(--crm-text-sm);font-weight:600;margin-bottom:4px">
                      {m.subject}
                    </div>
                  {/if}
                  <div style="font-size:var(--crm-text-sm);line-height:1.55;white-space:pre-wrap">
                    {m.body}
                  </div>
                </div>
              </div>
            {/if}
          {/each}

          {#if canReply}
            <form method="POST" action="?/reply" enctype="multipart/form-data" use:enhance={send}>
              <div class="v2-card" style="padding:13px 14px;margin-top:18px">
                <textarea
                  name="body"
                  bind:value={body}
                  rows="3"
                  placeholder={internal ? ui('Note for the team…') : ui('Write a reply…')}
                  style="width:100%;border:none;background:transparent;resize:vertical;font:inherit;font-size:var(--crm-text-sm);line-height:1.55;color:var(--v2-ink);outline:none"
                ></textarea>
                <div
                  style="display:flex;gap:9px;align-items:center;border-top:1px solid var(--v2-line);padding-top:12px;flex-wrap:wrap"
                >
                  <label
                    class="v2-sub"
                    style="display:flex;align-items:center;gap:5px;font-size:var(--crm-text-xs);cursor:pointer"
                  >
                    <input type="checkbox" name="internal" bind:checked={internal} />
                    {ui('Internal note')}
                  </label>
                  <!-- The whole chip is the click target: a label wrapping a hidden
                     input. A file may ride with the reply or go on its own. -->
                  <label class="attach" class:has-file={fileName}>
                    <Paperclip size={13} />
                    <span class="attach-label">{fileName || 'Attach'}</span>
                    <input
                      bind:this={fileInput}
                      type="file"
                      name="attachment"
                      aria-describedby="ticket-attachment-limit"
                      onchange={pickFile}
                      hidden
                    />
                  </label>
                  {#if fileName}
                    <button
                      type="button"
                      class="clear-file"
                      onclick={clearFile}
                      title={ui('Remove file')}
                    >
                      <X size={12} />
                    </button>
                  {/if}
                  <span class="v2-sub" style="margin-left:auto;font-size:var(--crm-text-xs)"
                    >{ui('Status on send')}</span
                  >
                  <!-- Answering and moving the ticket is one decision, so it is
                     one submit. Empty means "leave the status alone". -->
                  <select
                    name="status"
                    class="v2-input"
                    style="width:auto;font-size:var(--crm-text-xs)"
                  >
                    <option value="">{ui('Unchanged')}</option>
                    <option value="Assigned">{ui('Assigned')}</option>
                    <option value="Pending">{ui('Pending')}</option>
                  </select>
                  <button class="v2-btn v2-btn-primary" disabled={sending || !canSend}>
                    {sending
                      ? ui('Sending…')
                      : body.trim()
                        ? internal
                          ? ui('Add note')
                          : ui('Send reply')
                        : fileName
                          ? ui('Attach file')
                          : internal
                            ? ui('Add note')
                            : ui('Send reply')}
                  </button>
                </div>
              </div>
              {#if internal}
                <p class="v2-sub" style="margin:8px 2px 0;font-size:var(--crm-text-xs)">
                  {ui('A note stays inside the team and does not stop the first-reply clock.')}
                </p>
              {/if}
            </form>
          {:else}
            <p id="ticket-attachment-limit" class="v2-sub">{ui('Up to 25 MB per file.')}</p>
            {#if fileError}<p class="v2-error" role="alert">{ui(fileError)}</p>{/if}
            <p class="v2-sub" style="margin-top:18px;font-size:var(--crm-text-sm)">
              {ui(
                'You can read this ticket but not reply to it. Ask an admin, or whoever it is assigned to.'
              )}
            </p>
          {/if}
        </div>
      </div>
    </div>

    <aside class="v2-rail">
      <div class="v2-label v2-rail-head">{ui('Ticket')}</div>
      <dl class="v2-kv">
        <dt>{ui('Priority')}</dt>
        <dd><Pill tone={PRIORITY_TONE[ticket.priority]}>{ticket.priority}</Pill></dd>
        <dt>{ui('Status')}</dt>
        <dd><Pill tone={CASE_STATUS_TONE[ticket.status]}>{ticket.status}</Pill></dd>
        <dt>{ui('Type')}</dt>
        <dd>{ticket.case_type ?? ui('Not set')}</dd>
        <dt>{ui('Assignee')}</dt>
        <dd>
          {ticket.assignee ?? ui('Unassigned')}
          {#if ticket.assignee_count > 1}
            <span class="v2-sub">+{ticket.assignee_count - 1}</span>
          {/if}
        </dd>
        <dt>{ui('Opened')}</dt>
        <dd>{longDate(ticket.opened_at)}</dd>
        <dt>{ui('First reply')}</dt>
        <dd>
          {#if ticket.first_response_at}
            {relativeTime(ticket.first_response_at)}
          {:else if ticket.first_response_deadline}
            <span style={slaColor(ticket.first_response_breached, ticket.first_response_at_risk)}>
              {ui('due')}
              {relativeTime(ticket.first_response_deadline)}
            </span>
          {:else}
            {ui('No target')}
          {/if}
        </dd>
        {#if ticket.resolved_at}
          <dt>{ui('Resolved')}</dt>
          <dd>{longDate(ticket.resolved_at)}</dd>
        {:else if ticket.resolution_deadline}
          <dt>{ui('Resolve by')}</dt>
          <dd>
            <span style={slaColor(ticket.resolution_breached, ticket.resolution_at_risk)}>
              {relativeTime(ticket.resolution_deadline)}
            </span>
          </dd>
        {/if}
        {#if ticket.paused_at}
          <dt>SLA</dt>
          <dd>{ui('Paused while pending')}</dd>
        {/if}
      </dl>

      {#if ticket.account}
        <div class="v2-label v2-rail-head">{ui('Account')}</div>
        <a
          class="v2-rail-row"
          href={resolve(`/accounts/${ticket.account.id}`)}
          style="color:inherit;text-decoration:none"
        >
          <Avatar name={ticket.account.name} size={29} />
          <div>
            <div style="font-size:var(--crm-text-sm);font-weight:550">{ticket.account.name}</div>
            <div class="v2-sub" style="font-size:var(--crm-text-xs)">
              {#if contacts.length === 1}
                {ui('Reported by')} {contacts[0].name}
              {:else if contacts.length > 1}
                {contacts.length} {ui('people on this ticket')}
              {:else}
                {ui('Nobody named on this ticket')}
              {/if}
            </div>
          </div>
        </a>
      {/if}

      {#if contacts.length}
        <div class="v2-label v2-rail-head">{ui('People')}</div>
        {#each contacts as c (c.id)}
          <a
            class="v2-rail-row"
            href={resolve(`/contacts/${c.id}`)}
            style="color:inherit;text-decoration:none"
          >
            <Avatar name={c.name} size={26} />
            <div style="font-size:var(--crm-text-sm);font-weight:550">{c.name}</div>
          </a>
        {/each}
      {/if}

      <Attachments
        attachments={attachments.map((file) => ({ ...file, href: file.url }))}
        allowUpload={false}
      />

      {#if alsoOpen.length}
        <div class="v2-label v2-rail-head">{ui('Also open here')}</div>
        {#each alsoOpen as t (t.id)}
          <a
            class="v2-rail-row"
            href={resolve(`/tickets/${t.id}`)}
            style="color:inherit;text-decoration:none"
          >
            <div>
              <div style="font-size:var(--crm-text-sm);font-weight:550;line-height:1.35">
                {t.name}
              </div>
              <div class="v2-sub" style="font-size:var(--crm-text-xs)">
                {t.priority} · {shortAge(t.opened_at)}
                {ui('old')}
              </div>
            </div>
          </a>
        {/each}
      {/if}

      {#if activity.length}
        <div class="v2-label v2-rail-head">{ui('History')}</div>
        {#each activity.slice(0, 8) as a (a.id)}
          <div class="v2-rail-row">
            <div>
              <div style="font-size:var(--crm-text-sm);font-weight:550;line-height:1.35">
                {a.label}
              </div>
              <div class="v2-sub" style="font-size:var(--crm-text-xs)">
                {a.by ?? ui('System')} · {shortAge(a.at)}
                {ui('ago')}
              </div>
            </div>
          </div>
        {/each}
      {/if}
    </aside>
  </div>
{:else}
  <TicketProfile {data} {form} onadvanced={() => (advanced = true)} />
{/if}

<style>
  /* The confirm step for closing a parent. Everything in it stacks, so it
     holds at 390px without a media query of its own. */
  .v2-close-panel {
    padding: 15px var(--crm-space-4);
    margin-bottom: 18px;
  }
  .v2-close-list {
    list-style: none;
    margin: 10px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 180px;
    overflow-y: auto;
  }
  .v2-close-list li {
    display: flex;
    gap: var(--crm-space-2);
    align-items: center;
    justify-content: space-between;
    font-size: var(--crm-text-sm);
  }
  /* The name truncates and the status pill never does: which tickets these are
     matters less than the fact that they are open. */
  .v2-close-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .v2-close-check {
    display: flex;
    gap: 9px;
    align-items: flex-start;
    margin-top: 13px;
    font-size: var(--crm-text-sm);
    cursor: pointer;
  }
  .v2-close-check input {
    margin-top: 2px;
    flex: none;
  }

  /* Identity mark for a ticket that has no account to show a face for. */
  .ticket-glyph {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: var(--v2-line-soft);
    border: 1px solid var(--v2-line);
    color: var(--v2-slate);
  }

  /* The composer's attach control, sized to sit in the action row beside the
     Internal-note toggle. */
  .attach {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 9px;
    font-size: var(--crm-text-xs);
    color: var(--v2-slate);
    border: 1px solid var(--v2-line);
    border-radius: var(--crm-radius-md);
    cursor: pointer;
  }
  .attach:hover,
  .attach.has-file {
    color: var(--v2-ink);
    border-color: var(--v2-slate);
  }
  .attach .attach-label {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .clear-file {
    display: grid;
    place-items: center;
    padding: var(--crm-space-1);
    border: none;
    background: transparent;
    color: var(--v2-slate);
    cursor: pointer;
    border-radius: var(--crm-radius-sm);
  }
  .clear-file:hover {
    color: var(--v2-rust);
    background: var(--v2-hover);
  }
</style>
