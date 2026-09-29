/**
 * Prefer the batched API. Keep the previous reads only during a rolling deploy
 * where a new web instance can briefly reach the previous API version.
 * @param {any} response
 * @param {any[]} stages
 * @param {URLSearchParams} query
 * @param {(params: URLSearchParams) => Promise<any>} list
 */
export async function pipelineColumns(response, stages, query, list) {
  const columns =
    response.board ??
    (await Promise.all(
      stages
        .filter((stage) => !query.get('stage') || query.get('stage') === stage.value)
        .map(async (stage) => {
          const params = new URLSearchParams(query);
          params.delete('board');
          params.set('stage', stage.value);
          params.set('include_choices', 'false');
          params.set('include_deal_values', 'true');
          const offset = Math.min(
            10000000,
            Math.max(0, parseInt(query.get(`${stage.value}_offset`) || '0') || 0)
          );
          params.set('offset', String(offset));
          const data = await list(params);
          return {
            key: stage.value,
            results: data.results,
            count: data.totals.count,
            money_totals: data.totals.money_totals,
            offset
          };
        })
    ));
  return columns.map((column) => ({
    ...stages.find((stage) => stage.value === column.key),
    value: column.key,
    contacts: column.results,
    count: column.count,
    moneyTotals: column.money_totals,
    offset: column.offset
  }));
}
