<script>
  import { tick } from 'svelte';
  import { TriangleAlert } from '@lucide/svelte';
  import { fieldNames } from './feedback.js';
  let { issue, scope = null, completion = false } = $props();
  let notice = $state(null);
  $effect(() => {
    const current = issue;
    if (!current) return;
    let active = true;
    const marked = [];
    tick().then(() => {
      if (!active) return;
      const root = scope || notice?.closest('form') || document;
      for (const field of current.fields || []) {
        const names = fieldNames(field.key);
        const nodes = [...(root?.querySelectorAll('input,select,textarea') || [])].filter(
          (node) => names.includes(node.name) && node.type !== 'hidden'
        );
        for (const group of root?.querySelectorAll('[data-stage-field]') || []) {
          if (names.includes(group.dataset.stageField))
            nodes.push(...group.querySelectorAll('input:not([type=hidden]),select,textarea'));
        }
        for (const node of new Set(nodes)) {
          for (
            let details = node.closest('details');
            details;
            details = details.parentElement?.closest('details')
          )
            details.open = true;
          const previous = node.getAttribute('aria-invalid');
          node.classList.add('stage-missing');
          node.setAttribute('aria-invalid', 'true');
          const clear = () => {
            node.classList.remove('stage-missing');
            if (previous == null) node.removeAttribute('aria-invalid');
            else node.setAttribute('aria-invalid', previous);
          };
          node.addEventListener('input', clear);
          marked.push(() => {
            clear();
            node.removeEventListener('input', clear);
          });
        }
      }
      notice?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
    return () => {
      active = false;
      marked.forEach((clear) => clear());
    };
  });
</script>

{#if issue}<div class="stage-notice" role="alert" tabindex="-1" bind:this={notice}>
    <TriangleAlert size={20} />
    <div>
      <strong
        >{issue.code === 'source_stage'
          ? 'This stage change is not allowed'
          : `Complete the requirements for ${issue.stage_label}`}</strong
      >
      <p>
        {issue.code === 'source_stage'
          ? issue.message
          : completion
            ? 'Complete the fields below, then choose Save and move.'
            : 'The stage has not changed. Complete the highlighted fields, then save again.'}
      </p>
      {#if issue.fields?.length}<ul>
          {#each issue.fields as field}<li>
              {field.label}{#if field.is_read_only === true || field.is_read_only === 'True'}
                — managed in Calendar. Schedule the appointment there before entering this stage.{/if}
            </li>{/each}
        </ul>{/if}
    </div>
  </div>{/if}

<style>
  .stage-notice {
    display: flex;
    gap: var(--crm-space-3);
    padding: var(--crm-space-4);
    margin: 0 0 18px;
    background: var(--crm-warning-bg);
    border: 1px solid var(--crm-warning);
    border-left: 4px solid var(--crm-warning);
    border-radius: var(--crm-radius-md);
    color: var(--crm-warning);
    font-size: var(--crm-text-sm);
    line-height: 1.5;
  }
  .stage-notice :global(svg) {
    flex-shrink: 0;
    margin-top: 2px;
  }
  strong {
    font-size: var(--crm-text-sm);
  }
  p {
    margin: 5px 0;
  }
  ul {
    padding-left: 18px;
    margin: 6px 0 0;
  }
  :global(.stage-missing) {
    border-color: var(--crm-warning) !important;
    box-shadow: 0 0 0 2px var(--crm-warning-bg) !important;
    background-color: var(--crm-warning-bg) !important;
  }
</style>
