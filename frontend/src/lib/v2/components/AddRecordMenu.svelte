<script>
  import { tick } from 'svelte';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { Plus, Upload, ChevronDown } from '@lucide/svelte';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
  import { useI18n } from '$lib/i18n/context.js';
  import { can } from '$lib/v2/permissions.js';
  import ImportDialog from './ImportDialog.svelte';

  let { module } = $props();
  const { ui } = useI18n();
  const objects = {
    contacts: {
      add: 'Add contact',
      create: 'Create contact',
      import: 'Import contacts',
      path: '/contacts/new'
    },
    companies: {
      add: 'Add company',
      create: 'Create company',
      import: 'Import companies',
      path: '/accounts/new'
    },
    deals: {
      add: 'Add deal',
      create: 'Create deal',
      import: 'Import deals',
      path: '/pipeline/new'
    },
    tasks: { add: 'Add task', create: 'Create task', import: 'Import tasks', path: '/tasks/new' },
    tickets: {
      add: 'Add ticket',
      create: 'Create ticket',
      import: 'Import tickets',
      path: '/tickets/new'
    }
  };
  let object = $derived(objects[module]);
  let importer = $state(),
    trigger = $state(null);
  let openingDialog = false;
  async function restoreFocus() {
    await tick();
    trigger?.focus();
  }
</script>

{#if can(page.data.permissions, module, 'create')}
  <DropdownMenu.Root>
    <DropdownMenu.Trigger bind:ref={trigger} class="v2-btn v2-btn-primary">
      <Plus size={16} aria-hidden="true" />{ui(object.add)}<ChevronDown
        size={14}
        aria-hidden="true"
      />
    </DropdownMenu.Trigger>
    <DropdownMenu.Content
      class="w-(--bits-dropdown-menu-anchor-width)"
      align="end"
      onCloseAutoFocus={(event) => {
        if (openingDialog) event.preventDefault();
        openingDialog = false;
      }}
    >
      <DropdownMenu.Item>
        {#snippet child({ props })}
          <a {...props} href={resolve(asInternalPath(object.path))}
            ><Plus size={16} aria-hidden="true" />{ui(object.create)}</a
          >
        {/snippet}
      </DropdownMenu.Item>
      {#if page.data.permissions?.is_admin}
        <DropdownMenu.Item
          onSelect={() => {
            openingDialog = true;
            importer.show();
          }}
        >
          <Upload size={16} aria-hidden="true" />{ui(object.import)}
        </DropdownMenu.Item>
      {/if}
    </DropdownMenu.Content>
  </DropdownMenu.Root>
  {#if page.data.permissions?.is_admin}
    <ImportDialog bind:this={importer} {module} onDismiss={restoreFocus} hideTrigger />
  {/if}
{/if}
