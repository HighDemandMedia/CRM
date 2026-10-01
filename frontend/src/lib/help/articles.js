// Product guidance for the customized HDM CRM. No customer records or tenant articles.
export const articles = [
  {
    slug: 'website-forms',
    category: 'Configuration',
    title: 'Connect your website forms',
    summary: 'Create contacts from website enquiries and notify your team.',
    sections: [
      {
        title: 'Create a form',
        steps: [
          'Open Settings → Channels & integrations → Web forms → New form. Choose Create a form and enter a name.',
          'Start: add your website addresses, including https://. Add the www address separately if visitors use it.',
          'Prepare: start with Name, Email, Phone, Company and Message. Add, reorder or remove fields. Name and Email are required. Set the title, button text, colors, font, width, corners and columns. Check Desktop and Mobile previews.',
          'Configure: choose the responsible user and CRM/email alerts. Choose a confirmation message or the full URL of an existing thank-you page.',
          'Install & test: publish the form, copy the code and paste it in your website’s HTML/embed block where the form should appear. Save and publish that website page.',
          'Start a test, submit an enquiry on your website, then Check for submission. Review the contact and recipient inbox separately.'
        ]
      },
      {
        title: 'Connect an existing HTML form',
        steps: [
          'Create a connection using Connect my existing form. Add the exact website addresses in Start.',
          'In Prepare, paste the complete <form>…</form> HTML and choose Detect fields. If several forms are found, choose the correct one. Select a CRM property or Skip for every input, then Use these matches. Pasted HTML is inspected locally, never executed or saved.',
          'Review the Website input name for each property. This must match the input’s name attribute, not its visible label. For example, <input name="your-email"> maps Website input name your-email to CRM property Email.',
          'Enter the form ID from <form id="contact-form">. Leave it blank only if that page contains exactly one form. IDs must start with a letter and use letters, numbers, hyphens or underscores. Add a suitable ID to the website form when needed.',
          'Choose the responsible user and alerts. Publish, then paste the connector code once immediately after </form> in that page’s HTML. Keep the website’s existing submit handler.',
          'Publish the website, start a test and submit the existing form. Choose Check for submission and verify the contact and notifications.'
        ]
      },
      {
        title: 'What the connector preserves',
        text: 'The generated connector copies mapped values to the CRM without replacing your website’s design, submit handler, original email delivery or thank-you page. Only named visible inputs, selects and textareas can be collected; passwords, hidden inputs and files are excluded. This browser copy is independent of the website’s own delivery and can be interrupted by navigation, network issues, consent tools or content security rules. For guaranteed coordinated delivery, a developer should submit from your website backend using the public form endpoint and a stable request_id. Older installed scripts without data-mode="copy" may take over submission: replace them with the current installation code, rather than installing both.'
      },
      {
        title: 'Appearance and installation',
        text: 'Appearance settings apply to CRM-built forms only. Mobile layouts use one column. The embedded frame isolates the form from website styles and can scroll when needed; adjust its height in the pasted code if the page needs more room. The thank-you URL must be a published page that exists on your website. For the alternate JavaScript renderer, replace the embed/ suffix in the published preview URL with embed.js and use that URL as a script src at the desired location. Do not install both renderers on the same form placement.'
      },
      {
        title: 'Existing contacts and alerts',
        text: 'Email addresses are matched within the organization. A returning visitor adds a submission to the existing contact without changing its details or owner. The responsible user, current contact owners and selected recipients receive alerts only when active and allowed to view the contact. Personal in-app preferences apply. CRM email alerts use the system sender and do not require a personal Gmail connection. Submission received confirms a CRM record, not delivery to an inbox; check email separately.'
      },
      {
        title: 'Spam protection and troubleshooting',
        text: 'The form must be published and the website origin allowed. Check field names and required values first. Turnstile is optional under Configure → More settings. Add its site key and secret, and authorize your website hostname in Cloudflare. An existing form needs its own available Turnstile token; a token already consumed by the website cannot be reused for the CRM. If the page strips scripts, use its custom-code editor. If an iframe is blocked, check the allowed website addresses. Open the published form to isolate installation problems. Submissions shows recent attempts; it does not prove email delivery.'
      }
    ]
  },
  {
    slug: 'getting-started',
    category: 'Getting started',
    title: 'Find your way around the CRM',
    summary: 'Today, navigation, search and your organization.',
    sections: [
      {
        title: 'Start with Today',
        text: 'Click the High Demand Media logo or Today to see your agenda, tasks, reminders and records that need attention. The view uses the current organization; available records depend on your access.'
      },
      {
        title: 'Find and open records',
        steps: [
          'Use Search near the top of the menu to find CRM records.',
          'Open Contacts, Companies or Deals to switch between list and pipeline views.',
          'Collapse the navigation bar to gain space; the module icons remain available.'
        ]
      },
      {
        title: 'Switch organizations',
        text: 'Open your profile menu at the bottom of the navigation bar. Use the organization selector in that menu to switch workspaces. Records, roles and settings belong to the selected organization.'
      },
      {
        title: 'Available modules',
        text: 'This CRM includes the workflows described in this guide. Experimental modules are maintained separately in a local laboratory.'
      }
    ]
  },
  {
    slug: 'contacts',
    category: 'Records',
    title: 'Create and manage contacts',
    summary: 'Contact details, owners, communication preferences and activity.',
    sections: [
      {
        title: 'Create a contact',
        steps: [
          'Open Contacts and choose New contact. The form opens beside your current view.',
          'Enter the name. Add phone, email, source, language, owner, address and preferred communication channel when available.',
          'Select tags or create one in the tag picker, then save. Pipeline rules may require additional information for the selected stage.'
        ]
      },
      {
        title: 'Edit without leaving your work',
        text: 'In the list, use Actions → Edit to open the editing panel. Inside a contact, use the Properties actions to edit in the same view. Save applies your changes; Cancel closes the editor without saving.'
      },
      {
        title: 'Notes, files and activity',
        text: 'Use Notes for comments and Attachments for files. To remove an attachment, use its delete button and confirm the file name shown. Deletion is permanent and requires Delete attachments permission for that object. Activity records property changes with the time and user. Simply opening the contact is not recorded as an activity. Last Activity reflects the latest recorded property change, with creation as the fallback.'
      },
      {
        title: 'Associate records',
        text: 'Use + in Companies or Deals to add an association. The associated record’s menu can remove the link. Removing a link does not delete the linked record.'
      }
    ]
  },
  {
    slug: 'duplicates-and-merge',
    category: 'Records',
    title: 'Find duplicates and merge contacts',
    summary: 'Understand duplicate warnings, record IDs and merging.',
    sections: [
      {
        title: 'Record ID and duplicate clues',
        text: 'Record ID is the stable internal identifier used by the CRM and integrations. The abbreviated display does not change the full ID. Email, normalized phone and similar names help detect possible existing contacts; shared names or phone numbers are not proof that two people are the same.'
      },
      {
        title: 'Check existing contacts',
        text: 'When entering contact details, matching suggestions can appear. Open the existing contact if it is the person you need. Suggestions only include records you are allowed to view in the organization.'
      },
      {
        title: 'Merge as an administrator',
        steps: [
          'Open Actions → Merge on a contact or in the contact list.',
          'Search for the second contact and compare their properties.',
          'Choose the primary contact and select which values to keep when they differ.',
          'Review and confirm the merge. The primary contact keeps its ID; associations, notes, files and history are consolidated.'
        ]
      },
      {
        title: 'Before confirming',
        text: 'Merge is an administrator action with no automatic undo. The secondary contact is archived and its old link leads to the primary when the viewer has access. Review each pair instead of merging solely because a phone or name matches.'
      }
    ]
  },
  {
    slug: 'companies',
    category: 'Records',
    title: 'Manage companies and their relationships',
    summary: 'Business properties, linked contacts, deals and appointments.',
    sections: [
      {
        title: 'Company properties',
        text: 'Use Companies for businesses. Properties include name, domain, owner, industry, employee count, annual revenue, phone, email, language, source, address, preferred communication channel, tags and page links. Name is required; stage rules can require other properties.'
      },
      {
        title: 'Work from the company profile',
        text: 'Use the Properties editing action to make changes in place. Linked contacts and deals are shown in their association sections. Add links using +; remove associations from the linked record’s menu without deleting the record.'
      },
      {
        title: 'Notes and attachments',
        text: 'Add notes from the Notes section and upload files through Attachments. Keep company information here and use the linked contact for information about a specific person.'
      },
      {
        title: 'Past due deals',
        text: 'Past due highlights open associated deals whose expected close date has passed. It is a sales follow-up signal, not an invoice balance.'
      },
      {
        title: 'Schedule from a company',
        text: 'Use Schedule event in the company profile. The company is selected as an attendee, and its event is distinguished from contact events in the calendar.'
      }
    ]
  },
  {
    slug: 'deals',
    category: 'Records',
    title: 'Track deals from prospecting to closing',
    summary: 'Amounts, expected close dates, ownership and pipeline stages.',
    sections: [
      {
        title: 'Create and associate a deal',
        text: 'Open Deals → New deal. Enter a name and add amount, stage, expected close date, owner, priority, source, phone, email, language, address and tags as needed. Associate the deal with the relevant contact or company. Stage entry rules can request additional fields.'
      },
      {
        title: 'Work the pipeline',
        text: 'Default stages are Prospecting, Proposal, Follow Up, Stan By, Close Won and Close Lost. Your organization may rename, reorder or add stages. Dragging a card changes its stage when the entry rules are satisfied.'
      },
      {
        title: 'Edit and add notes',
        text: 'Edit properties in the deal profile. Add notes in Notes and files in Attachments; Activity remains separate. Contact associations appear above company associations.'
      },
      {
        title: 'Understand the amount and date',
        text: 'Amount is the deal value. Close date is the expected close date, not proof of payment or a reliable historical win timestamp. Close Won is the won outcome; stage percentages can be configured independently.'
      }
    ]
  },
  {
    slug: 'list-and-pipeline',
    category: 'Records',
    title: 'Customize lists and use pipelines',
    summary: 'Columns, sorting, filters, cards and required stage information.',
    sections: [
      {
        title: 'Adjust the list',
        steps: [
          'Switch to the list icon in the module toolbar.',
          'Use Edit columns to add or remove visible columns.',
          'Drag a column header to reorder it; use its right edge to resize.',
          'Click a header to sort. Use the search field and filters to narrow the list.'
        ]
      },
      {
        title: 'Move pipeline cards',
        text: 'Switch to the pipeline icon and drag a card into another stage. The CRM saves the stage change. If information is missing, a side panel asks for the required properties before completing the move. If the source stage is not allowed, the message identifies the permitted route.'
      },
      {
        title: 'Read compact cards',
        text: 'Contacts, Companies and Deals show the main identifying information, applicable value, tags, last activity and days in stage. The first day has no elapsed-time label; stage time updates by day.'
      },
      {
        title: 'Export',
        text: 'CSV export uses the module’s current filters and requires export permission. Reports has a separate Export report action for its totals and charts.'
      }
    ]
  },
  {
    slug: 'calendar',
    category: 'Scheduling',
    title: 'Schedule, reschedule and cancel events',
    summary: 'Hosts, multiple attendees, conflicts and automatic deal creation.',
    sections: [
      {
        title: 'Schedule an event',
        steps: [
          'Open Calendar → Schedule event, or schedule from a contact or company profile.',
          'Choose a title, host, date, start time and end time.',
          'Search for attendees. You can add several contacts, companies or CRM users, including users for an internal meeting.',
          'Review the host’s weekly availability and the titles of existing events.',
          'Add internal notes if needed, review the automatic deal option and schedule.'
        ]
      },
      {
        title: 'Conflicting times',
        text: 'Occupied time stays highlighted in red. You can select it, but scheduling requires confirmation in the app when the host already has an overlapping event. You can return to choose another time.'
      },
      {
        title: 'Automatic deal creation',
        text: 'The scheduling form offers a checked option to create an associated deal when applicable. Review its fields before saving; its proposed title uses the attendee’s name. Tags and notes are not copied into the deal. Uncheck the option for meetings that should not create one, such as internal meetings.'
      },
      {
        title: 'Attendee records and notes',
        text: 'Scheduling updates the appointment field and activity on associated contact/company attendees. Activity identifies when it was scheduled and by whom. Internal event notes are also saved in those attendees’ Notes sections.'
      },
      {
        title: 'View or change an event',
        text: 'Switch between day, week and month views. Click an event to see its details and use Reschedule or Cancel. Click a contact or company attendee’s name to open its profile. Calendar cards show the title and start time.'
      },
      {
        title: 'Google Calendar',
        text: 'Google Calendar connection and synchronization are not enabled yet. Events created here currently belong to the CRM calendar.'
      }
    ]
  },
  {
    slug: 'tasks-and-reminders',
    category: 'Daily work',
    title: 'Manage tasks and reminders',
    summary: 'Assignees, due dates, pipeline view and Today reminders.',
    sections: [
      {
        title: 'Create and assign',
        text: 'Open Tasks → New task. Enter a title, choose assignees by searching their names, and set the stage, priority and due date. Use the available association field to link the relevant record.'
      },
      {
        title: 'Set a reminder',
        text: 'Choose how long before the due date to show a reminder, or select Custom time and enter the supported interval. Reminders appear in Today and Notifications, once per due date and reminder setting. They go to the task assignees, or its creator when unassigned, subject to record access. The reminder day follows your organization’s timezone. This does not schedule a task on the sales calendar.'
      },
      {
        title: 'Work the task',
        text: 'Tasks supports list and pipeline views in the same module. Open a task to review its details, or edit in place without navigating to a separate editing page. Complete the task when the work is done.'
      },
      {
        title: 'Where tasks appear',
        text: 'Manage tasks from Tasks and Today. Task sections are not shown inside contact, company or deal profiles, and tasks are not sales-calendar events.'
      }
    ]
  },
  {
    slug: 'tickets',
    category: 'Daily work',
    title: 'Manage customer tickets',
    summary: 'Support work for your customers, associations and assignees.',
    sections: [
      {
        title: 'Create a ticket',
        text: 'Open Tickets → New ticket or use the ticket creation action in a supported record profile. Enter the title and details, then search for assignees by name. Due date uses a date selection.'
      },
      {
        title: 'Associate the customer',
        text: 'Search for an associated contact or company. Results identify which object each match belongs to. Tickets do not associate with deals in the adapted workflow.'
      },
      {
        title: 'Track progress',
        text: 'Use list or pipeline view and update properties in the ticket profile. Stage rules can require information before a transition. Associated record profiles show their tickets; manage ticket details in Tickets.'
      },
      {
        title: 'CRM product support',
        text: 'Tickets is for your organization’s customer work. To report a problem with the CRM, request a feature or ask High Demand Media for assistance, use Help → Contact support.'
      }
    ]
  },
  {
    slug: 'reports',
    category: 'Reporting',
    title: 'Build a report for a date range',
    summary: 'Choose the date basis, compare periods and interpret values correctly.',
    sections: [
      {
        title: 'Set up the report',
        steps: [
          'Open Reports and choose Contacts, Companies, Deals, Tasks, Tickets or Events.',
          'Choose Date to use, such as Created date, Last activity, Due date or Expected close date, depending on the object.',
          'Set From and To dates, or choose a quick range. Filter by owner/host and stage if needed.',
          'Choose day, week or month for the time chart, and a breakdown such as stage, source or priority.',
          'Review Included records and use Export report if your permissions allow it.'
        ]
      },
      {
        title: 'Read the graph',
        text: 'The X axis shows dates and the Y axis shows record counts. Hover over a column or focus it with the keyboard to see its exact date and count. View data displays the values in a table.'
      },
      {
        title: 'Comparison and money',
        text: 'The comparison uses the immediately preceding period with the same number of days. Monetary amounts are separated by currency. Export report includes the complete totals, breakdown and series, not just the visible records page.'
      },
      {
        title: 'What the report means',
        text: 'Report boundaries use the organization’s timezone. Current stages, owners and amounts are filtered by the selected date; this is not a historical snapshot. Expected close date is planned, and currently won deal value is not cash collected. Last activity counts records by their latest property change, not the number of all actions.'
      }
    ]
  },
  {
    slug: 'properties-pipelines-tags',
    category: 'Configuration',
    title: 'Configure properties, pipelines and tags',
    summary: 'Object-specific fields, stable internal names and stage requirements.',
    sections: [
      {
        title: 'Properties',
        text: 'In Profile & Preferences → Properties, select an object to see its fields, types, internal names and usage count. Create a custom property for that object and choose its field type. Drag properties to change their order in record profiles. System field definitions stay protected.'
      },
      {
        title: 'Names and requirements',
        text: 'The display label is for people; the internal property key is for the API and integrations. Record ID is generated automatically, and Name is required. Other general fields are optional, but pipeline entry rules can make particular properties necessary for a stage.'
      },
      {
        title: 'Pipelines',
        text: 'Select the object in Pipelines. Reorder stages, change display names and percentages, and create custom stages. Internal names remain stable. System default stages cannot be removed. Changes save automatically.'
      },
      {
        title: 'Entry rules',
        text: 'Use Configure on a stage to open its rules panel. Select required properties and allowed source stages. Missing values trigger a completion panel when moving a card, or highlighted fields and a notice when editing. An invalid source stage must be corrected before entering.'
      },
      {
        title: 'Tags',
        text: 'Select several tags by searching in a record’s tag field, remove selected tags when needed, or create one with a color. In Tags settings, search, filter, edit name/color, inspect usage, merge or archive. Archiving removes a tag from pickers while preserving existing assignments; restore makes it available again. Merging tags has no automatic undo.'
      }
    ]
  },
  {
    slug: 'users-roles-teams',
    category: 'Configuration',
    title: 'Manage users, teams and permissions',
    summary: 'Invitations, access scopes and protected administrator roles.',
    sections: [
      {
        title: 'Users and teams',
        text: 'Administrators use Users & Teams to invite users, change their permission set and organize team membership. Select people by name. Deactivation removes organization access while preserving records.'
      },
      {
        title: 'Accept an invitation',
        text: 'New users open the emailed invitation and enter their name, password and password confirmation. Their email and organization are already defined. Existing users sign in with their current account to accept. Invitations expire after seven days; ask an administrator to resend an expired or cancelled invitation.'
      },
      {
        title: 'Access levels',
        text: 'Member uses Personal scope and Manager uses Team scope. Custom permission sets choose Personal, Team or Organization access and enable actions per object: view, create, edit properties, change stages, manage notes, upload attachments, delete attachments, manage associations, delete records, export and owner assignment. Uploading and deleting attachments are separate permissions; deletion is off by default for Member, Manager and custom sets until an admin enables it. Enabled actions must stay within view access.'
      },
      {
        title: 'Calendar and Reports permissions',
        text: 'Calendar permissions separately control scheduling, rescheduling, cancellation, choosing another host and confirming time conflicts. An invited user can view an event without being allowed to change it. Reports respects record visibility; exporting requires export access to both Reports and the underlying object.'
      },
      {
        title: 'Super Admin and Admin',
        text: 'The organization creator is its protected Super Admin. Admin is a separate assignable role. Only the Super Admin can invite or change administrators. The creator cannot be demoted, deactivated or removed through these controls.'
      },
      {
        title: 'Remove a member',
        text: 'Review the removal preview, choose whether to reassign records, and confirm with the exact email. Other assignees remain. Removing membership does not erase the global user’s historical authorship or memberships in other organizations. A new invitation is needed to return.'
      }
    ]
  },
  {
    slug: 'profile-notifications',
    category: 'Configuration',
    title: 'Profile, notifications and integrations',
    summary: 'Personal preferences, organization defaults and connection status.',
    sections: [
      {
        title: 'Profile',
        text: 'Open the profile menu → Profile & Preferences. Edit your name, phone, language and timezone. The sign-in email is shown as read-only. Profile photo upload is not offered.'
      },
      {
        title: 'Organization settings',
        text: 'Organization holds the organization name, currency, timezone and working-hour settings. These are separate from personal preferences. Change the active organization from its selector in the bottom profile menu.'
      },
      {
        title: 'Notifications',
        text: 'Use the bell in the navigation bar for incoming notifications. Notifications has read and unread history loaded in portions. Preferences control in-app notifications; existing notifications remain in history. Task reminders follow their configured lead time. Calendar events notify the host and internal attendees 15 minutes before the start; connected Google events notify their owner, excluding all-day events. The bell refreshes automatically, and a brief alert appears while the CRM is open. These reminders do not send email or browser push notifications.'
      },
      {
        title: 'Gmail and Google Calendar',
        text: 'Profile → Integrations shows separate Gmail and Google Calendar cards. Setup required means the connection is not active. Saving an email access preference or using Google to sign in does not connect Gmail or synchronize calendars.'
      }
    ]
  },
  {
    slug: 'deletion-and-associations',
    category: 'Records',
    title: 'Remove associations or delete a record',
    summary: 'Choose between unlinking records and permanently deleting them.',
    sections: [
      {
        title: 'Remove only the association',
        text: 'Use the associated record’s menu and remove its association where this action is available. Both records remain in the CRM; only their link is removed.'
      },
      {
        title: 'Delete a record',
        text: 'Use Delete in the record profile. Review the consequences and confirm by typing the requested name or code. Where related-record deletion is offered, choose it explicitly; otherwise associated objects remain without that link. Your role must allow deletion of all records selected for removal.'
      },
      {
        title: 'Check first',
        text: 'Deletion is not the same as clearing a stage or archiving a tag. Review the preview before confirming. Use contact merge for duplicate people rather than deleting a contact whose history you want to preserve.'
      }
    ]
  }
];
export const categories = [...new Set(articles.map((article) => article.category))];
