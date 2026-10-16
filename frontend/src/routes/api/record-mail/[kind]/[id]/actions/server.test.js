import { beforeEach, expect, it, vi } from 'vitest';
const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { POST } = await import('./+server.js');
const id = '11111111-1111-4111-8111-111111111111';
function event(body, kind = 'contact') {
  return /** @type {any} */ ({
    cookies: {},
    params: { kind, id },
    request: new Request('http://localhost/api/record-mail/contact/' + id + '/actions', {
      method: 'POST',
      body: JSON.stringify(body)
    })
  });
}
beforeEach(() => {
  apiRequest.mockReset();
});
it('forwards the explicit message only to its record action endpoint', async () => {
  const body = { action: 'comment', message: id, body: 'Team note' };
  apiRequest.mockResolvedValue({ commented: true, id });
  const response = await POST(event(body));
  expect(response.status).toBe(200);
  expect(response.headers.get('cache-control')).toBe('private, no-store');
  expect(apiRequest).toHaveBeenCalledWith(
    `/integrations/google/records/contact/${id}/mail/actions/`,
    { method: 'POST', body },
    { cookies: {} }
  );
});
it('rejects unknown record kinds before forwarding', async () => {
  expect((await POST(event({}, 'arbitrary'))).status).toBe(400);
  expect(apiRequest).not.toHaveBeenCalled();
});
it('retains safe duplicate-send conflict messages', async () => {
  apiRequest.mockRejectedValue(
    Object.assign(new Error('Check Gmail Sent before trying again.'), { status: 409 })
  );
  const response = await POST(event({}));
  expect(response.status).toBe(409);
  expect((await response.json()).error).toContain('Check Gmail Sent');
});
it('does not expose upstream internals or automatically retry uncertain sends', async () => {
  apiRequest.mockRejectedValue(new Error('private upstream failure'));
  const response = await POST(event({}));
  expect(response.status).toBe(503);
  expect((await response.json()).error).toBe(
    'Sending could not be confirmed. Check Gmail Sent before trying again.'
  );
  expect(apiRequest).toHaveBeenCalledTimes(1);
});

it('forwards multipart files and message payload without inventing content-type boundaries', async () => {
  const form = new FormData();
  form.set('payload', JSON.stringify({ action: 'send', body_html: '<p>Hello</p>' }));
  form.append('attachments', new File(['contents'], 'proposal.txt'));
  const request = new Request('http://localhost/api/send', { method: 'POST', body: form });
  apiRequest.mockResolvedValue({ sent: true });
  const response = await POST({ ...event({}), request });
  expect(response.status).toBe(200);
  const forwarded = apiRequest.mock.calls[0][1].body;
  expect(forwarded).toBeInstanceOf(FormData);
  expect(await forwarded.get('attachments').text()).toBe('contents');
  expect(JSON.parse(forwarded.get('payload')).body_html).toBe('<p>Hello</p>');
});
it('rejects non-file attachment fields before contacting the API', async () => {
  const form = new FormData();
  form.set('attachments', 'not a file');
  const request = new Request('http://localhost/api/send', { method: 'POST', body: form });
  expect((await POST({ ...event({}), request })).status).toBe(400);
  expect(apiRequest).not.toHaveBeenCalled();
});
