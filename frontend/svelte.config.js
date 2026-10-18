import adapter from '@sveltejs/adapter-node';

const config = {
  vitePlugin: {
    prebundleSvelteLibraries: false
  },
  kit: {
    adapter: adapter(),

    csp: {
      mode: 'auto',
      directives: {
        'script-src': ['self'],
        'object-src': ['none'],
        'base-uri': ['self'],
        'frame-ancestors': ['none']
      }
    },

    version: {
      pollInterval: 60000
    },

    experimental: {
      tracing: {
        server: true
      },

      instrumentation: {
        server: true
      }
    }
  }
};

export default config;
