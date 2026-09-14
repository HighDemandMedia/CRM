import { languages } from './languages.js';
export const advancedContactFilters = [
  {
    key: 'language',
    label: 'Language',
    options: languages.map((language) => [language, language])
  },
  { key: 'name', label: 'Name' },
  { key: 'phone', label: 'Phone' },
  { key: 'email', label: 'Email' },
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
      ['WALK_IN', 'Walk In']
    ]
  },
  {
    key: 'preferred_communication_channel',
    label: 'Communication channel',
    options: [
      ['SMS', 'SMS'],
      ['CALL', 'Call'],
      ['EMAIL', 'Email']
    ]
  },
  { key: 'address_line', label: 'Address' },
  { key: 'city', label: 'City' },
  { key: 'state', label: 'State' },
  { key: 'postcode', label: 'Zip Code' },
  { key: 'country', label: 'Country' },
  { key: 'organization', label: 'Business' },
  { key: 'title', label: 'Job title' },
  { key: 'department', label: 'Department' },
  { key: 'description', label: 'Notes' },
  { key: 'created_at', label: 'Created date', type: 'range' },
  { key: 'last_activity_at', label: 'Last activity date', type: 'range' },
  { key: 'appointment_at', label: 'Appointment date', type: 'range' },
  {
    key: 'do_not_call',
    label: 'Marketing Opt-Out',
    options: [
      ['true', 'Yes'],
      ['false', 'No']
    ]
  }
];
