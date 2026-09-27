export const requestTypes = [
  {
    key: 'bug',
    title: 'Report a bug',
    description: 'Something broke or gave the wrong result.',
    introduction: 'Help us understand what failed and how it affects your work.',
    subject: 'Summarize the issue',
    subjectPlaceholder: 'e.g. Moving a contact does not save its stage',
    action: 'Send bug report',
    fields: [
      {
        key: 'actual',
        label: 'What happened?',
        placeholder: 'Describe the incorrect result or paste the error message.',
        required: true
      },
      {
        key: 'expected',
        label: 'What should have happened?',
        placeholder: 'Describe the result you expected.',
        required: true
      },
      {
        key: 'impact',
        label: 'Can you continue working?',
        required: true,
        options: [
          { value: 'blocked', label: 'No — this blocks my work' },
          { value: 'workaround', label: 'Yes — using a workaround' },
          { value: 'minor', label: 'Yes — it is a minor issue' }
        ]
      },
      {
        key: 'frequency',
        label: 'How often does it happen?',
        required: false,
        options: [
          { value: 'once', label: 'It happened once' },
          { value: 'sometimes', label: 'Sometimes' },
          { value: 'always', label: 'Every time' },
          { value: 'unknown', label: 'Not sure yet' }
        ]
      },
      {
        key: 'steps',
        label: 'Steps to reproduce',
        placeholder: '1. Open…\n2. Click…\n3. The issue appears.',
        required: false
      },
      {
        key: 'record_link',
        label: 'Link to the affected page',
        placeholder: 'https://…',
        required: false,
        input: 'url'
      }
    ]
  },
  {
    key: 'feature',
    title: 'Request a feature',
    description: 'An idea to improve the way you work.',
    introduction: 'Start with the need. You do not have to design the solution.',
    subject: 'Give your idea a name',
    subjectPlaceholder: 'e.g. Reuse saved report filters',
    action: 'Share idea',
    fields: [
      {
        key: 'problem',
        label: 'What is difficult or missing today?',
        placeholder: 'Describe a real task and what gets in your way.',
        required: true
      },
      {
        key: 'benefit',
        label: 'What would a better outcome look like?',
        placeholder: 'e.g. My team could prepare its weekly report without rebuilding the filters.',
        required: true
      },
      {
        key: 'audience',
        label: 'Who would benefit?',
        required: false,
        options: [
          { value: 'me', label: 'Me' },
          { value: 'team', label: 'My team' },
          { value: 'organization', label: 'The whole organization' },
          { value: 'customers', label: 'Our customers' }
        ]
      },
      {
        key: 'suggestion',
        label: 'Your proposed solution',
        placeholder: 'Describe an example of how you imagine it working.',
        required: false
      }
    ]
  },
  {
    key: 'help',
    title: 'Ask for help',
    description: 'Guidance on using or setting up the CRM.',
    introduction: 'Tell us what you are trying to do. We will reply by email.',
    action: 'Ask the support team',
    fields: [
      {
        key: 'question',
        label: 'How can we help you?',
        placeholder: 'e.g. How do I require a phone number before a contact enters Qualified?',
        required: true
      },
      {
        key: 'tried',
        label: 'What have you tried so far?',
        placeholder: 'Any steps you followed or where you got stuck.',
        required: false
      }
    ]
  }
];
