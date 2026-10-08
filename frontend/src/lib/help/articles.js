import { settingsSections } from '$lib/v2/settings-access.js';

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
        text: 'Open your profile menu at the bottom of the navigation bar. The organization selector appears when more than one workspace is available. Use it to switch workspaces. Records, roles and settings belong to the selected organization.'
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
          'Select existing tags, or create a tag if you are an administrator, then save. Pipeline rules may require additional information for the selected stage.'
        ]
      },
      {
        title: 'Edit without leaving your work',
        text: 'In the list, use Actions → Edit to open the editing panel. Inside a contact, use the Properties actions to edit in the same view. Save applies your changes; Cancel closes the editor without saving.'
      },
      {
        title: 'Notes, files and activity',
        text: 'Activity is the first tab, followed by Notes and Emails. Use Notes for comments and Attachments for files (up to 25 MB each). To remove an attachment, use its delete button and confirm the file name shown. Deletion is permanent and requires Delete attachments permission for that object. Activity records creation, actual property changes, assignments, associations, notes, files, appointments and your own synchronized emails. Opening records, downloading files and saving unchanged values do not add entries. Older changes that were never recorded cannot be reconstructed. Last Activity reflects the latest recorded property change, with creation as the fallback.'
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
        text: 'Activity opens first and includes recorded changes, notes, attachments, appointments and your own matching emails. Notes and Emails have separate tabs. Company email history combines visible primary and linked contacts without repeating the same message. Keep company notes here and use a contact for information about a specific person.'
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
          'Use Edit columns to select system and custom properties. Notes and Record ID start hidden and can be selected manually.',
          'Drag a column header to reorder it; use its right edge to resize.',
          'Click a header to sort. Use the search field and filters to narrow the list.'
        ]
      },
      {
        title: 'Saved preferences',
        text: 'Columns and their order are saved per user, organization and object in this browser. Contacts, Companies and Deals also save column widths. Sort order is restored when opening a module without explicit URL options. Returning through navigation always opens the list; pipeline mode stays only in the current URL. Search, filters and pagination are not saved. Closing and reopening a normal tab preserves saved preferences; another browser or clearing site data does not.'
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
    title: 'Configure properties, creation forms, pipelines and tags',
    summary: 'Object-specific fields, stable internal names and stage requirements.',
    sections: [
      {
        title: 'Properties',
        text: 'In Profile & Preferences → Properties, select an object to see its fields, types, internal names and usage count. Create a custom property for that object and choose its field type. Drag properties to change their order in record profiles. System field definitions stay protected.'
      },
      {
        title: 'Creation forms',
        text: 'Open CRM configuration → Creation forms, choose an object, add or remove existing properties, reorder fields and mark those required when creating a record. Save applies to new forms opened by everyone in this organization. The identifying name stays required. Managers need explicit Creation forms permission to manage these settings. When creating a custom property, Add to creation form is off by default; enable it to include the property immediately. These rules do not change existing records or published web forms.'
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
        text: 'Select several tags by searching in a record’s tag field, remove selected tags when needed, or, as an administrator, create one with a color. Administrators and Managers granted Tags management use Tags settings to search, filter, edit name/color, inspect usage, merge or archive. Archiving removes a tag from pickers while preserving existing assignments; restore makes it available again. Merging tags has no automatic undo.'
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
        text: 'New users open the emailed invitation and enter their name, password and password confirmation. Their email and organization are already defined. Existing users sign in with that email to accept. Both complete Profile setup (name, CRM language and timezone) before opening modules. The initial organization administrator also completes Organization information. Closing the browser does not skip pending setup. Invitations expire after seven days; ask an administrator to resend an expired or cancelled invitation.'
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
        text: 'The organization owner is its protected Super Admin. For a new customer organization, the initial invited administrator becomes its owner on acceptance. Admin is a separate assignable role. The Super Admin and CRM owner can appoint or manage administrators. An ordinary Admin manages non-admin team members. The Super Admin cannot be demoted, deactivated or removed through these controls. Only the CRM owner can create new organizations; organization admins cannot create customer accounts.'
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
        text: 'Open the profile menu → Profile & Preferences. Edit your name, phone, communication language and timezone. Choose English or Español under Regional preferences → CRM language for your own interface; communication language is a separate field. The sign-in email is shown as read-only. Profile photo upload is not offered.'
      },
      {
        title: 'Organization settings',
        text: 'Organization holds company details, currency and timezone. Members cannot open Organization settings. Managers need explicit Read only or Manage access; administrators can manage them. These are separate from personal preferences. Change the active organization from its selector in the bottom profile menu.'
      },
      {
        title: 'Notifications',
        text: 'Use the bell in the navigation bar for incoming notifications. Notifications has read and unread history loaded in portions. Preferences control in-app notifications; existing notifications remain in history. Task reminders follow their configured lead time. Calendar events notify the host and internal attendees 15 minutes before the start; connected Google events notify their owner, excluding all-day events. The bell refreshes automatically, and a brief alert appears while the CRM is open. These reminders do not send email or browser push notifications.'
      },
      {
        title: 'Gmail and Google Calendar',
        text: 'Profile → Integrations shows separate Gmail and Google Calendar cards. Connect each service using your own Google account and accept its permissions. Setup required means the CRM owner must configure the Google integration; Reconnect required means authorization needs to be renewed. Manage connections and Sync now here, rather than inside record email tabs. Saving an email access preference or using Google to sign in does not connect Gmail or synchronize calendars.'
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
  },
  {
    slug: 'settings-access',
    category: 'Configuration',
    title: 'Who can use each setting?',
    summary: 'Personal preferences and explicitly delegated Manager settings.',
    sections: [
      {
        title: 'Choose access in Users & Teams',
        steps: [
          'As an administrator, open Profile & Preferences → Users & Teams and choose the user.',
          'Assign Member, Manager or a custom permission set for their work with records. Configure those sets in Roles & Permissions.',
          'Personal, Team and Organization scopes control which records actions apply to. Even Organization scope does not grant Settings administration.',
          'Only the organization Super Admin or CRM owner can appoint or manage other administrators. For a Manager, open Roles & Permissions → Manager → Settings access and grant each section as No access, Read only or Manage. Grants apply to all users assigned to that Manager set; they start with no access.'
        ]
      },
      ...settingsSections.map((section) => ({
        title: section.label + (section.beta ? ' (Beta)' : ''),
        text:
          section.member === 'personal'
            ? 'Every user manages their own preferences. Administrators do not gain control of another user’s personal Google connection.'
            : !['team', 'roles'].includes(section.key)
              ? 'Members and custom roles have no access. Managers need an explicit permission for this section. Admins and Super Admins can manage it in the selected organization.'
              : 'Admin and Super Admin access is required. This destination is hidden from non-admin users; directly opening its URL does not grant permission.'
      })),
      {
        title: 'Web forms and private data',
        text: 'Web forms read access covers the form list and configuration. Submission history, installation tests, publishing and edits require Manage access. Record access does not grant access to another user’s Gmail. Comments deliberately added as internal record notes are shared with teammates who can view that record.'
      }
    ]
  },
  {
    slug: 'accounts-and-invitations',
    category: 'Getting started',
    title: 'Create an account and invite a team',
    summary: 'Invitation-only customer workspaces and first-time setup.',
    sections: [
      {
        title: 'CRM owner: create a customer account',
        steps: [
          'Open /org in the CRM while signed in as the CRM owner, then choose Create new organization. Each organization is a separate customer workspace.',
          'Enter the customer administrator’s email, organization name and timezone. Leave the email blank only when creating your own workspace.',
          'Create the organization. The CRM attempts to send an invitation; if delivery fails, open Users & Teams in that organization and resend it.',
          'The customer opens the invitation, creates a password if needed, completes their profile and then confirms organization information, currency and timezone. They become that organization’s Super Admin.'
        ]
      },
      {
        title: 'Administrator: invite teammates',
        steps: [
          'Open Profile & Preferences → Users & Teams → Invite user.',
          'Enter the teammate’s email and choose the appropriate permission set. Only the Super Admin or CRM owner can appoint another Admin.',
          'The recipient accepts with the invited email and completes their profile before using the CRM. Existing users keep their password and other memberships.',
          'Invitations expire after seven days. Resend expired invitations or cancel invitations that should no longer be used.'
        ]
      },
      {
        title: 'Account boundaries',
        text: 'Public registration is closed. An invitation grants access only to its organization and assigned role. Customer administrators cannot create new customer organizations or access other customers. The CRM owner manages customer accounts separately from organization administration.'
      }
    ]
  },
  {
    slug: 'gmail-records',
    category: 'Communications',
    title: 'Read, send and discuss Gmail on records',
    summary: 'Email history, replies, forwarding and internal team comments.',
    sections: [
      {
        title: 'Connect and find email',
        steps: [
          'Open Profile → Integrations → Connect Gmail and authorize your own Google account. If sending needs authorization, reconnect there.',
          'Open a contact or company → Emails. The contact email must match a message participant. Company history includes visible primary and linked contacts.',
          'Search using any words from the subject, participants or message text. Use Filters for Sent or Received; company records also offer a contact filter.',
          'Conversations appear newest first. Expand a conversation to read messages in chronological order, and load more when available.'
        ]
      },
      {
        title: 'Send, reply or forward',
        steps: [
          'Choose New email, or open a message and choose Reply or Forward.',
          'Review To, CC, subject and message. Your connected Gmail is the sender. Reply keeps the original subject; Forward starts a separate conversation.',
          'Choose Send only when the draft is ready. If the result is uncertain, check Gmail Sent before composing another message to avoid duplicates.'
        ]
      },
      {
        title: 'Permissions and internal comments',
        text: 'Sending requires Edit on the contact or company and Google permission to send. Internal comment requires Manage notes and creates a shared record note referencing the email subject. Teammates with record access can see that comment in Notes and Activity, but do not gain access to your mailbox. Do not put private email content in a team comment unless you intend to share it.'
      },
      {
        title: 'What sync includes',
        text: 'The initial import covers the last 90 days, followed by background sync about every five minutes. Large imports can take several jobs. Full message text is available, including expandable quoted history; remote images and attachments are not imported. Drafts, spam and trash are excluded. The CRM does not create contacts from Gmail, mark messages read in Gmail or track recipient opens. Compose and forward support plain text and To/CC, with up to 25 recipients; attachments are not supported here.'
      },
      {
        title: 'Privacy and troubleshooting',
        text: 'Only you can read your connected mailbox through the CRM, even if another user is an administrator. Current record access is checked again when opening a message. Connections belong to your user profile in the selected organization. Manage connection status and Sync now in Profile → Integrations. Automated CRM notifications use the separate system sender and do not require every user to connect Gmail.'
      }
    ]
  },
  {
    slug: 'google-calendar',
    category: 'Scheduling',
    title: 'Connect and synchronize Google Calendar',
    summary: 'Hosted appointments, meeting notes and two-way updates.',
    sections: [
      {
        title: 'Connect your calendar',
        steps: [
          'Open Profile → Integrations → Connect Google Calendar and authorize your own account.',
          'Choose the calendar. The primary calendar is selected by default. Use a writable calendar to send CRM appointments to Google.',
          'Create appointments from Calendar or Schedule event on a record. The host must be the user with the connected calendar.',
          'Allow about five minutes for background sync or use Sync now in Profile → Integrations. Check the connection status if an appointment does not appear.'
        ]
      },
      {
        title: 'What synchronizes',
        text: 'Google events appear in your CRM calendar. Hosted CRM appointments synchronize title, start/end times and meeting notes in both directions; meeting notes become the Google event description. General contact notes are not exported. The sync window covers the previous 90 days and next 365 days. Google-only events are private to their connected user; shared host availability shows busy times without exposing private details.'
      },
      {
        title: 'Limits and conflicts',
        text: 'Calendar permissions still control CRM changes. This sync does not send invitation emails or add Google invitees. Edit all-day events in Google. If both sides changed, the CRM reports a conflict instead of overwriting them; align the Google event with the desired CRM details and sync again. Disconnecting removes the CRM connection and cached Google data, not appointments or Google events. Switching calendars can leave previously exported events in the old calendar.'
      }
    ]
  },
  {
    slug: 'sign-in-and-files',
    category: 'Getting started',
    title: 'Sign-in sessions and attachment limits',
    summary: 'Reopening the CRM, signing out and uploading files safely.',
    sections: [
      {
        title: 'Closing and reopening the CRM',
        text: 'Closing a normal browser tab does not sign you out. The session can renew for up to 14 days after its last successful renewal; active use can extend it again. There is no separate inactivity timeout. Expired or revoked access requires sign-in. Private browsing or clearing cookies may remove your session earlier. Use Sign out on shared computers.'
      },
      {
        title: 'Upload and delete record attachments',
        text: 'Record attachments allow up to 25 MB per file. Upload attachments and Delete attachments are separate permissions, limited by record access. Use the trash icon and review the confirmation before deleting; deletion is permanent. This limit applies to CRM record uploads, not Gmail forwarding or support uploads. It does not define an organization storage quota.'
      }
    ]
  }
];
export const categories = [...new Set(articles.map((article) => article.category))];
