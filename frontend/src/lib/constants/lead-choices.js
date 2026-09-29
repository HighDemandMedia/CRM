import { countryOptions } from './countries.js';

/**
 * Lead field choices matching Django backend
 * @module lib/constants/lead-choices
 */

/** @type {{ value: string, label: string }[]} */
export const INDUSTRIES = [
  { value: '', label: 'Select Industry' },
  { value: 'ADVERTISING', label: 'Advertising' },
  { value: 'AGRICULTURE', label: 'Agriculture' },
  { value: 'APPAREL & ACCESSORIES', label: 'Apparel & Accessories' },
  { value: 'AUTOMOTIVE', label: 'Automotive' },
  { value: 'BANKING', label: 'Banking' },
  { value: 'BIOTECHNOLOGY', label: 'Biotechnology' },
  { value: 'BUILDING MATERIALS & EQUIPMENT', label: 'Building Materials & Equipment' },
  { value: 'CHEMICAL', label: 'Chemical' },
  { value: 'COMPUTER', label: 'Computer' },
  { value: 'EDUCATION', label: 'Education' },
  { value: 'ELECTRONICS', label: 'Electronics' },
  { value: 'ENERGY', label: 'Energy' },
  { value: 'ENTERTAINMENT & LEISURE', label: 'Entertainment & Leisure' },
  { value: 'FINANCE', label: 'Finance' },
  { value: 'FOOD & BEVERAGE', label: 'Food & Beverage' },
  { value: 'GROCERY', label: 'Grocery' },
  { value: 'HEALTHCARE', label: 'Healthcare' },
  { value: 'INSURANCE', label: 'Insurance' },
  { value: 'LEGAL', label: 'Legal' },
  { value: 'MANUFACTURING', label: 'Manufacturing' },
  { value: 'PUBLISHING', label: 'Publishing' },
  { value: 'REAL ESTATE', label: 'Real Estate' },
  { value: 'SERVICE', label: 'Service' },
  { value: 'SOFTWARE', label: 'Software' },
  { value: 'SPORTS', label: 'Sports' },
  { value: 'TECHNOLOGY', label: 'Technology' },
  { value: 'TELECOMMUNICATIONS', label: 'Telecommunications' },
  { value: 'TELEVISION', label: 'Television' },
  { value: 'TRANSPORTATION', label: 'Transportation' },
  { value: 'VENTURE CAPITAL', label: 'Venture Capital' }
];

/** @type {{ value: string, label: string }[]} */
export const COUNTRIES = [
  { value: '', label: 'Select Country' },
  ...countryOptions()
];
