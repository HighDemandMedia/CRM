<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { onMount } from 'svelte';

  onMount(() => {
    setTimeout(() => {
      window.location.href = '/org';
    });
  });
</script>

<svelte:head>
  <title>{ui('Signing you in · High Demand Media CRM')}</title>
</svelte:head>

<div class="v2-root v2-auth">
  <div class="v2-auth-box" style="text-align:center">
    <div class="v2-spin" style="width:24px;height:24px;margin:0 auto;color:var(--crm-link)"></div>
    <p class="v2-sub" style="margin-top:12px">{ui('Signing you in…')}</p>
  </div>
</div>
