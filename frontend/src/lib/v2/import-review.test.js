import { describe, it, expect, vi } from 'vitest';
import { errorReportCsv, importBatches } from './import-review.js';

describe('CSV error report', () => {
  it('exports only rejected records with editable fields and diagnostics', () => {
    const report = errorReportCsv(
      [
        {
          row: 4,
          values: { name: 'Ana, "QA"', email: 'bad', phone: '+12025550123' },
          errors: [{ field: 'email', message: 'Invalid email' }]
        }
      ],
      [{ key: 'name' }, { key: 'email' }, { key: 'phone' }]
    );
    expect(report).toBe(
      '\ufeff"name","email","phone","__import_row","__import_errors"\r\n"Ana, ""QA""","bad","+12025550123","4","email: Invalid email"\r\n'
    );
  });
  it('neutralizes formulas without dropping multiline source values', () => {
    const report = errorReportCsv(
      [{ row: 2, values: { name: '=HYPERLINK("unsafe")\nNext line' }, errors: [] }],
      [{ key: 'name' }]
    );
    expect(report).toContain('"\'=HYPERLINK(""unsafe"")\nNext line"');
  });
  it('retains all 800 rejected records for download', () => {
    const rows = Array.from({ length: 800 }, (_, i) => ({
      row: i + 202,
      values: { name: `Person ${i}` },
      errors: [{ field: 'email', message: 'Invalid' }]
    }));
    expect(errorReportCsv(rows, [{ key: 'name' }]).split('\r\n')).toHaveLength(802);
  });
});
describe('batched imports', () => {
  it('uses server progress to continue after a lost response', async () => {
    const send = vi
      .fn()
      .mockResolvedValueOnce({ created: 200, total: 250, complete: false })
      .mockResolvedValueOnce({ created: 250, total: 250, complete: true });
    const progress = vi.fn();
    const result = await importBatches(send, 100, progress);
    expect(send.mock.calls).toEqual([[100], [200]]);
    expect(progress.mock.calls).toEqual([[200], [250]]);
    expect(result.created).toBe(250);
  });
  it('stops on failure and retains the last confirmed progress', async () => {
    const send = vi
      .fn()
      .mockResolvedValueOnce({ created: 100, total: 200, complete: false })
      .mockRejectedValueOnce(new Error('offline'));
    const progress = vi.fn();
    await expect(importBatches(send, 0, progress)).rejects.toThrow('offline');
    expect(progress).toHaveBeenCalledExactlyOnceWith(100);
  });
  it('rejects non-advancing progress instead of looping', async () => {
    await expect(
      importBatches(async () => ({ created: 0, total: 200, complete: false }), 0, vi.fn())
    ).rejects.toThrow('progress');
  });
});
