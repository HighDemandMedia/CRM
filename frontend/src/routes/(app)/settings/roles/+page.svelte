<script>
  import {enhance} from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import {Plus, ShieldCheck, Pencil, Copy} from '@lucide/svelte';
  let {data,form}=$props();
  let editing=$state(null), busy=$state(false), error=$state('');
  const labels={contacts:'Contacts',companies:'Companies',deals:'Deals',tasks:'Tasks',tickets:'Tickets'};
  const scopes=[['own','Personal'],['team','Team'],['organization','Organization']];
  function edit(role) {
    error='';
    editing=structuredClone(role || {name:'',description:'',scope:'own',rules:Object.fromEntries(Object.keys(labels).map(module=>[module,{view:'own',create:true,edit:'own',delete:'none',export:'none',reassign:'none'}]))});
    editing.scope = role?.name === 'Member' && role?.id ? 'own' : role?.name === 'Manager' && role?.id ? 'team' : role?.scope || 'own';
    editing.enabled = Object.fromEntries(Object.entries(editing.rules).map(([module,row])=>[module,Object.fromEntries(['view','create','edit','delete','export','reassign'].map(action=>[action,action === 'create' ? row[action] === true : !!row[action] && row[action] !== 'none']))]));
  }
  function rulesForSave() {
    return Object.fromEntries(Object.entries(editing.enabled).map(([module,row])=>[module,Object.fromEntries(Object.entries(row).map(([action,allowed])=>[action,action === 'create' ? allowed : allowed && row.view ? editing.scope : 'none']))]));
  }
  function duplicate(role) {
    edit({...role,id:null,name:`${role.name} copy`,member_count:0});
  }
</script>
<PageHeader title="Roles & Permissions">
  {#snippet sub()}Create permission sets and assign them to users in Users & Teams{/snippet}
  {#snippet actions()}{#if !data.forbidden}<button class="v2-btn v2-btn-primary" onclick={()=>edit(null)}><Plus size={15}/>New permission set</button>{/if}{/snippet}
</PageHeader>
<div class="v2-scroll"><div class="roles-content">
  {#if data.forbidden}<p>Only organization admins can manage roles and permissions.</p>
  {:else if editing}
    <form method="POST" action="?/save" use:enhance={()=>{busy=true;return async ({result,update})=>{try{if(result.type==='success'){await update();editing=null;}else{error=result.type === 'failure' ? String(result.data?.error || 'Could not save role.') : 'Could not save role.';}}finally{busy=false;}};}}>
      <input type="hidden" name="id" value={editing.id || ''}/><input type="hidden" name="rules" value={JSON.stringify(rulesForSave())}/>
      <div class="identity"><label>Permission set name<input class="v2-input" name="name" readonly={editing.id && ['Member','Manager'].includes(editing.name)} bind:value={editing.name} required maxlength="80"/></label><label>Description<input class="v2-input" name="description" bind:value={editing.description} maxlength="255"/></label></div>
      <div class="scope-field">
        {#if editing.id && ['Member','Manager'].includes(editing.name)}
          <div class="fixed-scope"><span>Access level</span><strong>{editing.name === 'Member' ? 'Personal' : 'Team'}</strong></div>
          <input type="hidden" name="scope" value={editing.scope}/>
        {:else}
          <label>Access level<select name="scope" class="v2-input" bind:value={editing.scope}>{#each scopes as [value,label]}<option {value}>{label}</option>{/each}</select></label>
        {/if}
      </div>
      <div class="matrix"><table><thead><tr><th>Module</th><th>View</th><th>Create</th><th>Edit</th><th>Delete</th><th>Export</th><th>Assign owner</th></tr></thead><tbody>
        {#each Object.entries(labels) as [module,label]}<tr><th>{label}</th>{#each ['view','create','edit','delete','export','reassign'] as action}<td><input aria-label={`${label}: ${action}`} type="checkbox" bind:checked={editing.enabled[module][action]} disabled={action !== 'view' && action !== 'create' && !editing.enabled[module].view}/></td>{/each}</tr>{/each}
      </tbody></table></div>
      <p class="hint">The selected access level applies to all enabled permissions. Personal covers assigned records; Team includes the user's teams; Organization covers the entire organization.</p>
      {#if editing.member_count}<p class="hint">Changes apply to {editing.member_count} assigned users.</p>{/if}
      {#if error}<p class="error" role="alert">{error}</p>{/if}
      <div class="actions"><button class="v2-btn v2-btn-primary" disabled={busy}>{busy?'Saving…':'Save permission set'}</button><button class="v2-btn" type="button" disabled={busy} onclick={()=>editing=null}>Cancel</button></div>
    </form>
  {:else}
    <div class="role"><div><h2><ShieldCheck size={17}/>Super Admin</h2><p>Organization creator. Full access; cannot be reassigned, demoted or deactivated.</p></div><span class="protected">Creator only</span></div>
    <div class="role"><div><h2><ShieldCheck size={17}/>Admin</h2><p>Assignable administrator. Manages users, teams, permissions and settings; cannot change the Super Admin.</p></div><span class="protected">System role</span></div>
    {#each data.roles as role}<div class="role"><div><h2>{role.name}</h2><p>{role.description || (role.name === 'Manager' ? 'Team access · deletion and export disabled by default' : role.name === 'Member' ? 'Own records · deletion and export disabled by default' : 'Custom permission set')} · {role.member_count} users</p></div><div class="actions"><button class="v2-btn v2-btn-sm" onclick={()=>duplicate(role)} aria-label={`Duplicate ${role.name}`}><Copy size={13}/>Duplicate</button><button class="v2-btn v2-btn-sm" onclick={()=>edit(role)}><Pencil size={13}/>Edit permissions</button></div></div>{/each}
    {#if form?.saved}<p class="success" role="status">Permission set saved.</p>{/if}
  {/if}
</div></div>
<style>
.roles-content{padding:24px 28px;max-width:1150px}.role{display:flex;gap:20px;align-items:center;justify-content:space-between;padding:22px 0;border-bottom:1px solid var(--v2-line-soft)}h2{font-size:15px;margin:0;display:flex;align-items:center;gap:8px}.role p,.hint{color:var(--v2-slate);font-size:12px;line-height:1.6}.protected{font-size:11px;color:var(--v2-slate)}.identity{display:grid;grid-template-columns:1fr 2fr;gap:20px;margin-bottom:26px}label{display:grid;gap:8px;font-size:13px}.scope-field{max-width:260px;margin-bottom:24px}.fixed-scope{display:grid;gap:8px;font-size:13px}.scope-field strong{font-size:14px;font-weight:550;padding:8px 0}.matrix{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:12px 8px;text-align:left;border-bottom:1px solid var(--v2-line-soft)}select{min-width:130px;font-size:12px}input[type=checkbox]{accent-color:var(--v2-ink);width:17px;height:17px}.actions{display:flex;gap:8px;margin-top:24px}.error{color:var(--v2-rust)}.success{color:var(--v2-moss)}@media(max-width:650px){.identity{grid-template-columns:1fr}.roles-content{padding:16px}.role{flex-wrap:wrap}}
</style>
