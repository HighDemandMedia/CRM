<script>
  import { untrack } from 'svelte';
  import { invalidate } from '$app/navigation';
  import { watchRecordMail } from '$lib/mail/watch-record-mail.js';

  /** @type {{kind:'contact'|'company',id:string,active:boolean,onStatus:(data:any)=>void}} */
  let { kind, id, active, onStatus } = $props();
  let previous = '';
  let previousRecord = '';
  $effect(() => {
    const record = `${kind}:${id}`;
    const dependency = `crm:record:${kind === 'contact' ? 'Contact' : 'Account'}:${id}`;
    const endpoint = `/api/record-mail/${kind}/${id}`;
    if (!active) return;
    return untrack(() => {
      if (previousRecord !== record) {
        previousRecord = record;
        previous = '';
      }
      return watchRecordMail({
        endpoint,
        onStatus: async (status) => {
          onStatus(status);
          if (status.revision !== previous) {
            // Keyed activity items retain their expanded state; no navigation or full reload.
            await invalidate(dependency);
            previous = status.revision;
          }
        },
        onUnavailable: () => invalidate(dependency)
      });
    });
  });
</script>
