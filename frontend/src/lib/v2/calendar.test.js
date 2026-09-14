import {expect,it} from 'vitest';
import {calendarDays,dateKey,shiftDate} from './calendar.js';
it('shows six full weeks spanning month boundaries',()=>{
 const days=calendarDays(new Date(2026,8,13),'month');
 expect(days).toHaveLength(42); expect(days[0].getDay()).toBe(0);
 expect(dateKey(days[0])).toBe('2026-08-30');expect(dateKey(days[41])).toBe('2026-10-10');
});
it('moves months safely from the 31st',()=>expect(dateKey(shiftDate(new Date(2026,0,31),'month',1))).toBe('2026-02-01'));
it('week and day have appropriate lengths',()=>{expect(calendarDays(new Date(2026,8,13),'week')).toHaveLength(7);expect(calendarDays(new Date(),'day')).toHaveLength(1);});

it('positions minute-precise appointments and separates overlapping cards', async () => {
 const {timedCards}=await import('./calendar.js');
 const events=[15,30,90].map((minute,i)=>({id:String(i),start:new Date(2026,8,13,9,minute).toISOString()}));
 const cards=timedCards(events);
 expect(cards.map(c=>c.minute)).toEqual([555,570,630]);
 expect(cards.slice(0,2).map(c=>c.lane)).toEqual([0,1]);
 expect(cards.slice(0,2).map(c=>c.lanes)).toEqual([2,2]);
 expect(cards[2].lanes).toBe(1);
});
it('uses the appointment end time to detect overlaps', async()=>{
 const {timedCards}=await import('./calendar.js');
 const cards=timedCards([{id:'long',start:'2026-09-13T09:00:00',end:'2026-09-13T11:00:00'},{id:'short',start:'2026-09-13T10:15:00',end:'2026-09-13T10:45:00'}]);
 expect(cards[0].duration).toBe(120);expect(cards[1].duration).toBe(30);expect(cards.map(c=>c.lanes)).toEqual([2,2]);
});
