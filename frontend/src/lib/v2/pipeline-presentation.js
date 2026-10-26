import { configuredStages } from './pipeline-config.js';

/** Combine authorized board records with inherited presentation configuration.
 * No filtering, totals or pagination is derived from the visible list page.
 * @param {any} data
 * @param {any} config
 * @param {string} target
 */
export function pipelinePresentation(data, config, target) {
  const stages = configuredStages(config, target, data.stages ?? []);
  return {
    ...data,
    stages,
    board: (data.board ?? []).map((column) => ({
      ...column,
      // Keep current labels/rules when a layout refresh changes configuration.
      ...stages.find((stage) => stage.value === column.value)
    }))
  };
}
