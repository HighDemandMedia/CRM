import {describe,it,expect} from 'vitest';
import {orderedEntries,customDisplay} from './property-order.js';
describe('record property order',()=>{
  const config={system:[{key:'first_name',label:'Name'},{key:'phone',label:'Phone'}],order:['custom_fields.custom_plan','phone','first_name'],custom:[{key:'custom_plan',label:'Plan',field_type:'text'}]};
  it('interleaves new custom properties with system fields',()=>{
    const rows=orderedEntries([['Name','Ana'],['Phone','555']],'Contact',config,{custom_plan:'Gold'});
    expect(rows.map(r=>r.label)).toEqual(['Plan','Phone','Name']);
    expect(rows[0].value).toBe('Gold');
  });
  it('shows new unfilled properties and preserves zero and false',()=>{
    expect(orderedEntries([],'Contact',config,{})[0].label).toBe('Plan');
    expect(customDisplay(0,{field_type:'number'})).toBe('0');
    expect(customDisplay(false,{field_type:'checkbox'})).toBe('No');
    expect(customDisplay(undefined,{field_type:'text'})).toBe('—');
  });
});
