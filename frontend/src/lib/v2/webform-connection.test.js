import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { connectorSnippet, previewUrl } from './webform-connection.js';

// Execute the actual distributed connector, with the host page's existing form.
const template = readFileSync(
  new URL('../../../../backend/webforms/templates/webforms/connect.js', import.meta.url),
  'utf8'
);
/** @param {{mode?: string | null, status?: number, fields?: any, captcha?: string, late?: boolean}} options */
function host({ mode = 'copy', status = 200, fields, captcha = '', late = false } = {}) {
  const controls = fields || [{ name: 'visitor-email', type: 'email', value: 'test@example.test' }];
  controls.namedItem = (name) => controls.find((c) => c.name === name);
  const button = { disabled: false };
  const children = [],
    events = [];
  let handler, observer;
  let present = !late;
  const form = {
    tagName: 'FORM',
    dataset: {},
    elements: controls,
    appendChild: (node) => {
      children.push(node);
    },
    checkValidity: () => true,
    querySelectorAll: () => [button],
    addEventListener: vi.fn((_, fn) => {
      handler = fn;
    }),
    dispatchEvent: (event) => {
      events.push(event.type);
    }
  };
  const assign = vi.fn(),
    error = vi.fn();
  const fetch = vi.fn(async (_url, _options) => ({
    ok: status === 200,
    json: async () =>
      status === 200
        ? { status: 'ok', mode: 'redirect', redirect_url: 'https://crm.test/thanks' }
        : { detail: 'Try again' }
  }));
  const config = {
    formId: 'test',
    submitUrl: 'https://api.test/submit/',
    honeypot: 'trap',
    captchaSiteKey: captcha,
    fields: [{ name: 'email', externalName: 'visitor-email', label: 'Email', required: true }]
  };
  const document = {
    readyState: 'complete',
    body: {},
    currentScript: { getAttribute: (key) => (key === 'data-mode' ? mode : '#existing') },
    querySelectorAll: () => (present ? [form] : []),
    createElement: () => ({ value: '', style: {}, setAttribute() {} })
  };
  const context = {
    document,
    window: { location: { assign } },
    fetch,
    console: { error },
    crypto: { randomUUID: vi.fn(() => '00000000-0000-4000-8000-000000000001') },
    AbortController,
    setTimeout,
    clearTimeout,
    MutationObserver: class {
      constructor(callback) {
        observer = callback;
      }
      observe() {}
    },
    CustomEvent: class {
      constructor(type) {
        this.type = type;
      }
    }
  };
  vm.runInNewContext(template.replace('{{ config_json|safe }}', JSON.stringify(config)), context);
  return {
    fetch,
    form,
    button,
    children,
    events,
    assign,
    error,
    async mount() {
      present = true;
      observer([{ addedNodes: [form] }]);
      await new Promise((resolve) => setTimeout(resolve, 80));
    },
    async submit() {
      const event = { preventDefault: vi.fn(), stopImmediatePropagation: vi.fn() };
      await handler(event);
      return event;
    }
  };
}

describe('existing HTML form connector', () => {
  it('connects a form inserted later and does not duplicate its handler on DOM updates', async () => {
    const h = host({ late: true });
    expect(h.form.addEventListener).not.toHaveBeenCalled();
    await h.mount();
    await h.mount();
    expect(h.form.addEventListener).toHaveBeenCalledTimes(1);
    await h.submit();
    expect(h.fetch).toHaveBeenCalledTimes(1);
  });
  it('copies mapped data without cancelling the existing email/thank-you handler', async () => {
    const h = host();
    const event = await h.submit();
    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(event.stopImmediatePropagation).not.toHaveBeenCalled();
    expect(h.button.disabled).toBe(false);
    expect(h.assign).not.toHaveBeenCalled();
    expect(h.events).toContain('hdm:submitted');
    expect(h.fetch.mock.calls[0][1].keepalive).toBe(true);
    expect(JSON.parse(h.fetch.mock.calls[0][1].body).email).toBe('test@example.test');
    expect(h.children.some((c) => c.textContent)).toBe(false);
  });
  it('retains managed behavior for already installed snippets', async () => {
    const h = host({ mode: null });
    const event = await h.submit();
    expect(event.preventDefault).toHaveBeenCalled();
    expect(event.stopImmediatePropagation).toHaveBeenCalled();
    expect(h.assign).toHaveBeenCalledWith('https://crm.test/thanks');
  });
  it('leaves the website working when the CRM refuses a copy and reuses retry IDs', async () => {
    const h = host({ status: 503 });
    await h.submit();
    await h.submit();
    expect(h.events).toEqual(['hdm:error', 'hdm:error']);
    expect(h.button.disabled).toBe(false);
    expect(h.fetch.mock.calls[0][1].body).toBe(h.fetch.mock.calls[1][1].body);
  });
  it('does not copy an unchanged successful submission twice', async () => {
    const h = host();
    await h.submit();
    await h.submit();
    expect(h.fetch).toHaveBeenCalledTimes(1);
  });
  it('does not collect a mapped password or submit without a required mapping', async () => {
    const h = host({ fields: [{ name: 'visitor-email', type: 'password', value: 'private' }] });
    const event = await h.submit();
    expect(h.fetch).not.toHaveBeenCalled();
    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(h.error).toHaveBeenCalled();
  });
  it('requires configured verification and does not install another captcha in copy mode', async () => {
    const h = host({ captcha: 'site-key' });
    await h.submit();
    expect(h.fetch).not.toHaveBeenCalled();
    expect(h.error).toHaveBeenCalled();
  });
});

it('generates copy snippets for one form or a specified safe ID', () => {
  expect(connectorSnippet('https://api.test/submit/')).toContain(
    'data-form="form" data-mode="copy"'
  );
  expect(connectorSnippet('https://api.test/submit/', 'leadForm')).toContain(
    'data-form="#leadForm"'
  );
  expect(connectorSnippet('https://api.test/submit/', '"><script>')).toBe('');
  expect(previewUrl('https://api.test/submit/')).toBe('https://api.test/embed/');
});
