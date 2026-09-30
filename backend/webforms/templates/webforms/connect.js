/* High Demand Media CRM: connect one existing HTML form. */
(function () {
  'use strict';
  var config = {{ config_json|safe }};
  var script = document.currentScript;
  var selector = script && script.getAttribute('data-form');
  function attach() {
    var matches;
    try { matches = selector ? document.querySelectorAll(selector) : []; }
    catch (_) { console.error('CRM: use a valid form selector in data-form.'); return; }
    if (matches.length !== 1 || matches[0].tagName !== 'FORM') {
      console.error('CRM: data-form must match exactly one HTML form.'); return;
    }
    var form = matches[0];
    if (form.dataset.hdmConnected) return;
    form.dataset.hdmConnected = config.formId;
    var status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    form.appendChild(status);
    var trap = document.createElement('input');
    trap.name = config.honeypot; trap.type = 'text'; trap.tabIndex = -1;
    trap.autocomplete = 'off'; trap.setAttribute('aria-hidden', 'true');
    trap.style.cssText = 'position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden';
    form.appendChild(trap);
    var token = '', widgetId = null;
    if (config.captchaSiteKey) {
      var widget = document.createElement('div'); form.appendChild(widget);
      var attempts = 0;
      function renderCaptcha() {
        if (window.turnstile) {
          widgetId = window.turnstile.render(widget, {
            sitekey: config.captchaSiteKey, callback: function (value) { token = value; },
            'expired-callback': function () { token = ''; }
          });
        } else if (++attempts < 100) { setTimeout(renderCaptcha, 100); }
        else { status.textContent = 'Verification could not load. Please reload this page.'; }
      }
      if (!document.querySelector('script[src^="https://challenges.cloudflare.com/turnstile/"]')) {
        var captchaScript = document.createElement('script');
        captchaScript.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
        captchaScript.async = true; document.head.appendChild(captchaScript);
      }
      renderCaptcha();
    }
    var pending = false, submitted = false, requestId = null, previousPayload = null;
    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      // This connector owns this form's submit. Sites with another submit
      // handler should integrate the endpoint in that handler instead.
      event.stopImmediatePropagation();
      if (pending || submitted || !form.reportValidity()) return;
      var payload = Object.create(null), missing = [];
      config.fields.forEach(function (field) {
        var controls = Array.from(form.elements).filter(function (el) {
          return el.name === field.externalName && !el.disabled &&
            !['password', 'file', 'submit', 'button', 'reset', 'hidden'].includes(el.type);
        });
        var values = [];
        controls.forEach(function (el) {
          if (['checkbox', 'radio'].includes(el.type) && !el.checked) return;
          if (el.tagName === 'SELECT' && el.multiple) {
            Array.from(el.selectedOptions).forEach(function (option) { values.push(option.value); });
          } else { values.push(el.value); }
        });
        var multi = controls.some(function (el) { return el.multiple; }) || controls.filter(function (el) { return el.type === 'checkbox'; }).length > 1;
        var value = multi ? values : (values[0] || '');
        if (controls.length === 1 && controls[0].type === 'checkbox' && !multi) value = controls[0].checked;
        if (field.required && (value === '' || value === false || (Array.isArray(value) && !value.length))) missing.push(field.label);
        if (value !== '') payload[field.name] = value;
      });
      if (missing.length) { status.textContent = 'Please complete: ' + missing.join(', ') + '.'; return; }
      if (config.captchaSiteKey && !token) { status.textContent = 'Please complete the verification.'; return; }
      var fingerprint = JSON.stringify(payload);
      if (fingerprint !== previousPayload || !requestId) requestId = crypto.randomUUID();
      previousPayload = fingerprint;
      payload.request_id = requestId;
      payload[config.honeypot] = trap.value;
      payload['cf-turnstile-response'] = token;
      pending = true; status.textContent = 'Sending…';
      var buttons = Array.from(form.querySelectorAll('button, input[type="submit"]'));
      var disabled = buttons.map(function (button) { return button.disabled; });
      buttons.forEach(function (button) { button.disabled = true; });
      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 20000);
      try {
        var response = await fetch(config.submitUrl, {
          method: 'POST', credentials: 'omit', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload), signal: controller.signal
        });
        var result = await response.json();
        if (!response.ok || result.status !== 'ok') {
          var errors = config.fields.filter(function (field) { return result[field.name]; }).map(function (field) { return field.label + ': ' + [].concat(result[field.name]).join(' '); });
          throw new Error(errors.join(' ') || result.detail || 'Your message was not accepted. Please try again.');
        }
        submitted = true;
        status.textContent = result.message || 'Thanks. Your message has been received.';
        form.dispatchEvent(new CustomEvent('hdm:submitted', {bubbles: true}));
        if (result.mode === 'redirect' && /^https?:\/\//i.test(result.redirect_url)) window.location.assign(result.redirect_url);
      } catch (error) {
        status.textContent = error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError
          ? 'We could not confirm delivery. Your entries are still here; please try again.' : error.message;
        if (widgetId !== null && window.turnstile) { window.turnstile.reset(widgetId); token = ''; }
      } finally {
        clearTimeout(timeout); pending = false;
        buttons.forEach(function (button, index) { button.disabled = submitted || disabled[index]; });
      }
    }, true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', attach, {once: true});
  else attach();
})();
