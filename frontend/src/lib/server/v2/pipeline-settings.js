import { apiRequest } from '$lib/api-helpers.js';
export function getPipelineSettings({ cookies }) {
  return apiRequest('/pipeline-settings/', {}, { cookies });
}
export function savePipelineSettings({ cookies }, body) {
  return apiRequest('/pipeline-settings/', { method: 'PUT', body }, { cookies });
}
