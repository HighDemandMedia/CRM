import { beforeEach, expect, it, vi } from 'vitest';

vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('./contacts.js', () => ({ listContacts: vi.fn(), FILTER_FIELDS: [] }));
vi.mock('./accounts.js', () => ({ listAccounts: vi.fn(), FILTER_FIELDS: [] }));
vi.mock('./deals.js', () => ({ listDeals: vi.fn(), FILTER_FIELDS: [] }));
vi.mock('./tasks.js', () => ({ listTasks: vi.fn(), FILTER_FIELDS: [] }));
vi.mock('./tickets.js', () => ({
  listTickets: vi.fn(),
  FILTER_FIELDS: [],
  OPEN_STATUSES: ['New']
}));

import { apiRequest } from '$lib/api-helpers.js';
import { listContacts } from './contacts.js';
import { listAccounts } from './accounts.js';
import { listDeals } from './deals.js';
import { listTasks } from './tasks.js';
import { listTickets } from './tickets.js';
import { exportContacts } from './contact-csv.js';
import { exportCompanies } from './company-csv.js';
import { exportDeals } from './deal-csv.js';
import { exportQueue } from './queue-csv.js';
import { postExport } from './export-scope.js';

/** @type {Array<[string, string, string, import("vitest").Mock, (event: any) => Promise<any>]>} */
const objects = [
  ['contacts', 'Contact', 'CON', vi.mocked(listContacts), exportContacts],
  ['companies', 'Account', 'COM', vi.mocked(listAccounts), exportCompanies],
  ['deals', 'Opportunity', 'DEA', vi.mocked(listDeals), exportDeals],
  ['tasks', 'Task', 'TSK', vi.mocked(listTasks), (event) => exportQueue(event, 'Task')],
  ['tickets', 'Case', 'TKT', vi.mocked(listTickets), (event) => exportQueue(event, 'Case')]
];

beforeEach(() => vi.resetAllMocks());

it.each(objects)(
  '%s exports complete compact IDs and associations in requested page order',
  async (module, target, prefix, list, exportCSV) => {
    const associations =
      target === 'Contact'
        ? ['account']
        : target === 'Account'
          ? ['contacts']
          : ['account', 'contacts'];
    const keys = ['id', ...associations];
    vi.mocked(apiRequest).mockResolvedValue({
      property_layout: {
        [target]: { system: keys.map((key) => ({ key, label: key })) }
      }
    });
    const row = (id) => ({
      id,
      account: { id: 'COM-0041', name: 'Linked Company' },
      contacts: [
        { id: 'CON-0042', name: 'Linked Contact' },
        { id: 'CON-10001', name: 'Second Contact' }
      ]
    });
    vi.mocked(list).mockResolvedValue({
      results: [row(`${prefix}-0007`), row(`${prefix}-10000`)],
      totals: { count: 2 }
    });
    const form = new FormData();
    // The unavailable ID must not bypass the API's authorized result set.
    for (const id of [`${prefix}-10000`, `${prefix}-9999`, `${prefix}-0007`])
      form.append('ids', id);
    const csv = await postExport(
      {
        cookies: {},
        url: new URL(`http://localhost/${module}/export?scope=page&columns=${keys.join(',')}`),
        request: new Request('http://localhost/export', { method: 'POST', body: form })
      },
      exportCSV
    );
    const lines = csv.trim().split('\r\n');
    expect(lines).toHaveLength(3);
    expect(lines[1]).toContain(`"${prefix}-10000"`);
    expect(lines[2]).toContain(`"${prefix}-0007"`);
    expect(csv).not.toContain(`${prefix}-9999`);
    for (const line of lines.slice(1)) {
      if (associations.includes('account')) expect(line).toContain('Linked Company');
      if (associations.includes('contacts')) {
        expect(line).toContain('Linked Contact');
        expect(line).toContain('Second Contact');
      }
      expect(line).not.toContain('[object Object]');
    }
    expect(vi.mocked(list).mock.calls[0][1].get('permission_action')).toBe('export');
  }
);
