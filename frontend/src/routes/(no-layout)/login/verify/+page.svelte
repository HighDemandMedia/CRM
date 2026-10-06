<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { base, resolve } from '$app/paths';
  import '../../../../app.css';
  import '$lib/v2/styles/v2.css';

  let { data } = $props();
</script>

<svelte:head>
  <title>{ui('Verifying · High Demand Media CRM')}</title>
  <meta name="referrer" content="no-referrer" />
</svelte:head>

<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <a href={resolve('/')} class="v2-auth-brand">
      <img
        class="v2-brand-mark"
        src={`${base}/brand/hdm-symbol.png`}
        alt=""
        width="228"
        height="155"
      />
      <b>High Demand Media CRM</b>
    </a>

    <div class="v2-auth-card" style="text-align:center">
      {#if data.error}
        <div class="v2-auth-head" style="margin-bottom:16px">
          <h1>{ui('Link expired or invalid')}</h1>
          <p>{data.error}</p>
        </div>
        <a href={resolve('/login')} class="v2-btn v2-btn-block">{ui('Back to sign in')}</a>
      {:else}
        <div
          class="v2-spin"
          style="width:26px;height:26px;margin:4px auto 15px;color:var(--crm-link)"
        ></div>
        <div class="v2-auth-head" style="margin-bottom:0">
          <h1>{ui('Signing you in…')}</h1>
          <p>{ui('One moment while we verify your link.')}</p>
        </div>
      {/if}
    </div>
  </div>
</div>
