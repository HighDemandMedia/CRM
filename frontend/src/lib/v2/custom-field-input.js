export function fieldInputType(type) {
  if (['number', 'integer', 'percentage'].includes(type)) return 'number';
  if (type === 'phone') return 'tel';
  if (['email', 'date', 'time'].includes(type)) return type;
  return 'text';
}
export function fieldInputStep(type) {
  return type === 'integer' ? '1' : type === 'money' ? '0.01' : type === 'time' ? '1' : 'any';
}
