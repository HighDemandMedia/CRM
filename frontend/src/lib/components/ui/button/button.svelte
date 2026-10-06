<script module>
  import { cn } from '$lib/utils.js';
  import { tv } from 'tailwind-variants';

  export const buttonVariants = tv({
    base: [
      'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap',
      'rounded-[var(--r-md)] text-sm font-medium leading-normal tracking-[-0.01em]',
      'outline-none transition-[background-color,color,border-color,box-shadow] duration-150',
      'disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50',
      "[&_svg:not([class*='size-'])]:size-[16px] [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg]:stroke-[1.7]",
      'focus-visible:shadow-[0_0_0_3px_var(--focus-ring)]',
      'aria-invalid:border-[color:var(--red)] aria-invalid:shadow-[0_0_0_3px_var(--red-soft)]'
    ].join(' '),
    variants: {
      variant: {
        default: [
          '[background:var(--crm-action-bg)] text-[color:var(--cta-text)] border border-transparent',
          'hover:[background:var(--crm-action-hover-bg)] active:[background:var(--crm-action-active-bg)]'
        ].join(' '),
        ghost: [
          'bg-[color:var(--bg-elevated)] text-[color:var(--text-muted)]',
          'border border-[color:var(--crm-control-border)]',
          'hover:border-[color:var(--crm-control-border)] hover:text-[color:var(--text)]'
        ].join(' '),
        outline: [
          'bg-[color:var(--bg-elevated)] text-[color:var(--text-muted)]',
          'border border-[color:var(--crm-control-border)]',
          'hover:border-[color:var(--crm-control-border)] hover:text-[color:var(--text)]'
        ].join(' '),
        secondary: [
          'bg-[color:var(--bg-elevated)] text-[color:var(--text-muted)]',
          'border border-[color:var(--crm-control-border)]',
          'hover:border-[color:var(--crm-control-border)] hover:text-[color:var(--text)]'
        ].join(' '),
        destructive: [
          'bg-[color:var(--bg-elevated)] text-[color:var(--red)]',
          'border border-[color:var(--crm-control-border)]',
          'hover:border-[color:var(--red)]'
        ].join(' '),
        link: [
          'bg-transparent text-[color:var(--text)] border border-transparent px-0',
          'underline-offset-4 hover:underline'
        ].join(' ')
      },
      size: {
        default:
          'min-h-[var(--crm-control-height)] px-[var(--crm-control-padding-x)] py-[var(--crm-control-padding-y)]',
        sm: 'min-h-8 gap-2 px-3 py-1 text-xs',
        lg: 'min-h-11 px-5 py-2',
        icon: 'size-10',
        'icon-sm': 'size-8',
        'icon-lg': 'size-11'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default'
    }
  });
</script>

<script>
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  /**
   * @type {{
   *   class?: string,
   *   variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link',
   *   size?: 'default' | 'sm' | 'lg' | 'icon' | 'icon-sm' | 'icon-lg',
   *   ref?: HTMLElement | null,
   *   href?: string,
   *   type?: 'button' | 'submit' | 'reset',
   *   disabled?: boolean,
   *   children?: import('svelte').Snippet,
   *   [key: string]: any
   * }}
   */
  let {
    class: className,
    variant = 'default',
    size = 'default',
    ref = $bindable(null),
    href = undefined,
    type = 'button',
    disabled = false,
    children,
    ...restProps
  } = $props();
</script>

{#if href}
  <a
    bind:this={ref}
    data-slot="button"
    class={cn(buttonVariants({ variant, size }), className)}
    href={disabled ? undefined : resolve(asInternalPath(href))}
    aria-disabled={disabled}
    role={disabled ? 'link' : undefined}
    tabindex={disabled ? -1 : undefined}
    {...restProps}
  >
    {@render children?.()}
  </a>
{:else}
  <button
    bind:this={ref}
    data-slot="button"
    class={cn(buttonVariants({ variant, size }), className)}
    {type}
    {disabled}
    {...restProps}
  >
    {@render children?.()}
  </button>
{/if}
