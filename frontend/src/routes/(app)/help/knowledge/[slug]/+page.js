import { error } from '@sveltejs/kit';
import { articles } from '$lib/help/articles.js';
export function load({ params }) {
  const article = articles.find((article) => article.slug === params.slug);
  if (!article) error(404, 'This guide does not exist.');
  return {
    article,
    related: articles
      .filter((item) => item.category === article.category && item.slug !== article.slug)
      .slice(0, 3)
  };
}
