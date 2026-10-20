<script>
  import imgGoogle from '$lib/assets/images/google.svg';
  import { useI18n } from '$lib/i18n/context.js';
  const { ui } = useI18n();
  let { busy = false } = $props();
</script>

<button type="submit" class="v2-btn v2-btn-block google-signin" disabled={busy}>
  <img src={imgGoogle} alt="" width="20" height="20" />
  {busy ? ui('Connecting…') : ui('Continue with Google')}
</button>

<style>
  .google-signin {
    background: #fff;
    border: 1px solid #747775;
    color: #1f1f1f;
    gap: 0.625rem;
  }
  .google-signin img {
    flex: 0 0 1.25rem;
  }
  .google-signin:hover:not(:disabled) {
    background: #f2f2f2;
  }
</style>
