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
          {#each issue.fields as field}<li>{field.label}</li>{/each}
        </ul>{/if}
    </div>
  </div>{/if}

<style>
  .stage-notice {
    display: flex;
    gap: 12px;
    padding: 16px;
    margin: 0 0 18px;
    background: #fff8ec;
    border: 1px solid #dec493;
    border-left: 4px solid #a77525;
    border-radius: 8px;
    color: #624618;
    font-size: 13px;
    line-height: 1.5;
  }
  .stage-notice :global(svg) {
    flex-shrink: 0;
    margin-top: 2px;
  }
  strong {
    font-size: 14px;
  }
  p {
    margin: 5px 0;
  }
  ul {
    padding-left: 18px;
    margin: 6px 0 0;
  }
  :global(.stage-missing) {
    border-color: #b37720 !important;
    box-shadow: 0 0 0 2px #c18b3530 !important;
    background-color: #fffaf0 !important;
  }
</style>
