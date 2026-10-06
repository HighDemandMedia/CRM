<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { can } from '$lib/v2/permissions.js';
  import * as Dropdown from '$lib/components/ui/dropdown-menu/index.js';
  import { ChevronDown, Pencil, Merge, ExternalLink } from '@lucide/svelte';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import ContactMerge from './ContactMerge.svelte';
  /** @type {{contact:any, list?:boolean, onEdit?:()=>void, disabled?:boolean}} */
  let { contact, list = false, onEdit, disabled = false } = $props();
  let mergeOpen = $state(false);
</script>

<Dropdown.Root>
  <Dropdown.Trigger
    class={list ? 'v2-btn compact-contact-actions' : 'v2-btn'}
    {disabled}
    aria-label={`Actions for ${contact.name}`}
    >{ui('Actions')} <ChevronDown size={13} /></Dropdown.Trigger
  >
  <Dropdown.Content align="end">
    {#if list}<Dropdown.Item
        >{#snippet child({ props })}<a {...props} href={resolve(`/contacts/${contact.id}`)}
            ><ExternalLink size={14} />{ui('Open')}</a
          >{/snippet}</Dropdown.Item
      >{/if}
    {#if can(page.data.permissions, 'contacts', 'edit')}{#if onEdit}<Dropdown.Item onclick={onEdit}
          ><Pencil size={14} />{ui('Edit')}</Dropdown.Item
        >
      {:else}<Dropdown.Item
          >{#snippet child({ props })}<a {...props} href={resolve(`/contacts/${contact.id}/edit`)}
              ><Pencil size={14} />{ui('Edit')}</a
            >{/snippet}</Dropdown.Item
        >{/if}
    {/if}
    {#if page.data.role === 'ADMIN' || page.data.isSuperAdmin}<Dropdown.Item
        onclick={() => (mergeOpen = true)}><Merge size={14} />{ui('Merge')}</Dropdown.Item
      >{/if}
  </Dropdown.Content>
</Dropdown.Root>
{#if mergeOpen}<ContactMerge {contact} onClose={() => (mergeOpen = false)} />{/if}

<style>
  :global(.compact-contact-actions) {
    padding: var(--crm-space-1) var(--crm-space-2);
    font-size: var(--crm-text-xs);
    min-height: 30px;
  }
</style>
