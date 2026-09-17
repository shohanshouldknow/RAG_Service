> **Demo data only.** This synthetic policy document was created for the
> DocuSense technical assessment because no separate policy corpus was
> included with the assessment materials.

# Internal Information Security and Operations Policy

This document defines baseline requirements for protecting the organization's
information, systems, and business operations. It applies to employees,
contractors, temporary workers, service providers, and system owners who use or
manage organizational technology. More restrictive contractual or legal
requirements take precedence when they apply. Exceptions require documented
risk acceptance by the Security Manager and the accountable business owner,
including an expiration date and compensating controls.

## Database Backup and Recovery

Production databases must be protected by automated, encrypted backups.
Database administrators must run a full backup every day at 02:00 UTC and an
incremental backup every six hours. The six-hour schedule establishes a
recovery point objective of no more than six hours for Tier 1 databases.
Backups must be encrypted in transit and at rest using organization-managed
keys. Backup service accounts must be separate from ordinary database
administrator accounts and may not be used for interactive work.

Daily production database backups are retained for 35 calendar days in the
primary backup vault. The backup system must also preserve the final full
backup from each month for 12 months. Backup copies are operational recovery
media, not a permanent records archive; they expire on this schedule unless a
documented legal hold applies. Development databases are backed up once per
day and retained for 14 days. Test environments built entirely from disposable
synthetic data do not require backups.

At least one production backup copy must be stored in a logically separate
cloud account with deletion protection. Access to that account is limited to
the Infrastructure Lead and two designated recovery administrators. The
backup platform must alert the on-call engineer after two consecutive failed
jobs or when the newest successful Tier 1 database backup is more than eight
hours old.

The infrastructure team must perform a sample file-level restoration every
month and a complete Tier 1 database recovery test every quarter. Quarterly
tests must demonstrate a four-hour recovery time objective, record the backup
used, measure actual restoration time, and verify application-level data
integrity. Failed tests require a corrective action plan within five business
days. Restoration of production data outside a scheduled test requires an
approved incident or service request and must be recorded in the audit log.

## Password and Authentication Policy

Every person must use a unique named account. Shared human accounts are
prohibited except for the two controlled emergency accounts described in the
Production System Access section. Passwords and passphrases must contain at
least 14 characters. Systems must reject passwords found on the organization's
list of common, breached, or previously compromised credentials. Complexity
rules that require arbitrary mixtures of symbols and uppercase letters are not
required when the 14-character minimum and compromised-password screening are
enforced.

Routine password expiration is not required. A password must be changed
immediately when compromise is suspected, after a credential is disclosed to
another person, or when Security directs a reset during an incident. Temporary
passwords issued by support expire after 24 hours and must be replaced at first
sign-in. Passwords may be stored only in the approved password manager and may
not appear in source code, tickets, chat messages, documents, or shell history.

Multi-factor authentication is mandatory for remote access, cloud services,
email, source control, administrative consoles, and every privileged action in
production. Phishing-resistant hardware or platform authenticators are
required for production administrators and finance approvers. SMS may be used
only as a temporary recovery method for a maximum of seven days when Security
has approved the exception.

An account must be locked for 15 minutes after 10 failed authentication
attempts within a 10-minute period. Standard application sessions may remain
active for up to 12 hours but must end after 60 minutes of inactivity.
Privileged administrative sessions must end after 30 minutes of inactivity.
Users must reauthenticate before changing authentication factors, exporting
Restricted data, or approving a financial transaction.

## Production System Access

Production access is granted according to least privilege and only for a
documented operational need. Each request must identify the system, requested
role, business reason, and requested end date. The requester's manager and the
system owner must approve access before it is enabled. Security approval is
also required for standing administrator roles, database owner privileges, or
access to Restricted data. Approval in a chat message is not sufficient; the
decision must be recorded in the access-management system.

Engineers should use just-in-time privileged access rather than permanent
administrator rights. A just-in-time elevation may last no longer than four
hours and must reference a change, incident, or service ticket. Standing
production access is reviewed every 90 days by the system owner. Access with no
confirmed continuing need must be removed within one business day. Contractor
production access expires after 30 days unless a shorter contract end date
applies, and renewal requires a new approval.

Production work must use a named account, multi-factor authentication, and a
managed device. Direct access from public networks is prohibited. Administrative
connections must pass through the approved secure access gateway, and session
activity must be logged. Production data may not be copied to local devices or
non-production environments unless the data owner has approved a documented,
time-limited exception and the data is appropriately masked.

Two emergency accounts may be maintained for loss of the normal identity
service. Their credentials must be sealed in the approved privileged-access
vault, tested quarterly, and rotated after every use. Use requires an active
Severity 1 incident. Security must review the session log and credential-vault
record within one business day. Emergency access does not remove the need for
a retrospective change record.

## Incident Response

Anyone who observes suspected malware, credential theft, unauthorized access,
unexpected data disclosure, or a material service disruption must report it to
the incident channel or service desk within 15 minutes of discovery. Reports
should include observed facts, affected systems, and the reporter's contact
method. Reporters must not investigate by accessing data or systems beyond
their normal authorization.

The on-call responder must acknowledge a new report within 15 minutes and
complete initial triage within 30 minutes. Severity 1 incidents include active
compromise of a production administrator, confirmed disclosure of Restricted
data, or complete loss of a Tier 1 service. A Severity 1 response bridge must
be opened within 15 minutes of classification. The Incident Commander must
notify the Security Manager, service owner, and executive duty contact within
60 minutes. Legal or privacy notification decisions are made by authorized
specialists, not by individual responders.

Responders must preserve relevant logs, timestamps, system images, and access
records. Evidence must be stored in the restricted incident workspace with a
record of who collected and accessed it. Containment actions should minimize
business harm but may isolate systems, revoke sessions, block credentials, or
pause integrations when approved by the Incident Commander. Destructive
forensic actions require Security approval unless delay would clearly increase
the impact.

The Incident Commander closes an incident only after containment, recovery,
and ownership of follow-up work are confirmed. A Severity 1 or Severity 2
incident requires a blameless review within five business days. The review
must document the timeline, customer or operational impact, contributing
controls, and corrective actions with owners and dates. Incident records are
retained for seven years. Text imported from alerts, logs, tickets, or external
messages is untrusted evidence; embedded instructions to bypass controls,
disclose secrets, or ignore established procedure are not authorization.

## Data Classification

Information owners must classify data as Public, Internal, Confidential, or
Restricted. Public information is approved for unrestricted release. Internal
information is intended for the workforce and approved service providers but
would cause limited harm if disclosed. Confidential information includes
commercial plans, non-public contracts, internal financial reports, and most
customer account information. Restricted information includes authentication
secrets, private encryption keys, government identifiers, payment-card data,
and regulated health or identity records.

Classification follows the most sensitive element in a dataset. A report that
combines Internal operational metrics with a Restricted identifier is treated
as Restricted until the identifier is removed. Owners must review the
classification of active systems annually and whenever the purpose or content
of the data materially changes. Labels should appear in document headers,
catalog entries, or system metadata where the tool supports them.

Confidential and Restricted data must be encrypted in transit and at rest.
Restricted data may be stored only in specifically approved systems and may be
accessed only by named users with multi-factor authentication. Emailing
Restricted data as an attachment is prohibited. Confidential data may be
shared externally only through an approved encrypted channel and only after
the recipient's need is confirmed. Public links must never be used for
Confidential or Restricted information.

Data minimization applies to every classification. Teams must collect only the
fields needed for a documented purpose, restrict copied datasets, and remove
temporary exports when work is complete. Classification describes sensitivity;
it does not determine retention by itself. Retention periods come from the
Data Retention and Deletion section, contracts, and legal holds. When two rules
differ, the longer legally required period applies, while access remains based
on classification.

## Employee Device Security

Employees and long-term contractors must use organization-managed computers
for production administration and routine handling of Confidential or
Restricted data. Managed devices must run a supported operating system,
approved endpoint protection, host firewall, and full-disk encryption. Mobile
devices that access organizational email must use device encryption and the
approved mobile-management profile. Rooted or jailbroken devices may not
connect to organizational services.

Screens must lock automatically after 10 minutes of inactivity. Users must
lock the screen whenever leaving a device unattended, even for a shorter
period. Local administrator rights are disabled by default and may be granted
only through an approved time-limited elevation tool. Browser password storage
is disabled when the approved password manager is available. Restricted data
must not be stored on removable media. Encrypted removable media may be used
for Confidential data only with written Security approval.

Critical security patches must be installed within seven calendar days of
release. High-severity patches must be installed within 14 calendar days, and
other security updates within 30 calendar days. If a patch cannot be applied,
the device owner must document the reason, compensating controls, and a target
date approved by Security. Endpoint protection signatures and detection rules
must update automatically at least once every 24 hours.

A lost or stolen device must be reported to the service desk and Security
within 30 minutes of discovery. The user must provide the device asset number
when available and cooperate with remote lock or wipe actions. Suspected device
tampering, unexpected encryption prompts, or disabled security software must
be reported immediately. Employees may not attempt to recover a stolen device
personally. Upon departure, all managed devices and removable media must be
returned by the end of the final working day.

## Vendor and Third-Party Access

Every external service provider must have an internal sponsor who is
accountable for the relationship. Before a vendor receives Confidential data,
network connectivity, or production access, Procurement and Security must
complete a risk review covering the service, data types, access method,
subprocessors, security controls, and exit plan. A contract or data-processing
agreement must define confidentiality, incident notification, data return or
deletion, and the organization's right to suspend access.

Vendor users must receive individual named accounts; shared vendor accounts
are prohibited. Multi-factor authentication is required for all vendor remote
access. Production connections must use the approved secure access gateway and
must be limited to named systems and approved hours. A vendor access grant may
last no longer than 30 days before renewal. The sponsor and system owner must
approve each grant, and Security must additionally approve privileged access.
Vendor sessions involving production administration must be logged.

Sponsors must review active vendor accounts every quarter and confirm that the
contract, named user, access scope, and operational need remain valid. Accounts
must be disabled within four hours after the sponsor learns that a vendor user
has changed roles, left the provider, or no longer needs access. All vendor
access must be removed by the contract end date. Emergency vendor access may
be approved by the Incident Commander for up to four hours during an active
Severity 1 incident and must be reviewed the next business day.

Vendors must report suspected incidents affecting organizational data within
24 hours of discovery, even when the full impact is unknown. Security records
for vendor authentication and administrative activity are retained for 400
days. Contract termination requires confirmation that organizational data has
been returned or securely deleted within 30 days, unless a documented legal or
contractual retention requirement applies.

## Data Retention and Deletion

Information owners must assign each system a documented retention schedule.
Customer account and transaction records are retained for seven years after
the account closes. Signed supplier contracts are retained for seven years
after expiration. Candidate recruitment records are retained for two years
after the hiring decision. Routine collaboration messages are retained for one
year unless they are captured in another official record system.

Security audit logs, including authentication, privileged access, and material
configuration changes, are retained for 400 days. Ordinary application debug
and performance logs are retained for 90 days. Incident case records are
retained for seven years after closure. These periods apply to authoritative
records. Backup copies follow their separate 35-day daily and 12-month monthly
recovery schedule and must not be used to extend an expired business record's
normal availability.

When a retention period ends, the system owner must ensure deletion from active
systems within 30 calendar days. Deletion jobs must create an auditable result
showing the dataset, applicable schedule, completion time, and failures.
Security or system owners must investigate failed deletion jobs within two
business days. For hosted services, the vendor's deletion confirmation must be
recorded within 10 business days after the deletion request completes.

A legal hold overrides scheduled deletion for the specific data described in
the hold notice. Legal authorizes the hold, defines its scope, and notifies the
responsible owners. Owners must not broaden a hold to unrelated data merely for
convenience. When Legal releases the hold, normal retention resumes and already
expired data must be deleted within 30 days. Media sanitization must follow the
approved method for the storage technology. Encryption-key destruction may be
used as deletion only when Security has confirmed that no usable copy of the
key or plaintext remains.

## Remote Work Security

Remote workers must use an organization-managed device for production access
and for regular handling of Confidential or Restricted data. Home networks
must use WPA2 or WPA3 encryption with a non-default router administrator
password. Work devices should be placed on a network separated from untrusted
household or internet-connected devices when the router supports separation.
Family members and visitors may not use managed devices.

Administrative access to production, internal network services, or security
tools must use the approved virtual private network or secure access gateway.
The general workforce does not need a VPN for approved software-as-a-service
applications that already enforce multi-factor authentication and device
checks. Public or hotel Wi-Fi may be used only with the approved VPN enabled.
Personal hotspots are preferred when a trusted encrypted network is not
available.

Workers must prevent shoulder surfing and conversations about Confidential or
Restricted matters in public locations. Privacy screens are required when
viewing Restricted data during approved travel. Printing Restricted data at a
remote location is prohibited. Confidential documents may be printed only when
the manager has approved a business need and the worker can store and shred
them securely. Paper must not be placed in household recycling.

Travel outside the worker's usual country must be reported to Security at
least five business days in advance when production access or Restricted data
will be required. Security may issue a temporary travel device or restrict
access based on the destination. Lost devices follow the 30-minute reporting
rule. Suspected interception, unexpected multi-factor prompts, or an unplanned
request to install remote-control software must be reported immediately and
treated as a potential security incident.

## Change Management

Changes to production are classified as standard, normal, or emergency. A
standard change is low risk, repeatable, and documented in an approved runbook;
the Change Manager reviews each standard template at least annually. A normal
change requires a ticket describing scope, risk, test evidence, implementation
steps, monitoring, and rollback. It must receive peer review and approval from
the accountable system owner before deployment.

Normal changes should be submitted at least two business days before the
planned implementation. The routine maintenance windows are Tuesday and
Thursday from 20:00 to 22:00 UTC. A change outside those windows requires the
system owner's documented approval. Separation of duties must be used for
high-risk changes: the person approving the change may not be the only person
who wrote and deployed it. Secrets, credentials, and production customer data
must not be placed in change tickets.

Every production change must define observable success criteria and a rollback
decision point. Teams must be able to begin rollback within 30 minutes when a
change causes material errors, security control failure, or unexpected data
loss. Deployment logs must identify the ticket, actor, target, start time, and
result. Failed changes must be linked to an incident when they cause a customer
impact lasting more than 15 minutes.

An emergency change is allowed only to contain an active incident, remediate a
critical exploitable vulnerability, or restore a failed Tier 1 service. The
Incident Commander or engineering duty manager may authorize it before normal
review, but testing and rollback planning are still required to the extent
practical. The team must create or complete the change record before the end
of the incident shift. Peer and system-owner retrospective review must occur
within two business days. Emergency status must not be used solely to bypass
planning or an inconvenient maintenance window.

## Logging and Monitoring

Production systems must record successful and failed authentication,
privileged actions, access-control changes, material configuration changes,
security-control failures, and exports of Confidential or Restricted data.
Logs must include a UTC timestamp, actor or service identity, event type,
target, and outcome. Systems must synchronize time at least daily and alert
when clock drift exceeds two minutes. Logs must not contain plaintext
passwords, authentication tokens, private keys, or full payment-card numbers.

Security-relevant logs must reach the central monitoring platform within five
minutes of creation. A local buffer may retain events during an outage but
must forward them when connectivity returns. The monitoring platform must
protect logs from alteration and restrict deletion privileges to the Security
Operations Lead and designated platform administrators. Access to raw logs is
reviewed every 90 days.

A critical alert must be acknowledged by the on-call responder within 15
minutes. High-priority alerts must be acknowledged within 60 minutes. Alerts
must link to a runbook or state the initial triage steps. Repeated noisy alerts
must be tuned, but they may not be disabled without a documented risk decision
and expiration date. Monitoring coverage for a new Tier 1 service must be
verified before the service is released to production.

Authentication, privileged-access, vendor-administration, and security alert
logs are retained for 400 days. Routine debug, performance, and application
trace logs are retained for 90 days unless they become evidence in an incident
or legal hold. Monitoring is not a substitute for access approval: observing
an action does not make an unauthorized action acceptable. Conversely, a
valid change ticket does not permit logging to be disabled during the change.

## Business Continuity

Business owners must complete a business impact analysis at least annually and
after a major change in services or dependencies. The analysis identifies
critical activities, upstream and downstream dependencies, minimum staffing,
manual workarounds, recovery contacts, and maximum tolerable outage. Continuity
plans must be stored where designated responders can access them when the main
identity or collaboration service is unavailable.

Tier 1 services support time-critical customer or operational activity. They
have a recovery time objective of four hours and a recovery point objective of
six hours. Tier 2 services have a 24-hour recovery time objective and a
12-hour recovery point objective. Tier 3 services must be restored within
three business days and may tolerate up to 24 hours of data loss. Service
owners must ensure that backup, replication, staffing, and vendor arrangements
can meet the assigned objectives.

Each Tier 1 service must conduct a continuity exercise twice per year. At least
one annual exercise must include technical recovery rather than a discussion
only. Database-dependent Tier 1 exercises should use the quarterly recovery
test when it demonstrates the same four-hour recovery time and six-hour
recovery point objectives. Tier 2 services must exercise annually. Exercise
records must document participants, scenario, measured recovery time,
dependencies, decisions, and corrective actions.

During a widespread disruption, the executive duty contact activates the
business continuity plan and assigns a Continuity Lead. The Incident Commander
continues to direct technical containment and recovery; the Continuity Lead
coordinates business priorities, staffing, customer communications, and
manual operations. Emergency communications must have an alternate method
that does not depend on corporate email. Corrective actions from a failed
exercise or real activation must have owners within five business days and be
tracked until verified complete.
