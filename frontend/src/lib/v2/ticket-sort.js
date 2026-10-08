// Only columns with an API ordering contract can sort the whole result set.
export const TICKET_SORT_FIELDS = {
  id: 'id',
  ticket_code: 'ticket_number',
  name: 'name',
  priority: 'priority',
  status: 'status',
  category: 'category',
  source: 'source',
  due_at: 'due_at',
  created_at: 'created_at',
  last_activity: 'last_activity_at',
  last_activity_at: 'last_activity_at',
  description: 'description',
  waiting_reason: 'waiting_reason',
  resolution_note: 'resolution_note'
};
