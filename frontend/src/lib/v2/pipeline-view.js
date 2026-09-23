/** Visual accents only; stage values and transitions stay owned by each module. */
export function pipelineTone(label) {
  const stage = String(label)
    .toLowerCase()
    .replace(/[\s_-]/g, '');
  if (['qualified', 'closewon', 'closedwon', 'resolved', 'closed'].includes(stage))
    return 'success';
  if (['lost', 'closelost', 'closedlost', 'notqualified', 'rejected', 'duplicate'].includes(stage))
    return 'muted';
  if (['followup', 'waiting', 'pending', 'standby', 'stanby', 'negotiation'].includes(stage))
    return 'waiting';
  return 'open';
}
