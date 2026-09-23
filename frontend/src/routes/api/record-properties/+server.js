import {json} from '@sveltejs/kit';
import {apiRequest} from '$lib/api-helpers.js';
import {readableError} from '$lib/server/v2/form-errors.js';
const endpoints = {Contact:'contacts', Account:'accounts', Opportunity:'opportunities', Task:'tasks', Case:'cases'};
export async function POST({cookies,request}) {
  const {target,id,values} = await request.json();
  if (!Object.hasOwn(endpoints,target) || !/^[0-9a-f-]{36}$/i.test(id) || !values || typeof values !== 'object' || Array.isArray(values)) return json({error:'Invalid properties.'},{status:400});
  try {
    await apiRequest(`/${endpoints[target]}/${id}/`, {method:'PATCH',body:{custom_fields:values}}, {cookies});
    return json({saved:true});
  } catch (err) {return json({error:readableError(err,'Could not save the property.')},{status:err.status || 400});}
}
