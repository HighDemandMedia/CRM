<script>
  import RecordAction from '$lib/v2/components/RecordAction.svelte';
  import { resolve } from '$app/paths';
  import { can } from '$lib/v2/permissions.js';
  import { page } from '$app/state';
  import { useI18n } from '$lib/i18n/context.js';
  import * as Dropdown from '$lib/components/ui/dropdown-menu/index.js';
  import {
    Trash2,
    ChevronDown,
    Ellipsis,
    Merge,
    ListTodo,
    Ticket,
    Pencil,
    ExternalLink
  } from '@lucide/svelte';
  import DeleteRecord from '$lib/v2/components/DeleteRecord.svelte';
  import RecordMerge from '$lib/components/RecordMerge.svelte';
  const { ui } = useI18n();
  /** @type {{company:any, disabled?:boolean, list?:boolean}} */
  let { company, disabled = false, list = false } = $props();
  let deleteDialog = $state();
  let mergeOpen = $state(false);
</script>

{#if !list}
  {#if can(page.data.permissions, 'tasks', 'create')}<RecordAction
      icon={ListTodo}
      label={ui('Create task')}
      {disabled}
      href={resolve(`/tasks/new?account=${encodeURIComponent(company.id)}`)}
    />{/if}
  {#if can(page.data.permissions, 'tickets', 'create')}<RecordAction
      icon={Ticket}
      label={ui('Create ticket')}
      {disabled}
      href={resolve(`/tickets/new?account=${encodeURIComponent(company.id)}`)}
    />{/if}
{/if}

{#if list || can(page.data.permissions, 'companies', 'delete') || page.data.role === 'ADMIN' || page.data.isSuperAdmin}
  <Dropdown.Root>
    <Dropdown.Trigger
      class={list ? 'v2-btn compact-company-actions' : 'v2-btn record-more-actions'}
      {disabled}
      aria-label={list ? `Actions for ${company.name}` : ui('More actions')}
      title={list ? undefined : ui('More actions')}
    >
      {#if list}{ui('Actions')} <ChevronDown size={13} />{:else}<Ellipsis size={18} />{/if}
    </Dropdown.Trigger>
    <Dropdown.Content align="start" class={list ? undefined : 'record-actions-menu'}>
      {#if list}
        <Dropdown.Item
          >{#snippet child({ props })}<a {...props} href={resolve(`/accounts/${company.id}`)}
              ><ExternalLink size={14} />{ui('Open')}</a
            >{/snippet}</Dropdown.Item
        >
        {#if can(page.data.permissions, 'companies', 'edit')}
          <Dropdown.Item
            >{#snippet child({ props })}<a {...props} href={resolve(`/accounts/${company.id}/edit`)}
                ><Pencil size={14} />{ui('Edit')}</a
              >{/snippet}</Dropdown.Item
          >
        {/if}
      {/if}
      {#if list && can(page.data.permissions, 'tasks', 'create')}
        <Dropdown.Item
          >{#snippet child({ props })}<a
              {...props}
              href={resolve(`/tasks/new?account=${encodeURIComponent(company.id)}`)}
              ><ListTodo size={14} />{ui('Create task')}</a
            >{/snippet}</Dropdown.Item
        >
      {/if}
      {#if list && can(page.data.permissions, 'tickets', 'create')}
        <Dropdown.Item
          >{#snippet child({ props })}<a
              {...props}
              href={resolve(`/tickets/new?account=${encodeURIComponent(company.id)}`)}
              ><Ticket size={14} />{ui('Create ticket')}</a
            >{/snippet}</Dropdown.Item
        >
      {/if}
      {#if page.data.role === 'ADMIN' || page.data.isSuperAdmin}
        <Dropdown.Item onclick={() => (mergeOpen = true)}
          ><Merge size={14} />{ui('Merge')}</Dropdown.Item
        >
      {/if}
      {#if !list && can(page.data.permissions, 'companies', 'delete')}
        <Dropdown.Separator />
        <Dropdown.Item variant="destructive" onclick={() => deleteDialog?.open()}
          ><Trash2 size={14} />{ui('Delete')}</Dropdown.Item
        >
      {/if}
    </Dropdown.Content>
  </Dropdown.Root>
{/if}
{#if mergeOpen}<RecordMerge
    record={company}
    kind="company"
    onClose={() => (mergeOpen = false)}
  />{/if}

{#if !list && can(page.data.permissions, 'companies', 'delete')}<DeleteRecord
    bind:this={deleteDialog}
    kind="company"
    id={company.id}
    showTrigger={false}
  />{/if}

<style>
  :global(.compact-company-actions) {
    padding: var(--crm-space-1) 6px;
    gap: 4px;
    max-width: 100%;
    font-size: var(--crm-text-xs);
    min-height: 30px;
  }
</style>
