<script>
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  import '../app.css';
  import { page } from '$app/stores';
  import ErrorPage from '$lib/components/ErrorPage.svelte';
</script>

<svelte:head>
  <title
    >{$page.status}
    {$page.status === 404 ? ui('Not Found') : ui('Error')} | High Demand Media CRM</title
  >
</svelte:head>

<main class="bg-background min-h-screen">
  <ErrorPage status={$page.status} />
</main>
