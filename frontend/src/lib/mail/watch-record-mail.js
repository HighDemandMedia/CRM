import { watchResourceStatus } from '$lib/utils/watch-resource-status.js';

/** @param {Parameters<typeof watchResourceStatus>[0]} options */
export function watchRecordMail(options) {
  return watchResourceStatus({ ...options, endpoint: `${options.endpoint}?view=status` });
}
