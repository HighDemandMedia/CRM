<script>
  import AssociationPicker from '$lib/components/creation/AssociationPicker.svelte';
  let { values = $bindable(), options } = $props();
  const labels = { contact: 'Contact', account: 'Company', deal: 'Deal' };
  const paths = { contact: 'contacts', account: 'accounts', deal: 'pipeline' };
  const records = $derived(
    [
      ...(options.contacts ?? []).map((record) => ({ ...record, type: 'contact' })),
      ...(options.accounts ?? []).map((record) => ({ ...record, type: 'account' })),
      ...(options.deals ?? []).map((record) => ({ ...record, type: 'deal' }))
    ].map((record) => ({
      ...record,
      label: labels[record.type],
      href: `/${paths[record.type]}/${record.id}`
    }))
  );
  function record(type, id) {
    return (
      records.find((item) => item.type === type && item.id === id) ?? {
        type,
        id,
        label: labels[type],
        name: labels[type]
      }
    );
  }
  const chosen = $derived([
    ...(values.contacts ?? []).map((id) => record('contact', id)),
    ...(values.account ? [record('account', values.account)] : []),
    ...(values.deal ? [record('deal', values.deal)] : [])
  ]);
  function choose(record) {
    if (record.type === 'contact') values.contacts = [...(values.contacts ?? []), record.id];
    else values[record.type] = record.id;
  }
  function remove(record) {
    if (record.type === 'contact')
      values.contacts = values.contacts.filter((id) => id !== record.id);
    else values[record.type] = '';
  }
</script>

<AssociationPicker
  {records}
  {chosen}
  onselect={choose}
  onremove={remove}
  label="Associated Objects"
/>
<input type="hidden" name="account" value={values.account ?? ''} />
<input type="hidden" name="deal" value={values.deal ?? ''} />
{#each values.contacts ?? [] as contact (contact)}<input
    type="hidden"
    name="contacts"
    value={contact}
  />{/each}
