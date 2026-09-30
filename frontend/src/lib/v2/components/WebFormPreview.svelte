<script>
  import { formFonts, buttonTextColor } from '$lib/v2/webform-builder.js';
  let { fields, appearance, button = 'Submit', mobile = false } = $props();
</script>

<div
  class="preview"
  class:mobile
  style:max-width={`${mobile ? 360 : appearance.width}px`}
  style:background={appearance.background_color}
  style:color={appearance.text_color}
  style:font-family={formFonts[appearance.font] ?? formFonts.system}
  style:--radius={`${appearance.radius}px`}
>
  {#if appearance.title}<h2>{appearance.title}</h2>{/if}
  {#if appearance.description}<p>{appearance.description}</p>{/if}
  <div class="fields" style:--columns={appearance.columns}>
    {#each fields as field, i}
      <div class="field">
        <label for={`preview-${i}`}
          >{field.label || 'Field label'}{field.is_required ? ' *' : ''}</label
        >
        {#if field.lead_field === 'description'}
          <textarea id={`preview-${i}`} placeholder={field.placeholder} tabindex="-1" readonly
          ></textarea>
        {:else}
          <input id={`preview-${i}`} placeholder={field.placeholder} tabindex="-1" readonly />
        {/if}
      </div>
    {/each}
  </div>
  <button
    type="button"
    tabindex="-1"
    style:background={appearance.button_color}
    style:color={buttonTextColor(appearance.button_color)}>{button}</button
  >
</div>

<style>
  .preview {
    width: 100%;
    padding: 16px;
    margin: auto;
    box-sizing: border-box;
    container-type: inline-size;
    font-size: 16px;
    line-height: 1.5;
  }
  h2 {
    font-size: 24px;
    line-height: 1.3;
    margin: 0 0 12px;
    color: inherit;
  }
  p {
    white-space: pre-wrap;
    margin: 0 0 24px;
  }
  .fields {
    display: grid;
    grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
    gap: 0 20px;
  }
  .mobile .fields {
    grid-template-columns: minmax(0, 1fr);
  }
  .field {
    margin-bottom: 16px;
    min-width: 0;
  }
  label {
    display: block;
    margin-bottom: 4px;
    font-size: 14px;
    font-weight: 600;
  }
  input,
  textarea {
    width: 100%;
    box-sizing: border-box;
    min-height: 44px;
    padding: 10px 12px;
    font: inherit;
    color: inherit;
    border: 1px solid #d1d5db;
    border-radius: var(--radius);
    background: #fff;
  }
  textarea {
    min-height: 96px;
    resize: vertical;
  }
  button {
    border: 0;
    border-radius: var(--radius);
    font: inherit;
    font-weight: 600;
    padding: 12px 16px;
    min-height: 44px;
    min-width: 180px;
  }
  @container (max-width:508px) {
    .fields {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
