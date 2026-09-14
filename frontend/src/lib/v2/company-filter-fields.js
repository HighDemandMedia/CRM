export const advancedCompanyFilters = [
  { key: 'contacts', label: 'Contacts' },
  {
    key: 'source',
    label: 'Source',
    options: [
      ['META', 'Meta'],
      ['GOOGLE', 'Google'],
      ['TIKTOK', 'TikTok'],
      ['ORGANIC', 'Organic'],
      ['CALL', 'Call'],
      ['CUSTOMER_REFERAL', 'Customer Referal'],
      ['EMPLOYER_REFERAL', 'Employer Referal'],
      ['WALK_IN', 'Walk In'],
      ['UNASSIGNED', 'No source']
    ]
  },
  { key: 'name', label: 'Name' },
  { key: 'website', label: 'Domain' },
  { key: 'pages', label: 'Pages' },
  { key: 'currency', label: 'Currency' },
  { key: 'industry', label: 'Industry' },
  { key: 'address_line', label: 'Address' },
  { key: 'city', label: 'City' },
  { key: 'state', label: 'State' },
  { key: 'postcode', label: 'Zip Code' },
  { key: 'country', label: 'Country' },
  { key: 'created_at', label: 'Created date', type: 'range' },
  { key: 'updated_at', label: 'Updated date', type: 'range' },
  { key: 'number_of_employees', label: 'Number of Employees', type: 'number-range' },
  { key: 'annual_revenue', label: 'Annual revenue', type: 'number-range' }
];
