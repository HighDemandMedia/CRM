<script>
  import { tick } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { displayPhone } from '$lib/utils/phone-number.js';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import InlineProperty from './InlineProperty.svelte';
  const { ui } = useI18n();
  /** @type {{target:string,record:any,schema:any,property:'name'|'email'|'phone',onstate?:(active:boolean)=>void}} */
  let { target, record, schema, property, onstate = () => {} } = $props();
  let phoneOpen = $state(false);
  let phoneEditor = $state();
  let textEditor = $state();
  export async function commit() {
    if (property === 'phone') return phoneOpen ? await phoneEditor?.commit() : true;
    return await textEditor?.commit();
  }
  let field = $derived({
    ...schema.fields.find(
      (item) => item.key === (property === 'name' && target === 'Contact' ? 'first_name' : property)
    ),
    key: property,
    label: ui({ name: 'Name', email: 'Email', phone: 'Phone' }[property]),
    required: property === 'name'
  });
</script>

{#if property === 'phone'}
  <Popover.Root bind:open={phoneOpen}>
    <!-- Keep the opening mouse click from stealing focus back from the phone input. -->
    <Popover.Trigger
      class="identity-phone-trigger"
      aria-label={ui('Edit Phone')}
      onmousedown={(event) => event.preventDefault()}
    >
      {record.phone ? displayPhone(record.phone) : ui('Add phone')}
    </Popover.Trigger>
    <Popover.Content
      class="identity-phone-popover"
      align="start"
      collisionPadding={12}
      aria-label={ui('Phone')}
      onOpenAutoFocus={(event) => {
        event.preventDefault();
        void tick().then(() => phoneEditor?.edit());
      }}
      onInteractOutside={(event) => event.preventDefault()}
      onEscapeKeydown={(event) => event.preventDefault()}
    >
      <span class="phone-label">{ui('Phone')}</span>
      <!-- Portal focus changes are not edits; Enter, Tab out and outside clicks commit. -->
      <InlineProperty
        {field}
        value={record.phone}
        {target}
        recordId={record.id}
        bind:this={phoneEditor}
        saveOnBlur={false}
        {onstate}
        onfinish={() => {
          phoneOpen = false;
          onstate(false);
        }}>{record.phone || '—'}</InlineProperty
      >
    </Popover.Content>
  </Popover.Root>
{:else}
  <InlineProperty
    bind:this={textEditor}
    {field}
    value={record[property]}
    {target}
    recordId={record.id}
    persistent
    {onstate}
  >
    {record[property] || (property === 'email' ? ui('Add email') : '—')}
  </InlineProperty>
{/if}

<style>
  :global(.identity-phone-trigger) {
    width: 100%;
    min-height: 32px;
    border: 0;
    border-bottom: 1px solid var(--crm-control-border);
    border-radius: 0;
    padding: 4px 0;
    background: transparent;
    color: var(--v2-ink);
    font: inherit;
    text-align: left;
    cursor: text;
  }
  :global(.identity-phone-trigger:hover) {
    border-bottom-color: var(--crm-focus);
  }
  :global(.identity-phone-trigger:focus-visible),
  :global(.identity-phone-trigger[data-state='open']) {
    outline: none;
    border-bottom-color: var(--crm-focus);
    box-shadow: 0 1px 0 var(--crm-focus);
  }
  :global(.identity-phone-popover .phone-control.phone-control) {
    border: 0;
    border-bottom: 1px solid var(--crm-control-border);
    border-radius: 0;
    background: transparent;
    outline: none;
  }
  :global(.identity-phone-popover .phone-control:focus-within) {
    border-bottom-color: var(--crm-focus);
    box-shadow: 0 1px 0 var(--crm-focus);
  }
  :global(.identity-phone-popover .phone-control input.v2-input) {
    min-height: 32px;
    padding: 4px 8px;
    border-radius: 0;
    cursor: text;
  }
  :global(.identity-phone-popover .phone-control:has([aria-invalid='true'])) {
    border-bottom-color: var(--v2-rust);
    box-shadow: 0 1px 0 var(--v2-rust);
  }
  :global(.identity-phone-popover) {
    width: min(360px, calc(100vw - 24px));
    padding: 14px;
    background: var(--v2-card);
    color: var(--v2-ink);
  }
  .phone-label {
    display: block;
    margin-bottom: 8px;
    color: var(--v2-slate);
    font-size: var(--crm-text-xs);
  }
</style>
