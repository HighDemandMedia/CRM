import { expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({apiRequest:vi.fn()}));
import { apiRequest } from '$lib/api-helpers.js';
import { actions as companies } from '../../../routes/(app)/accounts/[id]/+page.server.js';
import { actions as deals } from '../../../routes/(app)/pipeline/[id]/+page.server.js';
it.each([['accounts',companies,'tag_ids'],['opportunities',deals,'tags']])('saves visible owner and tag fields for %s', async (route,actions,tagKey) => {
  vi.mocked(apiRequest).mockResolvedValue({});
  const form=new FormData();
  form.set('changes',JSON.stringify({assigned_to:'owner-id', tags:['tag-id']}));
  const result=await actions.saveFields(/** @type {any} */({cookies:{},params:{id:'record-id'},request:{formData:async()=>form}}));
  expect(result).toEqual({saved:true});
  expect(apiRequest).toHaveBeenLastCalledWith(`/${route}/record-id/`,{method:'PATCH',body:{assigned_to:['owner-id'],[tagKey]:['tag-id']}},{cookies:{}});
});
