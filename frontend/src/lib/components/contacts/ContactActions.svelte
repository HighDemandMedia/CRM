<script>
  import * as Dropdown from '$lib/components/ui/dropdown-menu/index.js';
  import { ChevronDown, Pencil, Merge, ExternalLink } from '@lucide/svelte';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import ContactMerge from './ContactMerge.svelte';
  /** @type {{contact:any, list?:boolean, onEdit?:()=>void, disabled?:boolean}} */
  let {contact, list=false, onEdit, disabled=false} = $props();
  let mergeOpen = $state(false);
</script>
<Dropdown.Root>
  <Dropdown.Trigger class={list ? "v2-btn compact-contact-actions" : "v2-btn"} {disabled} aria-label={`Actions for ${contact.name}`}>Actions <ChevronDown size={13}/></Dropdown.Trigger>
  <Dropdown.Content align="end">
    {#if list}<Dropdown.Item>{#snippet child({props})}<a {...props} href={resolve(`/contacts/${contact.id}`)}><ExternalLink size={14}/>Open</a>{/snippet}</Dropdown.Item>{/if}
    {#if onEdit}<Dropdown.Item onclick={onEdit}><Pencil size={14}/>Edit</Dropdown.Item>
    {:else}<Dropdown.Item>{#snippet child({props})}<a {...props} href={resolve(`/contacts/${contact.id}/edit`)}><Pencil size={14}/>Edit</a>{/snippet}</Dropdown.Item>{/if}
    {#if page.data.role === 'ADMIN' || page.data.isSuperAdmin}<Dropdown.Item onclick={() => mergeOpen = true}><Merge size={14}/>Merge</Dropdown.Item>{/if}
  </Dropdown.Content>
</Dropdown.Root>
{#if mergeOpen}<ContactMerge {contact} onClose={() => mergeOpen = false}/>{/if}

<style>
  :global(.compact-contact-actions) { padding:4px 8px; font-size:12px; min-height:30px; }
</style>
