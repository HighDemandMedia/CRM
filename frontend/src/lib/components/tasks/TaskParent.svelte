<script>
  import AssociationPicker from '$lib/components/creation/AssociationPicker.svelte';
  let {
    parents,
    kind = $bindable(''),
    selected = $bindable(''),
    contacts = $bindable([])
  } = $props();
  const labels = {
    contact: 'Contact',
    account: 'Company',
    opportunity: 'Deal',
    case: 'Ticket',
    lead: 'Lead'
  };
  const paths = {
    contact: 'contacts',
    account: 'accounts',
    opportunity: 'pipeline',
    case: 'tickets'
  };
  const records = $derived(
    Object.entries(parents).flatMap(([type, items]) =>
      items.map((item) => ({
        ...item,
        type,
        label: labels[type],
        href: paths[type] ? `/${paths[type]}/${item.id}` : undefined
      }))
    )
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
    ...(kind && selected ? [record(kind, selected)] : []),
    ...contacts.map((id) => record('contact', id))
  ]);
  function choose(item) {
    if (item.type === 'contact') contacts = [...contacts, item.id];
    else {
      kind = item.type;
      selected = item.id;
    }
  }
  function remove(item) {
    if (item.type === 'contact') contacts = contacts.filter((id) => id !== item.id);
    else {
      kind = '';
      selected = '';
    }
  }
</script>

<AssociationPicker {records} {chosen} onselect={choose} onremove={remove} />
<input type="hidden" name="parent_kind" value={kind} />
{#if kind}<input type="hidden" name={`parent_${kind}`} value={selected} />{/if}
<input type="hidden" name="contacts_present" value="1" />
{#each contacts as contactId (contactId)}<input
    type="hidden"
    name="contacts"
    value={contactId}
  />{/each}
