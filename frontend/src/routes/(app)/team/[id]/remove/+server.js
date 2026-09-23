import {json} from '@sveltejs/kit';
import {apiRequest} from '$lib/api-helpers.js';
import {readableError} from '$lib/server/v2/form-errors.js';
async function handle({cookies,params,request}, method) {
  try {
    const body=method === 'POST' ? await request.json() : undefined;
    return json(await apiRequest(`/members/${params.id}/remove/`,{method,body},{cookies}),{headers:{'Cache-Control':'no-store'}});
  } catch(err) {
    return json({message:readableError(err,'Could not remove this user.')},{status:err.status || 400});
  }
}
export const GET=event=>handle(event,'GET');
export const POST=event=>handle(event,'POST');
