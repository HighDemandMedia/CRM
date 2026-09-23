import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
vi.mock('$lib/api-helpers.js', () => ({apiRequest:vi.fn()}));
const event = (fields) => ({cookies:{get:()=>undefined}, request:{formData:async () => {const data=new FormData(); for (const [key,value] of Object.entries(fields)) data.set(key,value); return data;}}});
describe('organization details', () => {
  beforeEach(() => { vi.mocked(apiRequest).mockReset(); });
  it('only submits organization property fields and keeps omitted settings unchanged', async () => {
    vi.mocked(apiRequest).mockResolvedValue({});
    const result=await actions.save(/** @type {any} */ (event({name:' New name ', api_key:'not-allowed', csat_enabled:'false'})));
    expect(result).toEqual({saved:true});
    expect(apiRequest).toHaveBeenCalledWith('/org/settings/', {method:'PATCH',body:{name:'New name'}}, expect.anything());
  });
  it('reports backend permission refusal instead of claiming success', async () => {
    vi.mocked(apiRequest).mockRejectedValue({status:403});
    const result=await actions.save(/** @type {any} */ (event({name:'New name'})));
    expect(/** @type {any} */ (result).status).toBe(403);
  });
  it('rejects malformed organization IDs before switching', async () => {
    const result=await actions.switchOrg(/** @type {any} */ (event({org_id:'invalid'})));
    expect(/** @type {any} */ (result).status).toBe(400);
    expect(apiRequest).not.toHaveBeenCalled();
  });
});
