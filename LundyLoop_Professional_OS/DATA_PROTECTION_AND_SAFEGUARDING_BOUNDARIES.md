# LundyLoop Pro — Data Protection & Safeguarding Boundaries

## Status of this document

This is a prototype implementation aid, not legal advice, a privacy notice, a DPIA, a records-management schedule or a safeguarding policy. Each organisation remains responsible for its own lawful basis, special-category conditions, transparency, security, access controls, retention and incident response.

---

## 1. What the application stores

The flagship may store:

- an alias and optional group code;
- exact pupil wording or a placeholder showing that local audio was used;
- communication route and support level;
- adult interpretation kept separately;
- decision scope, audience, named owner and dates;
- decision, reason, action, Plan B or trial details;
- feedback returned and pupil review;
- retention date;
- a tamper-evident audit-event chain;
- an optional local audio blob where the browser and policy permit it.

By default, data stays inside the browser profile on the device. The application makes no automatic network request and has no analytics.

---

## 2. Local storage is not secure case management

The preferred data store is IndexedDB. A browser-storage or in-memory fallback may be used where IndexedDB is unavailable.

Local storage has important limitations:

- another person using the same unlocked browser profile may be able to view it;
- clearing browser data can delete it;
- it does not automatically synchronise or back up;
- device loss, profile reset or browser policy changes may remove access;
- the application has no role-based access control, central audit service or administrator console;
- the local SHA-256 chain can reveal alteration of retained audit events, but it does not make the database immutable and cannot prove that a record was not deleted or replaced wholesale.

Use the prototype only on devices and profiles approved by the organisation.

---

## 3. Data minimisation

Use an alias or initials unless identity is necessary for the stated purpose. Avoid storing:

- full names, dates of birth and addresses;
- detailed medical or diagnostic information;
- detailed safeguarding disclosures;
- allegations or investigation material;
- unnecessary information about family members or peers;
- free-text interpretations that go beyond what is needed to route and return the participation loop.

The redacted CSV intentionally excludes aliases and exact pupil words. A full JSON backup does not.

---

## 4. Safeguarding bypass

Where a child may be at risk, the ordinary LundyLoop workflow must not delay action.

Staff should:

1. follow the setting’s approved safeguarding process immediately;
2. contact the designated safeguarding lead or emergency services where required;
3. record detailed information only in the approved safeguarding system;
4. use LundyLoop, if appropriate, only to mark that the matter was transferred;
5. select **transfer and redact local voice** where local sensitive text should not remain in the prototype.

The “I need help staying safe” button gives a pupil-facing instruction but deliberately does not create a case or store disclosure details.

Data-protection law does not prevent necessary safeguarding information sharing. Decisions should remain fair, proportionate, lawful and limited to what is necessary.

---

## 5. Lawful basis and special-category information

Before live use, the organisation should identify:

- purpose and necessity;
- Article 6 lawful basis;
- any Article 9 condition where special-category data may be processed;
- whether criminal-offence data could arise;
- privacy information for pupils and families;
- who has access;
- whether a DPIA is required;
- retention and deletion rules;
- approved transfer destinations;
- processor/controller responsibilities if the design is later moved into a hosted service.

Do not assume that consent is automatically the correct lawful basis for school processing. Separately, pupil participation itself should remain voluntary and free from pressure.

---

## 6. Accuracy and voice fidelity

The tool keeps exact pupil wording and adult interpretation in separate fields. Corrections create another version rather than silently overwriting the original wording.

This supports accuracy, but staff still need to:

- read back scribed words where appropriate;
- state the support used;
- avoid leading prompts;
- correct factual errors;
- distinguish a pupil’s words from professional judgement;
- avoid treating a communication difference as lower reliability.

---

## 7. Audio boundary

Local audio is optional and disabled when storage is unavailable.

Before recording:

- check organisational policy and device permissions;
- explain what will be recorded, why, who can access it and when it will be deleted;
- record the pupil’s agreement using an accessible route;
- stop immediately if they withdraw;
- avoid recording other people in the background;
- transfer any formal evidence to an approved system if it must be retained.

The application does not use speech recognition and does not claim that an audio clip has been transcribed verbatim.

---

## 8. Retention and deletion

Each case receives a local retain-until date. This is a prompt, not an approved retention schedule.

Before pilot use, decide:

- how long low-risk participation records are needed;
- when a record should be transferred, anonymised or deleted;
- how reopened cycles affect retention;
- whether a closed loop still needs formal retention elsewhere;
- who runs the expired-record review;
- how deletion requests and records-management holds are handled.

The purge function permanently deletes expired local cases and associated local audio. It cannot delete copies already exported or transferred.

---

## 9. Export and backup risks

### Redacted CSV

Designed for process analysis. It excludes exact pupil words and aliases, but case IDs, topics, routes, dates and outcomes may still become identifiable when combined with other information.

### Plain JSON backup

Contains full local data and may include audio encoded inside the file. Treat it as sensitive.

### Encrypted backup

Where Web Crypto is available, the application uses:

- PBKDF2 with SHA-256;
- 250,000 iterations;
- a random 16-byte salt;
- AES-256-GCM;
- a random 12-byte IV.

Encryption protects the downloaded file contents against casual access, but it does not manage passwords, authorise recipients, secure the endpoint or prevent an authorised user exporting data. Store the password separately using an organisation-approved method.

---

## 10. Screen privacy

Use the privacy shield when the device is left unattended or another person approaches. Presentation mode blurs exact words on shared displays, but it is not access control: users can turn it off.

The optional auto-shield timer and blur-on-window-loss setting reduce accidental exposure; they do not secure an unlocked device.

---

## 11. Minimum local deployment decision

Do not move from fictional demonstration data to live pupil use until the organisation can answer all of the following:

- What precise purpose are we pursuing?
- Why is this information necessary?
- Which device and browser profile are approved?
- Who can open it?
- What privacy information has been provided?
- What is the safeguarding bypass?
- What information is prohibited from local entry?
- What is the retention period?
- Where are formal records transferred?
- Are backups permitted and where are they stored?
- Who monitors participation debt and overdue returns?
- How can a pupil correct, withdraw or challenge their record?
