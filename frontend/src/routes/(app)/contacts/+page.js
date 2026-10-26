import { pipelinePresentation } from '$lib/v2/pipeline-presentation.js';

/** @type {import('./$types').PageLoad} */
export async function load({ data, parent }) {
  // Universal parent() reuses layout data; server parent() would rerun its API reads.
  const shell = await parent();
  return pipelinePresentation(data, shell.pipelineConfig, 'Contact');
}
