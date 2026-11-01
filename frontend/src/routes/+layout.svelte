<script>
  import { page } from '$app/state';
  import { provideI18n } from '$lib/i18n/context.js';
  import { ModeWatcher } from 'mode-watcher';
  let { children } = $props();
  provideI18n(() => page.data.uiLocale ?? 'en');
  $effect(() => {
    document.documentElement.lang = page.data.uiLocale === 'es' ? 'es' : 'en';
  });
</script>

<ModeWatcher defaultMode="light" track={false} disableHeadScriptInjection />
{@render children()}
