<script>
  import { page } from '$app/state';
  import { provideI18n } from '$lib/i18n/context.js';
  let { children } = $props();
  provideI18n(() => page.data.uiLocale ?? 'en');
  $effect(() => {
    document.documentElement.lang = page.data.uiLocale === 'es' ? 'es' : 'en';
  });
</script>

{@render children()}
