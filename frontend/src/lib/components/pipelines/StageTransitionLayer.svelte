<script>
  import { onMount } from 'svelte';
  import TeamPanel from '$lib/components/team/TeamPanel.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  let request = $state(null);
  let editor = $state(null);
  const loadEditor = () => (editor = import('./StageTransitionEditor.svelte'));
  onMount(() => {
    const open = (event) => {
      if (request) return;
      request = event.detail;
      loadEditor();
    };
    window.addEventListener('crm-stage-requirements', open);
    return () => window.removeEventListener('crm-stage-requirements', open);
  });
</script>

{#if request}
  {#await editor}
    <TeamPanel title={ui('Stage change blocked')} onclose={() => (request = null)}>
      <p role="status">{ui('Loading…')}</p>
    </TeamPanel>
  {:then module}
    <module.default initial={request} onclose={() => (request = null)} />
  {:catch}
    <TeamPanel title={ui('Stage change blocked')} onclose={() => (request = null)}>
      <Notice message={ui('Could not open the form. Please try again.')} />
      <button class="v2-btn" onclick={loadEditor}>{ui('Try again')}</button>
    </TeamPanel>
  {/await}
{/if}
