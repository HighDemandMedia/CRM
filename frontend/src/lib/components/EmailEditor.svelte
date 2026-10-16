<script>
  import { onMount } from 'svelte';
  import { useI18n } from '$lib/i18n/context.js';
  import { mailEditorDocument } from '$lib/v2/mail-composition.js';
  import Bold from '@lucide/svelte/icons/bold';
  import Italic from '@lucide/svelte/icons/italic';
  import Underline from '@lucide/svelte/icons/underline';
  import List from '@lucide/svelte/icons/list';
  import ListOrdered from '@lucide/svelte/icons/list-ordered';
  import Link from '@lucide/svelte/icons/link';
  const { ui } = useI18n();
  /** @type {{initialText:string,disabled?:boolean,focusMessage?:boolean,onchange:(text:string,html:string,edited?:boolean)=>void}} */
  let { initialText, disabled = false, focusMessage = false, onchange } = $props();
  let element = $state();
  let editorState = $state(/** @type {{editor:import('@tiptap/core').Editor}|null} */ (null));
  let failed = $state(false);
  let fallback = $state('');
  let showLink = $state(false);
  let linkUrl = $state('');
  let linkError = $state('');
  const formats = [
    { name: 'Bold', icon: Bold, mark: 'bold', command: 'toggleBold' },
    { name: 'Italic', icon: Italic, mark: 'italic', command: 'toggleItalic' },
    { name: 'Underline', icon: Underline, mark: 'underline', command: 'toggleUnderline' },
    { name: 'Bulleted list', icon: List, mark: 'bulletList', command: 'toggleBulletList' },
    { name: 'Numbered list', icon: ListOrdered, mark: 'orderedList', command: 'toggleOrderedList' }
  ];
  onMount(() => {
    fallback = initialText;
    let disposed = false;
    let editor;
    void Promise.all([import('@tiptap/core'), import('@tiptap/starter-kit')])
      .then(([{ Editor }, { StarterKit }]) => {
        if (disposed) return;
        editor = new Editor({
          element,
          extensions: [
            StarterKit.configure({
              heading: false,
              code: false,
              codeBlock: false,
              horizontalRule: false,
              link: { openOnClick: false, autolink: false, defaultProtocol: 'https' }
            })
          ],
          content: mailEditorDocument(initialText),
          editable: !disabled,
          autofocus: focusMessage ? 'end' : false,
          editorProps: {
            attributes: {
              role: 'textbox',
              'aria-label': ui('Message'),
              'aria-multiline': 'true',
              'data-placeholder': ui('Write your message…')
            }
          },
          onTransaction: () => {
            editorState = { editor };
          },
          onUpdate: () => onchange(editor.getText(), editor.getHTML(), true)
        });
        editorState = { editor };
        onchange(editor.getText(), editor.getHTML());
      })
      .catch(() => {
        if (!disposed) failed = true;
      });
    return () => {
      disposed = true;
      editor?.destroy();
    };
  });
  $effect(() => {
    if (editorState && editorState.editor.isEditable === disabled)
      editorState.editor.setEditable(!disabled, false);
  });
  function applyLink() {
    try {
      const url = new URL(linkUrl);
      if (!['https:', 'http:', 'mailto:'].includes(url.protocol)) throw new Error();
      editorState?.editor.chain().focus().extendMarkRange('link').setLink({ href: url.href }).run();
      showLink = false;
      linkError = '';
    } catch {
      linkError = 'Enter a valid web or email link.';
    }
  }
</script>

<div class="mail-editor">
  {#if failed}
    <textarea
      class="v2-input"
      aria-label={ui('Message')}
      rows="6"
      bind:value={fallback}
      {disabled}
      maxlength="100000"
      oninput={() => onchange(fallback, '', true)}></textarea>
    <p class="v2-sub" role="status">
      {ui('Formatting unavailable. You can still send plain text.')}
    </p>
  {:else}
    {#if !editorState}<p class="v2-sub" role="status">{ui('Loading editor…')}</p>{/if}
    <div bind:this={element} class="editor-surface"></div>
    <div class="format-toolbar" role="group" aria-label={ui('Text formatting')}>
      {#each formats as format (format.mark)}
        <button
          type="button"
          title={ui(format.name)}
          aria-label={ui(format.name)}
          aria-pressed={editorState?.editor.isActive(format.mark) || false}
          disabled={disabled || !editorState}
          onmousedown={(event) => event.preventDefault()}
          onclick={() => editorState?.editor.chain().focus()[format.command]().run()}
        >
          <format.icon size={16} />
        </button>
      {/each}
      <button
        type="button"
        title={ui('Insert link')}
        aria-label={ui('Insert link')}
        aria-expanded={showLink}
        disabled={disabled || !editorState}
        onclick={() => {
          linkUrl = editorState?.editor.getAttributes('link').href || '';
          showLink = !showLink;
        }}><Link size={16} /></button
      >
    </div>
    {#if showLink}
      <div class="link-fields">
        <input
          class="v2-input"
          aria-label={ui('Link URL')}
          bind:value={linkUrl}
          placeholder="https://"
          {disabled}
          onkeydown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              applyLink();
            }
          }}
        />
        <button class="v2-btn v2-btn-sm" type="button" {disabled} onclick={applyLink}
          >{ui('Apply')}</button
        >
        <button
          class="v2-btn v2-btn-sm"
          type="button"
          {disabled}
          onclick={() => {
            editorState?.editor.chain().focus().unsetLink().run();
            showLink = false;
          }}>{ui('Remove')}</button
        >
      </div>
      {#if linkError}<p class="v2-error" role="alert">{ui(linkError)}</p>{/if}
    {/if}
  {/if}
</div>

<style>
  .mail-editor {
    min-width: 0;
  }
  .editor-surface :global(.tiptap) {
    min-height: 10rem;
    padding: 0.75rem 1rem;
    outline: none;
    font-size: var(--crm-text-sm);
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .editor-surface :global(.tiptap:focus-visible) {
    box-shadow: inset 0 0 0 2px var(--crm-link);
  }
  .editor-surface :global(p) {
    margin: 0 0 0.5em;
  }
  .editor-surface :global(.tiptap:has(p:only-child > br:only-child)::before) {
    content: attr(data-placeholder);
    color: var(--v2-slate);
    float: left;
    height: 0;
    pointer-events: none;
  }
  .editor-surface :global(ul) {
    list-style: disc;
    padding-left: 1.5em;
  }
  .editor-surface :global(ol) {
    list-style: decimal;
    padding-left: 1.5em;
  }
  .editor-surface :global(a) {
    color: var(--crm-link);
    text-decoration: underline;
  }
  .editor-surface :global(blockquote) {
    border-left: 2px solid var(--v2-line);
    padding-left: 0.75rem;
  }
  .format-toolbar {
    display: flex;
    gap: 0.125rem;
    padding: 0.25rem 0.75rem;
    border-top: 1px solid var(--v2-line-soft);
  }
  .format-toolbar button {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 0.25rem;
  }
  .format-toolbar button:hover,
  .format-toolbar button[aria-pressed='true'] {
    background: var(--crm-canvas);
    color: var(--crm-link);
  }
  .format-toolbar button:focus-visible {
    outline: 2px solid var(--crm-link);
    outline-offset: 1px;
  }
  .format-toolbar button:disabled {
    opacity: 0.45;
  }
  .link-fields {
    display: flex;
    gap: 0.25rem;
    padding: 0.5rem 0.75rem;
  }
  .link-fields input {
    min-width: 0;
    flex: 1;
  }
</style>
