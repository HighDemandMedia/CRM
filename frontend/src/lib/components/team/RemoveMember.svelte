<script>
  import {invalidateAll} from '$app/navigation';
  import {resolve} from '$app/paths';
  let {id, hideTrigger = false}=$props();
  let dialog;
  let preview=$state(null), loading=$state(false), busy=$state(false), error=$state(''), confirmation=$state(''), reassign=$state('');
  export async function open() {
    preview=null;error='';confirmation='';reassign='';loading=true;dialog.showModal();
    try {
      const response=await fetch(resolve(`/team/${id}/remove`));
      const data=await response.json();
      if (!response.ok) throw new Error(data.message);
      preview=data;
    } catch(err) {error=err.message;} finally {loading=false;}
  }
  async function remove() {
    if (!preview || confirmation!==preview.email || busy) return;
    busy=true;error='';
    try {
      const response=await fetch(resolve(`/team/${id}/remove`),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:preview.token,confirmation,reassign_to:reassign || null})});
      const data=await response.json();
      if (!response.ok) throw new Error(data.message);
      dialog.close();await invalidateAll();
    } catch(err) {error=err.message;} finally {busy=false;}
  }
</script>
{#if !hideTrigger}<button class="v2-btn v2-btn-sm danger" type="button" onclick={open}>Remove</button>{/if}
<dialog bind:this={dialog} aria-labelledby={`remove-member-${id}`} oncancel={e=>{if(busy)e.preventDefault();}}>
  <h2 id={`remove-member-${id}`}>Remove from organization</h2>
  {#if loading}<p>Loading assigned records…</p>{:else if preview}
    <p><strong>{preview.name}</strong> will lose access to this organization. Their account and access to other organizations will remain.</p>
    <p>Records, history and meetings are kept. Team membership and access tokens for this organization are removed.</p>
    <div class="counts">{#each Object.entries(preview.counts) as [label,count]}<span>{label}: <strong>{count}</strong></span>{/each}</div>
    <label>Reassign their records to<select class="v2-input" bind:value={reassign} disabled={busy}><option value="">Remove their assignment only</option>{#each preview.candidates as person}<option value={person.id}>{person.name}{preview.candidates.filter(p => p.name === person.name).length > 1 ? ` · ${person.email}` : ''}</option>{/each}</select></label>
    <p class="hint">Other assigned users stay assigned. Without a replacement, records with no remaining owner become unassigned.</p>
    <label>Type <strong>{preview.email}</strong> to confirm<input class="v2-input" aria-label="Confirm user email" bind:value={confirmation} disabled={busy} autocomplete="off" spellcheck="false" /></label>
  {/if}
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <div class="actions"><button class="v2-btn" type="button" disabled={busy} onclick={()=>dialog.close()}>Cancel</button><button class="v2-btn danger" type="button" disabled={loading || busy || !preview || confirmation!==preview.email} onclick={remove}>{busy?'Removing…':'Remove from organization'}</button></div>
</dialog>
<style>
  dialog{width:min(520px,calc(100vw - 32px));max-height:85vh;overflow:auto;border:1px solid var(--v2-line-soft);border-radius:16px;padding:24px;color:var(--v2-ink);background:var(--v2-white,#fff);text-align:left}dialog::backdrop{background:#0005}h2{font-size:19px;margin:0 0 18px}p{font-size:13px;line-height:1.6}label{display:grid;gap:8px;font-size:13px;margin:18px 0}.counts{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;padding:12px 0}.hint{color:var(--v2-slate);font-size:12px}.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:24px}.danger,.error{color:var(--v2-rust,#b42318)}
</style>
