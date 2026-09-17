# Synthetic Operations & Security Policy Handbook

> **Demo data only.** This synthetic policy handbook was created solely for testing a grounded RAG system. It is not associated with any real company, client, or employer.

# 1. Customer Account and Identity Policy

Customer accounts must use a unique email address or organization-issued identifier. Shared customer accounts are not permitted for administrative users. New administrative accounts require approval from the customer success owner and the platform owner before activation.

Administrative users must enable multi-factor authentication before receiving access to billing, user management, exports, or security settings. Passwords must be at least 14 characters long. Passwords may not contain the user's full name, email address, or any of the previous 10 passwords.

Routine password expiration is not required. A password must be changed immediately when there is evidence or reasonable suspicion of compromise, after recovery from an account takeover, after an administrator shares a credential in error, or when Security directs a reset following an incident.

Accounts are temporarily locked after 8 failed sign-in attempts within 15 minutes. The lock lasts 30 minutes unless an administrator verifies the user and performs an approved unlock. Repeated lockouts from multiple geographic regions must be reviewed by Security.

Dormant administrative accounts with no successful sign-in for 60 days are disabled automatically. Disabled accounts may be re-enabled only after the system owner confirms an ongoing business need.

# 2. Production Access Policy

Production access follows least privilege and must be tied to a documented operational need. A normal production-access request requires approval from the requester's manager and the system owner. Security approval is additionally required for standing administrator access, access to encryption keys, or access to Restricted data.

Engineers should use just-in-time privileged access whenever possible. A temporary privileged elevation may last no more than 3 hours and must reference a valid change ticket, incident ticket, or service request.

Standing production access is reviewed every 90 days. Access with no confirmed continuing need must be removed within one business day. Contractor production access expires automatically after 21 days unless renewed through a new approval.

Production work must use named accounts, multi-factor authentication, and managed devices. Direct production access from public Wi-Fi is prohibited. Administrative sessions must use the approved secure access gateway and must be logged.

Emergency access is permitted only during an active Severity 1 incident. Emergency credentials are stored in the privileged access vault, rotated after every use, and reviewed by Security within one business day.

# 3. Database Backup and Recovery Policy

Production databases must be backed up automatically. A full backup runs every day at 01:30 UTC, and incremental backups run every 4 hours.

Daily production database backups are retained for 45 calendar days. The final full backup from each month is retained for 18 months. Development databases are backed up once per day and retained for 10 days.

At least one production backup copy must be stored in a logically separate cloud account with deletion protection. Access to that recovery account is limited to the Infrastructure Manager and two designated recovery administrators.

The backup platform must alert the on-call engineer after two consecutive failed backup jobs or when the newest successful production database backup is more than 6 hours old.

A sample file-level restore must be performed every month. A complete Tier 1 database recovery test must be completed every quarter. Tier 1 database recovery tests must demonstrate a 3-hour recovery time objective and a 4-hour recovery point objective.

Failed recovery tests require a corrective-action plan within 5 business days.

# 4. Logging and Monitoring Policy

Authentication events, privileged access activity, material configuration changes, and security alerts must be sent to centralized monitoring.

Security-relevant events must reach centralized monitoring within 10 minutes of creation. Log sources that fail to report for more than 20 minutes must generate an operational alert.

Security audit logs are retained for 420 days. Ordinary application debug logs are retained for 75 days. High-volume performance metrics are retained for 30 days unless a longer period is required for an active investigation.

Production log timestamps must use UTC. Systems must synchronize time with approved network time sources.

Teams may not disable security logging to improve performance without written approval from Security. Temporary logging exceptions must include an expiry date and compensating control.

# 5. Incident Response Policy

Employees and contractors must report suspected security incidents immediately through the approved incident channel. Lost or stolen corporate devices must be reported within 30 minutes of discovery.

Severity 1 incidents include confirmed compromise of production credentials, active ransomware, unauthorized disclosure of Restricted data, or an outage affecting all customers.

The Incident Commander coordinates containment, recovery, communications, and decision tracking during a Severity 1 incident.

Security must preserve relevant evidence before destructive remediation whenever doing so does not create unacceptable operational risk.

A preliminary incident summary is due within 2 business days after containment. A final post-incident review must be completed within 7 business days after recovery.

Corrective actions from the final review must have an owner and target date. High-priority corrective actions should be completed within 30 calendar days unless the Security Lead approves an exception.

# 6. Employee Device Security Policy

Corporate laptops must use full-disk encryption, endpoint protection, automatic screen lock, and centrally managed updates.

The screen must lock after no more than 10 minutes of inactivity. Local administrator rights are not provided by default.

Critical security patches must be installed within 72 hours of release or internal approval. High-severity patches must be installed within 10 calendar days.

Employees may not store Restricted customer data permanently on local devices. Temporary local copies must be encrypted and deleted immediately after the approved work is complete.

Lost or stolen devices must be reported to Security within 30 minutes. Security may remotely lock or wipe managed devices when necessary to protect company or customer data.

Personal devices may access email and collaboration services only when enrolled in the approved mobile-device management program. Personal devices may not access production administration tools.

# 7. Vendor and Third-Party Access Policy

Every external service provider must have an internal business sponsor. Before a vendor receives Confidential data, production access, or network connectivity, Procurement and Security must complete a documented risk review.

Vendor users must have individual named accounts. Shared vendor accounts are prohibited. Multi-factor authentication is mandatory for vendor remote access.

Vendor production access may last no longer than 14 days before renewal. The internal sponsor and system owner must approve each grant. Security must also approve privileged vendor access.

Vendor accounts must be disabled within 4 hours after the sponsor learns that a user has left the provider, changed roles, or no longer needs access.

Vendors must report suspected incidents involving company or customer data within 12 hours of discovery.

When a contract ends, organizational data must be returned or securely deleted within 20 calendar days unless a legal or contractual retention obligation applies.

# 8. Data Classification and Handling Policy

Information is classified as Public, Internal, Confidential, or Restricted.

Public information is approved for unrestricted release. Internal information is intended for employees and approved contractors but is not sensitive enough to require special handling.

Confidential information includes non-public contracts, customer contact data, internal financial reports, and internal architecture documentation.

Restricted information includes authentication secrets, private encryption keys, unmasked payment data, government identification numbers, and production credentials.

Restricted data must be encrypted in transit and at rest. Restricted data may be accessed only from managed devices using approved applications.

Restricted data may not be sent through personal email, consumer file-sharing services, or unapproved messaging applications.

When Restricted data is used in non-production environments, it must be masked or replaced with synthetic data unless the data owner and Security approve a documented exception.

# 9. Data Retention and Deletion Policy

Customer account and transaction records are retained for 6 years after the account closes. Signed vendor contracts are retained for 7 years after contract expiration.

Candidate recruitment records are retained for 18 months after the hiring decision. Routine collaboration messages are retained for 1 year unless captured in another official record system.

Security audit logs follow the separate 420-day logging schedule. Backup copies follow the separate 45-day daily and 18-month monthly recovery schedule.

When a retention period ends, the system owner must ensure deletion from active systems within 30 calendar days.

Deletion jobs must produce an auditable record showing the dataset, applicable schedule, completion time, and failures. Failed deletion jobs must be investigated within 2 business days.

A legal hold suspends normal deletion only for the specific data described in the hold notice. When Legal releases the hold, normal retention resumes.

# 10. Change Management Policy

Production changes must have a change record before deployment.

Normal changes require:
- a description of the change,
- affected systems,
- implementation plan,
- rollback plan,
- testing evidence,
- risk level,
- planned deployment time,
- responsible engineer.

High-risk changes require approval from the system owner and an independent technical reviewer.

Emergency changes may proceed during an active incident when delay would create greater risk. An emergency change record must be created or completed within 4 hours after the change.

Routine production maintenance windows are Tuesday and Thursday from 22:00 to 01:00 UTC. Planned customer-impacting work outside these windows requires approval from the Operations Director.

Changes that affect authentication, encryption, network boundaries, or production data handling require Security review.

# 11. Remote Work and Network Security Policy

Employees may work remotely from approved locations using managed devices.

Administrative access to production systems must use the approved secure access gateway. Direct administrative access from public networks is prohibited.

When using public Wi-Fi, employees must connect through the approved corporate VPN before accessing Internal or Confidential services.

Restricted data should not be viewed in public locations where unauthorized people can observe the screen.

Home routers used for remote work must have vendor-supported firmware and a non-default administrator password.

Employees must not connect company devices to unknown USB network adapters, unapproved travel routers, or shared computers.

# 12. Business Continuity Policy

Business owners must complete a business impact analysis at least once per year and after major changes to critical services.

Tier 1 services have:
- recovery time objective (RTO): 3 hours,
- recovery point objective (RPO): 4 hours.

Tier 2 services have:
- recovery time objective (RTO): 18 hours,
- recovery point objective (RPO): 8 hours.

Tier 3 services must be restored within 4 business days and may tolerate up to 36 hours of data loss.

Tier 1 services must conduct a continuity exercise twice per year. Tier 2 services must conduct an exercise once per year.

At least one annual Tier 1 exercise must include technical recovery rather than discussion only.

During a widespread disruption, the executive duty contact activates the business continuity plan. The Incident Commander directs technical recovery, while the Continuity Lead coordinates staffing, business priorities, and customer communications.

# 13. Customer Refund and Service Credit Policy

Customer refunds and service credits must be tied to a documented billing or service issue.

Customer Support may approve a refund up to USD 100 without additional approval. Refunds above USD 100 and up to USD 500 require approval from a Support Manager.

Refunds above USD 500 require approval from both the Finance Manager and the Customer Success Director.

Duplicate charges should be refunded after the duplicate transaction is confirmed.

Service credits for availability incidents are based on the customer's contract. Support must not promise a specific credit percentage unless the contract or approved incident communication states it.

Approved refunds must be submitted to Finance within 2 business days. Finance should complete the payment reversal or credit within 7 business days when payment-provider processing allows.

# 14. Business Travel and Expense Policy

Employees must obtain manager approval before booking international business travel.

For domestic travel, pre-approval is required when the expected total trip cost exceeds USD 750.

Hotel expenses are reimbursable up to USD 180 per night before taxes unless a higher rate is approved in advance due to event or location constraints.

The standard meal reimbursement limit is USD 65 per day. Alcohol is not reimbursable.

Taxi, rideshare, rail, and public transportation expenses are reimbursable when they are reasonably required for business travel.

Expense reports must be submitted within 15 calendar days after the employee returns from travel. Receipts are required for individual expenses of USD 25 or more.

Personal entertainment, minibar purchases, traffic fines, and upgrades purchased for personal convenience are not reimbursable.
