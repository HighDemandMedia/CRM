<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();

  import { resolve, base } from '$app/paths';
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import { Building2, LogOut, Plus, ChevronRight } from '@lucide/svelte';
  import { enhance } from '$app/forms';

  let { data = { orgs: [], canCreateOrganization: false, uiLocale: 'en' } } = $props();
  let orgs = $derived(data?.orgs ?? []);

  let loading = $state(false);
  let selectedOrgId = $state(null);
</script>

<svelte:head>
  <title>{ui('Choose organisation · High Demand Media CRM')}</title>
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
      <div class="v2-auth-head">
        <h1>{ui('Choose an organisation')}</h1>
        <p>
          {orgs.length
            ? ui("Pick the workspace you'd like to open.")
            : data.canCreateOrganization
              ? ui('Create your first workspace to get started.')
              : ui('Use your invitation to join your organization.')}
        </p>
      </div>

      {#if orgs.length > 0}
        {#each orgs as org (org.id)}
          <form
            method="POST"
            action="?/selectOrg"
            use:enhance={() => {
              loading = true;
              selectedOrgId = org.id;
              return async ({ update }) => {
                await update();
                loading = false;
                selectedOrgId = null;
              };
            }}
          >
            <input type="hidden" name="org_id" value={org.id} />
            <input type="hidden" name="org_name" value={org.name} />
            <button type="submit" class="v2-auth-org" disabled={loading}>
              <span
                class="v2-mark"
                style="width:30px;height:30px;border-radius:8px;font-size:var(--crm-text-sm)"
              >
                {org.name?.slice(0, 1)?.toUpperCase() || '?'}
              </span>
              <span class="v2-auth-org-body">
                <b>{org.name}</b>
                <span class="v2-sub" style="display:block;text-transform:capitalize">
                  {org.role?.toLowerCase() || ui('member')}
                </span>
              </span>
              {#if loading && selectedOrgId === org.id}
                <span class="v2-spin"></span>
              {:else}
                <ChevronRight />
              {/if}
            </button>
          </form>
        {/each}

        {#if data.canCreateOrganization}
          <a href={resolve('/org/new')} class="v2-auth-add">
            <Plus />
            {ui('Create new organisation')}
          </a>
        {/if}
      {:else}
        <div class="v2-state" style="padding:22px 0 8px">
          <div class="v2-state-icon"><Building2 size={22} /></div>
          <h3>{ui('No organisations yet')}</h3>
          {#if data.canCreateOrganization}
            <p>{ui('Create your first workspace to start using High Demand Media CRM.')}</p>
            <a href={resolve('/org/new')} class="v2-btn v2-btn-primary">
              <Plus size={15} />
              {ui('Create organisation')}
            </a>
          {:else}<p>
              {ui('Open the invitation sent to your email, or contact your administrator.')}
            </p>{/if}
        </div>
      {/if}
    </div>

    <div class="v2-auth-foot">
      <a href={resolve('/logout')} style="display:inline-flex;align-items:center;gap:5px">
        <LogOut size={13} />
        {ui('Sign out')}
      </a>
    </div>
  </div>
</div>
