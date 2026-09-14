export const advancedDealFilters = [
  { key: 'account', label: 'Company' },
  { key: 'contacts', label: 'Contacts' },
  {
    key: 'lead_source',
    label: 'Source',
    options: [
      ['META', 'Meta'],
      ['GOOGLE', 'Google'],
      ['TIKTOK', 'TikTok'],
      ['ORGANIC', 'Organic'],
      ['CALL', 'Call'],
      ['CUSTOMER_REFERAL', 'Customer Referal'],
      ['EMPLOYER_REFERAL', 'Employer Referal'],
      ['WALK_IN', 'Walk In']
    ]
  },
  { key: 'name', label: 'Name' },
  { key: 'amount', label: 'Amount', type: 'number-range' },
  { key: 'closed_on', label: 'Close Date', type: 'range' },
  { key: 'address_line', label: 'Address' },
  { key: 'city', label: 'City' },
  { key: 'state', label: 'State' },
  { key: 'postcode', label: 'Zip Code' },
  { key: 'country', label: 'Country' },
  { key: 'created_at', label: 'Created date', type: 'range' },
  { key: 'updated_at', label: 'Updated date', type: 'range' }
];
