<script>
  import { emailTextParts } from '$lib/v2/email-presentation.js';
  /** @type {{text:string}} */
  let { text } = $props();
</script>

<div class="email-body">
  {#each emailTextParts(text) as part, index (index)}{#if part.href}<a
        href={part.href}
        target="_blank"
        rel="external noopener noreferrer"
        referrerpolicy="no-referrer">{part.text}</a
      >{:else}{part.text}{/if}{/each}
</div>

<style>
  .email-body {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.45;
    font-size: var(--crm-text-sm);
  }
  a {
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }
</style>
