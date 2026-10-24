<script>
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import Notice from '$lib/components/Notice.svelte';
  import { useI18n } from '$lib/i18n/context.js';

  const { ui, count } = useI18n();
  let { organization, onclose } = $props();
  let open = $state(true);
  let saving = $state(false);
  let message = $state('');
  const fields = [
    ['users', 'Users'],
    ['contacts', 'Contacts'],
    ['companies', 'Companies'],
    ['deals', 'Deals'],
    ['tasks', 'Tasks'],
    ['tickets', 'Tickets'],
    ['appointments', 'Appointments']
  ];
  // Commercial starting points by resource, not infrastructure capacity guarantees.
  const presets = {
    users: [1, 2, 3, 5, 10, 15, 25, 50, 100],
    contacts: [1000, 2500, 5000, 10000, 25000, 50000, 100000],
    companies: [100, 250, 500, 1000, 2500, 5000, 10000],
    deals: [250, 500, 1000, 2500, 5000, 10000, 25000],
    tasks: [1000, 2500, 5000, 10000, 25000, 50000, 100000],
    tickets: [500, 1000, 2500, 5000, 10000, 25000, 50000],
    appointments: [500, 1000, 2500, 5000, 10000, 25000, 50000]
  };
  const suggestions = (key) => presets[key];
  // Preserve existing custom limits when opening the editor.
  let choices = $state(
    untrack(() =>
      Object.fromEntries(
        fields.map(([key]) => {
          const value = organization.limits[key];
          return [
            key,
            {
              selected:
                value == null
                  ? ''
                  : value === 0 || suggestions(key).includes(value)
                    ? String(value)
                    : 'custom',
              custom: value ?? undefined
            }
          ];
        })
      )
    )
  );
  const belowUsage = $derived(
    fields
      .filter(([key]) => {
        const choice = choices[key];
        const value = choice.selected === 'custom' ? choice.custom : choice.selected;
        const used = key === 'users' ? organization.reserved_users : organization[key];
        return value !== '' && value != null && Number(value) < used;
      })
      .map(([, label]) => ui(label))
  );
</script>

<Dialog.Root bind:open onOpenChange={(value) => !value && onclose()}>
  <Dialog.Content class="limits-dialog" portalProps={{}}>
    <Dialog.Header class="">
      <Dialog.Title class="">{ui('Organization limits')}</Dialog.Title>
      <Dialog.Description class="">{organization.name}</Dialog.Description>
    </Dialog.Header>
    <form
      method="POST"
      action="?/limits"
      use:enhance={() => {
        saving = true;
        message = '';
        return async ({ result, update }) => {
          saving = false;
          if (result.type === 'success') {
            await update();
            onclose();
          } else {
            message =
              result.type === 'failure' && typeof result.data?.limitsError === 'string'
                ? result.data.limitsError
                : 'Could not save limits.';
          }
        };
      }}
    >
      <input type="hidden" name="organization_id" value={organization.id} />
      {#if message}<Notice message={ui(message)} />{/if}
      <div class="limit-fields">
        {#each fields as [key, label] (key)}
          <div class="limit-row">
            <label for={`quota-${key}`}
              >{ui(label)}<span
                >{ui('Used')}: {count(
                  key === 'users' ? organization.reserved_users : organization[key]
                )}</span
              ></label
            >
            <div class="limit-control">
              <select
                id={`quota-${key}`}
                class="v2-input"
                name={choices[key].selected === 'custom' ? undefined : key}
                bind:value={choices[key].selected}
                disabled={saving}
              >
                <option value="">{ui('No limit')}</option>
                <option value="0">{ui('Blocked (0)')}</option>
                {#each suggestions(key) as amount (amount)}
                  <option value={String(amount)}>{count(amount)}</option>
                {/each}
                <option value="custom">{ui('Custom…')}</option>
              </select>
              {#if choices[key].selected === 'custom'}
                <input
                  class="v2-input"
                  aria-label={`${ui(label)}: ${ui('Custom limit')}`}
                  name={key}
                  type="number"
                  min="0"
                  max="2147483647"
                  step="1"
                  inputmode="numeric"
                  placeholder={ui('Custom limit')}
                  bind:value={choices[key].custom}
                  required
                  disabled={saving}
                />
              {/if}
            </div>
          </div>
        {/each}
      </div>
      {#if belowUsage.length}
        <Notice
          tone="warning"
          title={belowUsage.join(', ')}
          message={ui(
            'Below current usage. Existing data and access stay; new additions are blocked.'
          )}
        />
      {/if}
      <p class="hint">{ui('Users include pending invitations. Support access does not count.')}</p>
      <div class="actions">
        <button type="button" class="v2-btn" onclick={onclose} disabled={saving}
          >{ui('Cancel')}</button
        >
        <button type="submit" class="v2-btn v2-btn-primary" disabled={saving}
          >{ui(saving ? 'Saving…' : 'Save limits')}</button
        >
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<style>
  :global(.limits-dialog) {
    width: min(32rem, calc(100vw - 2rem));
    max-width: 32rem;
    max-height: calc(100dvh - 2rem);
    overflow-y: auto;
    background: var(--crm-surface);
  }
  .hint {
    color: var(--v2-slate);
    font-size: var(--crm-text-sm);
    margin: 0 0 var(--crm-space-3);
  }
  .limit-fields {
    display: grid;
    gap: var(--crm-space-3);
    margin-bottom: var(--crm-space-4);
  }
  .limit-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 55%);
    gap: var(--crm-space-3);
    align-items: center;
  }
  label {
    font-size: var(--crm-text-sm);
    font-weight: 600;
  }
  label span {
    display: block;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
    font-weight: 400;
  }
  .limit-control {
    display: grid;
    gap: var(--crm-space-2);
    min-width: 0;
  }
  input,
  select {
    width: 100%;
    min-width: 0;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--crm-space-2);
  }
</style>
