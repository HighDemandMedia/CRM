import { apiRequest } from '$lib/api-helpers.js';

export async function load({ cookies, url }) {
  const params = new URLSearchParams(url.searchParams);
  params.delete('download');
  try {
    return {
      report: await apiRequest(`/reports/crm/?${params}`, {}, { cookies }),
      reportError: ''
    };
  } catch (cause) {
    if ([400, 403].includes(cause.status))
      return { report: null, reportError: String(cause.message) };
    throw cause;
  }
}
