<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  import { resolve, base } from '$app/paths';
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { LogOut, Plus } from '@lucide/svelte';
  import Notice from '$lib/components/Notice.svelte';

  let { data } = $props();
</script>

<svelte:head>
  <title>{ui('No organizations yet')} · High Demand Media CRM</title>
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
    <div class="v2-auth-card">
      <Notice
        layout="page"
        tone="info"
        title={ui('No organizations yet')}
        message={data.canCreateOrganization
          ? ui('Create your first workspace to get started.')
          : ui('Open the invitation sent to your email, or contact your administrator.')}
      >
        {#snippet actions()}
          {#if data.canCreateOrganization}
            <a href={resolve('/org/new')} class="v2-btn v2-btn-primary">
              <Plus size={15} />{ui('Create organization')}
            </a>
          {/if}
          <a href={resolve('/logout')} class="v2-btn v2-btn-secondary">
            <LogOut size={15} />{ui('Sign out')}
          </a>
        {/snippet}
      </Notice>
    </div>
  </div>
</div>
