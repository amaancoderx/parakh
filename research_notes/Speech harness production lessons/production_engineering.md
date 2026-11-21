# Production engineering for "Parakh" (Hindi/Hinglish call-transcript correction harness): India law, vendor data policies, PII, AWS deployment, API design, observability and cost

Research date: 2026-11-21 (Saturday; code freeze is Sun 22 Nov 2026, 2 PM IST). "In force" means in force as of today. Most legal sources here are law-firm or government summaries. The primary MeitY Rules PDF returned HTTP 403 to automated fetch, so check exact rule wording in the Gazette (G.S.R. 846(E) for the Rules, per one compliance guide) before relying on it.

---

## Q1. DPDP Act 2023 + DPDP Rules 2025: what applies to call recordings and contact lists, and what is in force as of Nov 2026

### Takeaway
As of 21 Nov 2026, most DPDP obligations are **not yet in force**: notice, consent, security safeguards, breach intimation, retention/erasure, children's data, SDF duties and the cross-border rule all start on **13 May 2027**. Only the definitions, the Data Protection Board's machinery (in force since Nov 2025) and the consent-manager provisions (since 13 Nov 2026) are live. The older IT Act s.43A / SPDI Rules 2011 regime still applies until May 2027. Even so, Parakh should be built to the 2027 rules now: they are final, the hackathon judges will ask about them, and a proposal to bring them forward exists, though it has not been notified.

### Cited Findings

**Timeline and status**
- The Act was enacted by Parliament on 11 Aug 2023. The government says the DPDP Rules 2025 were notified on 14 Nov 2025, after 6,915 consultation inputs, and that they set an "eighteen-month period for phased compliance", [PIB backgrounder, 17 Nov 2025](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- Khaitan & Co gives the notification date as **13 Nov 2025** and sets out three phases. (i) **Immediately**: definitions, establishment of the Data Protection Board, rule-making and transitional powers. (ii) **After 1 year, 13 Nov 2026**: registration and operation of consent managers. (iii) **After 18 months, 13 May 2027**: "core operational provisions… (a) consent… (b) obligations applicable to Data Fiduciaries; (c) obligations applicable to significant Data Fiduciaries; and (d) the remaining powers of the Board", [Khaitan & Co ERGO, 15 Nov 2025](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf). The 13 vs 14 Nov discrepancy is probably gazette date vs press-release date.
- Rules 3, 5–16, 22 and 23 (notice, security, breach, retention, children, SDF, rights, cross-border, research exemption, calls for information) commence on 13 May 2027, [Taxmann on Rule 7](https://www.taxmann.com/post/blog/personal-data-breach-intimation-rule-7-dpdp); [Saga Legal / Legal500](https://www.legal500.com/firms/237811-saga-legal/c-india/news-and-developments/the-privacy-timer-starts-now-analysing-the-dpdp-rules-and-its-18-month-countdown)
- **Interim regime:** "the existing data protection framework under Section 43A of the [IT Act 2000] read with the [SPDI] Rules 2011 will remain in force and not be repealed until the end of the 18-month period." Section 72-A of the IT Act (wrongful disclosure in breach of a lawful contract) continues to apply, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)
- **Consent managers:** registration opened on 13 Nov 2026 through a MeitY/Board portal, with a minimum net worth of ₹2 crore, [The Tribune](https://www.tribuneindia.com/news/consent-managers/govt-opens-registration-for-consent-managers-under-dpdp-act-rs-2-crore-net-worth-required); [ANI](https://www.aninews.in/news/business/govt-opens-registration-for-consent-managers-under-dpdp-act-rs-2-crore-net-worth-required20261114145151/). Consent managers must be Indian companies, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf). One analysis says the Board has no members yet, so registration is not yet practical, [Elets eGov](https://egov.eletsonline.com/2026/11/india-opens-consent-manager-registration-under-dpdp-act/) (status not independently verified).
- **PROPOSED, not in force:** at a January 2026 stakeholder consultation, MeitY proposed cutting the 18-month window to 12 months, at least for SDFs, which would have meant 13 Nov 2026. It also proposed making the cross-border restrictions and the government's call-for-information power effective immediately, [S.S. Rana & Co.](https://ssrana.in/articles/meity-plans-to-cut-short-dpdp-compliance-timeline-and-notify-cross-border-restrictions-for-sdfs/); [Mondaq](https://www.mondaq.com/india/data-protection/1773554/meity-plans-to-cut-short-dpdp-compliance-timeline-and-notify-cross-border-restrictions-for-sdfs). No gazette notification confirming this was found, [dpdprules.org](https://dpdprules.org/blog/dpdp-18-months-to-12-months-proposal). News on the consent-manager launch (Nov 2026) still describes 13 May 2027 as "the next major phase", [Tribune](https://www.tribuneindia.com/news/consent-managers/govt-opens-registration-for-consent-managers-under-dpdp-act-rs-2-crore-net-worth-required)

**Scope and household exemption**
- The Act does not apply to personal data processed by an individual for any personal or domestic purpose, [dpdpa.com, s.3](https://dpdpa.com/dpdpa2023/chapter-1/section3.html); [KPMG decoding DPDPA](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2023/08/decoding-the-digital-personal-data-protection-act-2023.pdf). One site numbers the provision differently (s.3(2)(a) vs s.3(c)).
- The Central Government may notify classes of fiduciaries, startups among them, as exempt from ss.5, 8(3), 8(7), 10 and 11 under s.17(3), [Taxmann, exemptions](https://www.taxmann.com/post/blog/exemptions-under-dpdp-act). No such startup notification was found.

**Notice and consent (Rule 3, from May 2027)**
- At minimum, the notice must contain: "(i) an itemised description of personal data sought to be processed; (ii) the specified purpose(s)… (iii) a specific description of the goods or services to be provided or uses to be enabled." It must be presented "independently", meaning separate from the T&Cs. It must include a communication link (website and/or app) for withdrawing consent, "as simple as the providing of the original consent", and for exercising rights. The final rules replaced "itemized" with "specific" for the goods/services description, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)
- Consent must be clear and informed, and can be withdrawn at any time, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf). In a dispute, the fiduciary bears the burden of proving that notice was given and consent obtained, [law.asia / Mondaq-type summary via search](https://law.asia/?p=691995) (secondary)
- The Act's seven principles are consent and transparency, purpose limitation, data minimisation, accuracy, storage limitation, security safeguards and accountability, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)

**Security, breach, logs**
- The reasonable security safeguards are indicative ("such as"): encryption, obfuscation, masking, "virtual tokens mapped to the personal data", access controls, monitoring and logging, continuity measures, and **retention of logs for breach detection for 1 year**, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)
- **Breach:** the Board must be told "without undue delay", followed by a detailed report **within 72 hours** of becoming aware (the Board can extend this on written request). Affected Data Principals must be told "without any delay" through their account or registered contact mode. The Rules set no fixed hour count for notifying individuals, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf). The notice to individuals must be in plain language and cover what happened, the likely impact, the mitigation taken and a contact for help, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- **Penalties** go up to ₹250 crore for failing to maintain security safeguards, up to ₹200 crore each for failing to notify a breach or for breaching children's-data obligations, and up to ₹50 crore for other violations, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)

**Retention and erasure**
- Under s.8(7), the fiduciary must erase data when consent is withdrawn or the specified purpose is no longer served, whichever comes first, unless law requires retention. It must also make its processor erase, [Taxmann, retention](https://www.taxmann.com/post/blog/data-retention-erasure-dpdp-act); [DSCI FAQ on retention/erasure](https://www.dsci.in/files/content/documents/2025/faq-on-data-retention-and-data-erasure-v2.pdf)
- **New Rule 8(3):** "all personal data, traffic data and logs generated from data processing activities [must] be retained at least for 1 year, even after the fulfilment of the purpose, or deletion of the user account, for purposes specified in the Seventh Schedule" (state functions, national security, disclosures under law), [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)
- **Third Schedule:** a maximum 3-year retention from the last interaction, plus **48-hour advance notice before deletion**. This applies only to e-commerce and social-media platforms with ≥20M registered Indian users and online gaming with ≥5M, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf). It does not apply to Parakh.
- Access, correction and erasure requests and grievances must be resolved within **90 days**, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf); [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)

**Children**
- A child is anyone under 18. Processing a child's data needs verifiable consent from a parent or guardian, verified as an identifiable adult through identity details already held, details provided voluntarily, or a DigiLocker-type virtual token, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf). Exemptions cover essential services such as healthcare, education and real-time safety, [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)

**Data processors**
- Under s.8(2), a fiduciary may engage a processor only under a valid contract and only for activities connected with offering goods or services. The fiduciary stays answerable for the processing, [dpdpa.com s.8](https://dpdpa.com/dpdpa2023/chapter-2/section8.html); [Taxmann on DPAs](https://www.taxmann.com/post/blog/data-processing-agreement-dpdp-act)

**Cross-border transfer (s.16 / Rule 15)**
- The model is a **negative list**: transfers are allowed unless the Central Government notifies a restricted country. **No restricted list has been published**, and s.16/Rule 15 have not commenced (start date 13 May 2027). Section 16(2) preserves stricter sectoral rules, such as RBI payment-data localisation, [King Stubb & Kasiva](https://ksandk.com/data-protection-and-data-privacy/indias-new-cross-border-data-transfer-framework/); [Bar & Bench column](https://www.barandbench.com/columns/the-dpdp-cross-border-transfer-rules-arent-live-yet-so-why-are-contracts-being-redrafted-as-if-they-are)
- Rule 15 lets the government require fiduciaries to meet conditions before making data available to a foreign State or entities under its control. SDFs may be required to keep specified personal data and traffic data in India, on a committee's recommendation, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)

**Significant Data Fiduciaries**
- SDFs are designated by government notification based on the volume and sensitivity of the data they process. They must run an annual DPIA, commission an independent audit and report findings to the Board, carry out "algorithmic due diligence" on software that handles personal data, and may face localisation directions, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf); [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf). The Rules contain **no numeric user-count threshold** for SDFs. No SDF list had been notified as of the sources found, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf); [Alastor Infosec, Aug 2026](https://www.alastorinfosec.com/blog/2026-08-07-dpdpa-significant-data-fiduciary-meity-12-month-proposal-india-2026)

**Research exemption**
- Processing for research, archiving or statistical purposes is exempt if it is lawful, limited to necessary data, reasonably accurate, retained only as long as needed, secured, and comes with contact details for rights requests, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)

### Inferences
- **Roles:** once Parakh is a hosted service, Parakh (the builder) is a **Data Fiduciary** for its own account data and probably for each user's learned-names store. OpenAI, Sarvam and AWS are its **Data Processors**, which requires a valid contract (s.8(2)); their API/DPA terms serve as that contract. An individual running Parakh on their own calls for themselves likely falls under the household exemption, but the service operator does not.
- **Contact lists are third-party data:** every contact name and number belongs to a Data Principal who never consented to Parakh. Minimise: use only display names, not numbers, for name biasing. Keep them per-user and never pooled across users. Send only the short candidate list relevant to a call, not the whole address book, to vendors. Offer deletion. The DPDP Rules explicitly list "virtual tokens mapped to personal data" as a safeguard, so storing hashed or tokenised numbers fits the text.
- **The other party on each call is also a Data Principal.** Consent from the uploading user does not cover the counterparty. For the demo, the participants consented. For production, record consent per participant and per purpose ("transcribe and correct this call; store transcript for N days").
- **Minimum consent notice for the demo (Rule 3-shaped):** (1) data items: call audio, transcript, speaker labels, contact display names, learned name list; (2) purpose: transcribe and correct names and numbers for you; no training or ads; (3) processors and locations: Sarvam (India), OpenAI (US, or India-resident project), AWS Mumbai; (4) retention, e.g. audio deleted 24 h after processing, transcript 30 days; (5) a withdraw/delete link and grievance contact; (6) under-18 users not allowed. Show it as a standalone screen with a checkbox and log the timestamp and notice version.
- **Breach readiness costs little:** keep an incident runbook with a Board notice within 72 h, log retention ≥1 year (CloudWatch Logs retention setting), and an email list of affected users.
- **Cross-border:** sending audio to OpenAI US endpoints is **not prohibited today**, and no country is on the negative list. It is still the riskiest part of the flow if the proposed acceleration of s.16 is notified, or if a future SDF designation brings localisation. An India-first routing option (Sarvam, or an OpenAI India-resident project) is a sensible feature to mention on the slides.
- **SDF:** a solo hackathon project will not be designated an SDF. Call it out as "not applicable; designation is by notification".

### Gaps
- The primary Rules PDF on meity.gov.in returned 403, so the exact text of Rules 3, 6, 7, 8, 10 and 15 was not read directly. Wording comes from the Khaitan summary.
- Whether voice recordings or "voice patterns" count as biometric "sensitive personal data" under the still-in-force SPDI Rules 2011 was not verified. If they do, written consent and a privacy policy under Rule 5 of the SPDI Rules apply today.
- One search result claimed "foundational duties relating to notice, consent… are already in force". It could not be attributed, and it contradicts Khaitan, PIB and the Nov 2026 news coverage. Treat it as unreliable.
- No AZB, Cyril Amarchand or Trilegal notes were retrieved. Khaitan, S.S. Rana, KSK and Saga Legal were used instead.

---

## Q2. Is recording phone calls legal in India (one-party consent, IT Act, telecom law, TRAI/DoT)?

### Takeaway
No Indian statute clearly authorises or bans a participant recording their own call. The case law is split. Several High Courts treat recording without the other party's consent as an Article 21 privacy violation. The Supreme Court (Vibhor Garg, 2025) held such recordings **admissible as evidence** in matrimonial cases, which is a ruling on evidence, not a licence to record. For a product, the defensible position is **all-party, informed consent**, captured and logged. That is what the demo already has.

### Cited Findings
- **Supreme Court, Vibhor Garg v. Neha, 2025 INSC 829 (14 Jul 2025):** set aside the Punjab & Haryana HC and held that secretly recorded spousal phone calls are admissible in matrimonial proceedings. "The mere fact that a conversation was recorded without the consent or knowledge of the speaker does not, by itself, render the evidence inadmissible." Admissibility still requires relevance, identification and accuracy, [LiveLaw](https://www.livelaw.in/top-stories/secretly-recorded-telephonic-conversation-of-spouse-admissible-in-matrimonial-cases-supreme-court-297390); [SC Observer](https://www.scobserver.in/supreme-court-observer-law-reports-scolr/evidentiary-value-of-secretly-recorded-phone-calls-between-spouses-in-marital-disputes-vibhor-garg-v-neha/). Commentators stress that it "should not be treated as a blanket license" for surveillance, [Mondaq](https://webiis10.mondaq.com/india/trials-appeals-compensation/1652876/divorce-in-the-digital-age-sc-allows-secretly-taped-calls-between-spouses)
- **High Courts, privacy line:** the Chhattisgarh HC held that recording phone conversations without knowledge and consent violates Article 21, [Bar & Bench](https://www.barandbench.com/news/chhattisgarh-high-court-recording-conversations-without-consent-right-to-privacy). The Delhi HC said "tapping phone lines or recording calls without consent is a breach of privacy" (prima facie, in a bail matter), [LiveLaw](https://www.livelaw.in/news-updates/tapping-phone-lines-recording-calls-without-consent-breach-right-to-privacy-delhi-high-court-216173). In July 2026 the Telangana HC reportedly held secret recordings of a spouse's calls to violate privacy and to be inadmissible in divorce proceedings, [LiveLaw](https://www.livelaw.in/amp/high-court/telangana-high-court/telangana-high-court-secretly-recording-spouse-calls-right-to-privacy-540791); [Free Press Journal](https://www.freepressjournal.in/india/secretly-recording-spouses-calls-without-consent-violates-privacy-inadmissible-in-divorce-proceedings-telangana-high-court). This appears to be in tension with Vibhor Garg; the judgment was not read.
- **One-party consent is unsettled:** a law-firm note says one AP High Court decision recognised that a person may record their own conversation, while a later decision refused a one-party recording between spouses as a privacy violation, [Vaish Associates via Mondaq](https://webiis08.mondaq.com/india/privacy-protection/1383316/unauthorized-phone-recordings-deemed-a-violation-of-privacy-rights)
- **Telecommunications Act 2023:** s.20(2)(a) gives the government interception powers, carried over largely from s.5(2) of the Telegraph Act 1885, which it repealed. The Act addresses state interception, not private participant recording, [LiveLaw article](https://www.livelaw.in/amp/articles/surveillance-state-or-secure-nation-unveiling-the-interception-powers-in-indias-telecom-act-246058); [PRS Legislative Brief](https://www.prsindia.org/files/bills_acts/bills_parliament/2023/Legislative_Brief-Telecommunications_Bill_2023.pdf). Interception rules followed in 2024, [Telecommunications (Lawful Interception) Rules 2024](https://www.thc.nic.in/Central%20Governmental%20Rules/Telecommunications%20(Procedures%20and%20Safeguards%20for%20Lawful%20Interception%20of%20Messages)%20Rules,%202024.pdf)
- IT Act s.72-A (disclosure of personal information in breach of a lawful contract or without consent) remains applicable alongside the DPDPA, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)
- Under the DPDP framework, call recordings count as personal data. One advisory brochure lists voice call recordings under communications data (truncated in the result), [Grant Thornton DPDPA brochure](https://www.grantthornton.in/globalassets/1.-member-firms/india/assets/pdfs/flyers/dpdpa-rules-detailed-brochure_final-25th-november-2025-1.pdf)

### Inferences
- For the hackathon demo, put a slide line such as "All demo calls recorded with informed consent of every participant; consent captured on [date]; audio deleted after processing." Keep a signed or recorded consent artefact for each demo call.
- Product guardrails: (a) a consent attestation checkbox for each upload ("all parties to this call consented to recording and AI transcription"); (b) an optional in-call announcement script in Hindi and English; (c) no feature that encourages covert recording.
- Under DPDP from May 2027, the uploading user's consent does not cover the counterparty's personal data. All-party consent is also the cleanest DPDP basis.

### Gaps
- **No TRAI or DoT regulation or consultation addressing private call recording by participants was found.** Telecom-licence conditions on operators were not researched. Treat "TRAI/DoT position" as unanswered.
- The Telangana HC July 2026 judgment text, and how it squares with Vibhor Garg, were not read.
- Criminal-law exposure (for example under the Bharatiya Nyaya Sanhita) for covert recording was not researched.

---

## Q3. Vendor data policies: OpenAI, Sarvam, AWS India regions

### Takeaway
OpenAI's **/v1/audio/transcriptions endpoint keeps no abuse-monitoring logs and no application state, and is ZDR-eligible**. The GPT endpoints (/v1/responses, /v1/chat/completions) keep abuse logs for up to **30 days** unless the org has ZDR or Modified Abuse Monitoring, both of which need sales approval. OpenAI offers **India at-rest data residency** for API projects, and India inference residency was reported in Nov 2026. Sarvam claims India residency, and its **retention is configurable per workspace but indefinite until an Owner sets it**, so set it to 0 days today. AWS Mumbai (ap-south-1) and Hyderabad (ap-south-2) charge the same for Fargate, but Amazon Transcribe appears to be Mumbai-only.

### Cited Findings

**OpenAI**
- API data is not used for training unless you opt in (since 1 Mar 2023). "Abuse monitoring logs are generated for all API feature usage and retained for up to 30 days, unless longer retention is required by law", [OpenAI "Your data"](https://developers.openai.com/api/docs/guides/your-data)
- Endpoint table:

| Endpoint | Abuse-monitoring retention | Application state | ZDR eligible |
|---|---|---|---|
| `/v1/audio/transcriptions` | None | None | Yes |
| `/v1/responses` | 30 days | None, with exceptions | Yes, with limitations |
| `/v1/chat/completions` | 30 days | None, with exceptions | Yes, with limitations |
| `/v1/realtime` | 30 days | None | Yes |

  ZDR and MAM both "require prior approval by OpenAI and acceptance of additional requirements" (via sales). ZDR also forces `store=false` on responses and chat completions, [OpenAI "Your data"](https://developers.openai.com/api/docs/guides/your-data)
- Aug 2026: OpenAI said it will require 30-day retention on its most capable models and is previewing "Private Safety Processing" to preserve ZDR, [Axios, 19 Aug 2026](https://axios.com/2026/08/19/openai-previews-zero-retention-safety-system-as-anthropic-requires-data-logs); [The Next Web](https://thenextweb.com/news/openai-zero-data-retention-private-safety-processing). The "Your data" table now has a "PSP/Safety Retention eligible" column. It shows transcription as "No" and responses/chat as "Yes, with limitations", [OpenAI](https://developers.openai.com/api/docs/guides/your-data)
- **Data residency:** at-rest residency in Japan, **India**, Singapore and South Korea for the API Platform (announced 7 May 2025), enabled by "creating a new Project… and selecting the relevant country." The announcement does not say whether inference happens in-region, [OpenAI, "Introducing data residency in Asia"](https://openai.com/index/introducing-data-residency-in-asia/)
- **India inference residency (secondary reports, Nov 2026):** described as covering "supported GPT-6 Luna requests"; it reportedly requires India selected for both storage and processing, an India regional endpoint, and **active ZDR**, with access through sales, [CRN Asia](https://www.crnasia.com/india/news/2026/openai-brings-api-inference-residency-to-india-addresses-enterprise-data-localisation-needs); [Analytics India Mag](https://analyticsindiamag.com/ai-news/openai-launches-api-inference-residency-in-india); [CASRAI](https://casrai.org/news/openai-india-api-inference-residency-november-2026). Not confirmed against an official OpenAI page.
- **gpt-transcribe model:** "High-accuracy speech-to-text model for file and Realtime input transcription." Price is **$0.0045 per audio minute**. Endpoints are `v1/audio/transcriptions` and `v1/realtime/transcription_sessions`. It supports "unstructured context and keyword hints" and "multiple language hints… code-switching". Default rate limits: Build 5,000 RPM, Launch 10,000 RPM, Grow 30,000 RPM, [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-transcribe). OpenRouter lists a release date of 5 Aug 2026, [OpenRouter](https://openrouter.ai/openai/gpt-transcribe-20260805). Older models: gpt-4o-transcribe is about $0.006/min and gpt-4o-mini-transcribe about $0.003/min (third-party estimates), [diyai.io](https://diyai.io/ai-tools/speech-to-text/openai-whisper-api-pricing-2026/)

**Sarvam**
- Retention is set per workspace (Settings → Workspace → Data policy). "Until an Owner sets a retention period, your workspace's data is retained indefinitely." Model APIs and Voice Agents can override it per product. **0 days ("No retention") is available for Model APIs** but not yet for Voice Agents. Options: 0 d, 1 d, 15 d, 45 d, 1/2/3/6/12/24 months. Changes are not retroactive. Only an org Owner can change them, [Sarvam data retention docs](https://docs.sarvam.ai/api/platform/data-retention); [changelog 15 Sep 2026](https://docs.sarvam.ai/changelog/2026/9/15.md)
- **Conflict:** the Sarvam developers page reportedly says "zero data retention after processing unless you explicitly request it", [sarvam.ai/developers](https://sarvam.ai/developers) (seen in a search snippet), which contradicts the "indefinite until set" default in the docs.
- The Trust Center claims "complete data residency in India" and ISO 27001 and SOC 2 Type II, [Sarvam Trust Center](https://www.sarvam.ai/trust-center) (search snippet). A third party reports that the managed environment runs in Azure Central India, [safeguard.sh](https://safeguard.sh/models/sarvam-saaras-v3) (lower reliability). The consumer privacy policy excludes business customer content, which falls under the DPA referenced in the EULA, [Sarvam privacy policy](https://sarvam.ai/privacy-policy); [EULA](https://www.sarvam.ai/eula)
- **STT limits:** the REST (real-time) API takes **≤30 s of audio per request**. Batch takes ≤2 h per file and ≤20 files per job. Accepted sample rates are 8, 16, 22.05 and 44.1 kHz, with 16 kHz best and 8 kHz recommended for telephony. Model `saaras:v4` covers 23 languages. Diarization is **batch-only, +20% cost**. Timestamps are chunk-level only; there are no word-level timestamps, [Sarvam STT FAQ](https://docs.sarvam.ai/api/speech-to-text/faq)
- **Rate limits (Pay-as-you-go / Pro / Growth):** STT REST 60 / 100 / 4,000 req/min. Batch 20 / 100 / 500 req/min. WebSocket 20 / 100 / 100 concurrent. Over-limit returns 429 `rate_limit_exceeded_error`, and **no Retry-After header is documented**. Retry 503 like 429. **402 means credits are exhausted, so do not retry.** Do not poll batch faster than about every 3 s on PAYG; the SDK default is 5 s, [Sarvam rate limits](https://docs.sarvam.ai/api/getting-started/ratelimits)
- **Pricing:** STT is about ₹0.49 / ₹0.45 / ₹0.41 per minute (PAYG / Pro / Growth), billed per second. Batch with diarization is ₹0.59 / ₹0.54 / ₹0.50, [Sarvam pricing](https://docs.sarvam.ai/api/pricing) (via search summary)

**AWS regions**
- Fargate prices are identical in Mumbai (ap-south-1) and Hyderabad (ap-south-2): x86 $0.04256 per vCPU-h and $0.004655–0.00466 per GB-h; ARM $0.02383 per vCPU-h and $0.00261 per GB-h, [AWS Price List, ECS ap-south-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-south-1/index.json); [ap-south-2](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-south-2/index.json)
- The Amazon Transcribe price list exists for ap-south-1 but returns NoSuchKey for ap-south-2, [Transcribe ap-south-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/transcribe/current/ap-south-1/index.json)

### Inferences
- **Do these today, about 10 minutes:** (1) set the Sarvam workspace retention to **0 days** for Model APIs. (2) Create a dedicated OpenAI API project, India data residency if the org is eligible, and use only `/v1/audio/transcriptions`, which has no retention. (3) For GPT correction calls, set `store=false` and send **minimised text** (transcript snippets plus candidate names), never audio or the full contact book. Disclose the 30-day abuse-log retention in the notice unless ZDR is granted.
- On the slides, frame the routing as "India-first": Sarvam (India-hosted) is the primary witness, OpenAI the secondary witness, and the GPT reconciler gets minimised text.
- Choose **ap-south-1 (Mumbai)** over Hyderabad: same compute price, and Transcribe and probably more services are available there.

### Gaps
- Sarvam's STT-specific retention default and the exact hosting location were not confirmed on an official Sarvam STT page.
- An official OpenAI page for India inference residency, and whether gpt-transcribe is covered by it, was not found.
- Sarvam's DPA terms (sub-processors, breach notice SLA) were not read.

---

## Q4. PII redaction for Hindi/Hinglish transcripts (phone, Aadhaar, PAN, UPI, bank accounts)

### Takeaway
No turnkey AWS service redacts **Hindi** PII. Comprehend PII is documented for English and Spanish only, and Transcribe redaction is not supported for hi-IN (it is for en-IN). Microsoft Presidio ships India pattern recognisers (Aadhaar with checksum, PAN, voter ID, passport, GSTIN, vehicle registration), and those work on digits and Latin letters regardless of language. That makes **Presidio plus custom regex recognisers (UPI, Indian mobile, IFSC, account numbers), run after number normalisation**, the practical path. Because Parakh's job is to fix names and numbers, **pseudonymise rather than blindly redact** before the LLM step.

### Cited Findings
- Presidio India entities: **IN_PAN** (pattern + context), **IN_AADHAAR** (pattern + context + **checksum**), **IN_VEHICLE_REGISTRATION** (pattern + context + checksum), **IN_VOTER**, **IN_PASSPORT**, **IN_GSTIN** (pattern + validation). Generic entities include PHONE_NUMBER (extensible through `supported_regions`), CREDIT_CARD (checksum), EMAIL_ADDRESS, IBAN_CODE, PERSON (NER-based) and IP_ADDRESS, [Presidio supported entities](https://presidio.dataprivacystack.org/supported_entities/). The docs have moved to a new home, presidio.dataprivacystack.org, [redirect from microsoft.github.io](https://microsoft.github.io/presidio/supported_entities/)
- Community examples of custom Indian recognisers often use simple regexes without checksums. Treat them as starting points only, [search summary of tutorials, e.g. Medium](https://medium.com/@nkbvikram/presidio-by-microsoft-a-practical-guide-to-detecting-and-masking-pii-at-scale-c3b39ce4f52c)
- **Amazon Comprehend:** the DetectPiiEntities API accepts `LanguageCode` values including `hi`, [API ref](https://docs.aws.amazon.com/comprehend/latest/APIReference/API_DetectPiiEntities.html). However, the developer guide lists PII detection as **English and Spanish** only, [Comprehend supported languages](https://docs.aws.amazon.com/comprehend/latest/dg/supported-languages.html); [real-time PII](https://docs.aws.amazon.com/en_us/comprehend/latest/dg/realtime-pii-api.html). In 2022 Comprehend added India entity types (Aadhaar, PAN, voter ID, passport and others) for English text, [AWS What's New, May 2022](https://aws.amazon.com/about-aws/whats-new/2022/05/amazon-comprehend-detects-redacts-pll-entity-types-across-us-uk-canada-india)
- **Amazon Transcribe:** the hi-IN row reads Redaction = **no**. en-IN redaction is batch plus streaming, [Transcribe supported languages](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
- The DPDP Rules list "encryption, obfuscation, masking, or using virtual tokens mapped to the personal data" as security measures, [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)

### Inferences
- **Pipeline order:** ASR witnesses → inverse text normalisation of spoken Hindi/English numbers (for example "nau aath saat…" or "double five" into digits) → Presidio analyzer with India recognisers plus custom regexes → **tokenise** (`<AADHAAR_1>`, `<PHONE_2>`) the categories the correction step does not need (Aadhaar, PAN, card, account numbers) → LLM reconciler sees tokens plus the names and numbers under correction → de-tokenise in the response. Store the token vault per job and delete it with the job.
- **Starter regexes** (my own, unverified; add context words and checksum checks):
  - Indian mobile: `(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)`
  - Aadhaar: `(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)` plus Verhoeff checksum (Presidio already ships this)
  - PAN: `\b[A-Z]{3}[PCHFATBLJG][A-Z]\d{4}[A-Z]\b`
  - UPI VPA: `\b[\w.\-]{2,256}@(?:ok)?[a-z]{2,64}\b`, filtered against a bank-handle list (ybl, okaxis, oksbi, paytm and so on) so it does not collide with email
  - IFSC: `\b[A-Z]{4}0[A-Z0-9]{6}\b`
  - Bank account: `(?<!\d)\d{9,18}(?!\d)` **only** within about 5 tokens of context words such as "account", "khata", "a/c", "खाता"
  - Also match Devanagari digits `[०-९]` by normalising them to ASCII first.
- **Redact before the LLM?** Yes for identifiers that are irrelevant to the correction task. No for the names and numbers Parakh is correcting: send those but minimise the context, and use `store=false` and a no-retention transcription endpoint. Log only redacted transcripts. The evidence trace should store token IDs, not raw values.
- PERSON detection in Hindi or Romanised Hinglish with Presidio's default spaCy English models will be weak. The user's own contact list (an exact or fuzzy gazetteer) is a better name detector for this use case than generic NER.

### Gaps
- Whether Presidio's India recognisers are enabled in the default registry, or must be added explicitly, was not confirmed.
- Presidio's multilingual support for Hindi NER was not researched.
- Quality benchmarks for any Hindi or Hinglish PII detector were not found.

---

## Q5. Deploying on AWS in hours: compute choice, uploads, async jobs, secrets, region, cost, Amazon Transcribe as an extra witness

### Takeaway
**App Runner is closed to new customers (since 30 Apr 2026), so do not plan on it** unless the account already used it. The fastest container path is **ECS Express Mode**: one CLI call gives Fargate, an HTTPS ALB, autoscaling and a URL, at about $1.5/day in Mumbai for a tiny task. The fastest serverless path is **Lambda** (timeout now up to 30 min, but a 6 MB synchronous payload cap), fed by **S3 presigned uploads** and an async job pattern. Use **ap-south-1**. Amazon Transcribe hi-IN supports custom vocabulary (batch and streaming) and is a cheap third witness.

### Cited Findings

**Compute options**
- **App Runner:** "no longer open to new customers. Existing customers can continue to use the service as normal… we do not plan to introduce new features." AWS recommends ECS Express Mode, [AWS App Runner availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html). Closed effective 30 Apr 2026 per search summary of the same doc.
- **ECS Express Mode:** "With a single API call, you provide a container image and two IAM roles", and ECS provisions "an ECS service on Fargate, an Application Load Balancer, auto scaling, and networking". "There is no additional charge." Provisioning "typically takes 3–5 minutes". CLI: `aws ecs create-express-gateway-service --execution-role-arn … --infrastructure-role-arn … --primary-container '{"image":…,"containerPort":8080}' --health-check-path / --scaling-target '{"minTaskCount":1,"maxTaskCount":4}'`. A GitHub Action exists (`aws-actions/amazon-ecs-deploy-express-service@v1`), [AWS App Runner → ECS Express migration guide](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)
- Express Mode expects a default VPC with public subnets. Up to 25 Express services in a VPC share one ALB. The ALB cannot be swapped for an NLB or removed, [ECS Express getting started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html); [AWS Containers blog](https://aws.amazon.com/blogs/containers/extending-amazon-ecs-express-mode-to-build-an-optimal-container-environment/); launched Nov 2025, [InfoQ, Dec 2025](https://www.infoq.com/news/2025/12/aws-ecs-express-mode)
- **Lambda quotas (current):** timeout up to **1,800 s (30 min)**. Memory 128 MB–10,240 MB, with about 1 vCPU at 1,769 MB. Invocation payload is **6 MB each way synchronous**, 200 MB for streamed responses, **1 MB asynchronous**. `/tmp` 512 MB–10 GB. Container images up to 10 GB. Default concurrency is 1,000, but "**New AWS accounts have reduced concurrency and memory quotas**", [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- **Lambda Web Functions** (serverless HTTP servers, new): request timeout defaults to 30 s (range 3–900 s), 2 vCPU and 2 GB per environment, 64 concurrent requests per environment by default, [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- Function URLs support response streaming, but not inside a VPC. Streamed responses run at 2 MBps after the first 6 MB, [Lambda response streaming docs](https://docs.aws.amazon.com/en_gb/lambda/latest/dg/configuration-response-streaming.html); [AWS What's New, Jul 2025](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-lambda-response-streaming-200-mb-payloads)

**Uploads with S3 presigned URLs**
- Presigned URLs can authorise PUT uploads. Expiry is 1 min–12 h from the console and up to 7 days from the SDK or CLI with IAM-user SigV4. With role credentials, the URL **expires when the session does**; ECS task role credentials "typically rotate every 1-6 hours". SigV4 presigned uploads support SHA-256 and other checksums. You can enforce a maximum signature age with `s3:signatureAge` in the bucket policy. Presigned URLs are bearer tokens, [S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)

**Amazon Transcribe hi-IN**
- hi-IN supports batch and streaming input, number transcription in batch and streaming, the custom-vocabulary table column in batch and streaming, custom language models in **batch only**, **no redaction**, and Call Analytics post-call, [Transcribe supported languages](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
- A custom vocabulary only applies to audio in its own language. If language ID detects a different language, the vocabulary is not applied. The file limit is 50 KB. List-format vocabularies are being deprecated, so use table format, [Transcribe custom vocabulary](https://docs.aws.amazon.com/transcribe/latest/dg/custom-vocabulary.md); [how-vocabulary](https://docs.aws.amazon.com/transcribe/latest/dg/how-vocabulary.html). AWS has published a Hindi/Hinglish custom-vocabulary walkthrough for call transcription, [AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/improve-transcription-accuracy-of-customer-agent-calls-with-custom-vocabulary-in-amazon-transcribe)

**Mumbai (ap-south-1) unit prices, AWS Price List API, published 2026-11-21**
- Fargate ARM: $0.02383/vCPU-h, $0.00261/GB-h. x86: $0.04256/vCPU-h, $0.004655/GB-h, [ECS price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-south-1/index.json)
- ALB: $0.0239/h plus $0.008 per LCU-h, [ELB price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/ap-south-1/index.json). Public IPv4: $0.005/h per in-use address, [VPC price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/ap-south-1/index.json)
- Lambda: $0.20 per 1M requests. x86 $0.0000166667/GB-s, ARM $0.0000133334/GB-s. Free tier 1M requests and 400K GB-s, [Lambda price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSLambda/current/ap-south-1/index.json)
- SQS standard: $0.40 per 1M requests, first 1M free, [SQS price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSQueueService/current/ap-south-1/index.json)
- Secrets Manager: $0.40 per secret-month and $0.05 per 10K API calls, [Secrets Manager price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSSecretsManager/current/ap-south-1/index.json)
- ECR storage: $0.10/GB-month, [ECR price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECR/current/ap-south-1/index.json)
- Transcribe: batch `TranscribeAudio` $0.0001/s (= $0.006/min). Streaming $0.0001667/s (= $0.01/min). CLM batch $0.0001/s for the first 250K min. Call Analytics $0.0005/s, [Transcribe price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/transcribe/current/ap-south-1/index.json). The flat $0.006/min batch rate is lower than one would expect; check it on the console pricing page before quoting it.

### Inferences
- **Recommended architecture for 15 h** (ECS Express path, lowest risk for a Python app that already exists as CLI scripts):
  1. Wrap the harness in **FastAPI** with these routes: `POST /v1/uploads` returns a presigned S3 PUT URL and `audio_id`. `POST /v1/jobs` takes `{audio_id, user_id, options}` and returns `202 {job_id}`. `GET /v1/jobs/{id}`. `GET /v1/jobs/{id}/transcript`. `DELETE /v1/jobs/{id}`. `GET /healthz`. Serve the static demo page from the same container, or from S3/CloudFront if time allows.
  2. Run the job inside the same container as a background worker (asyncio task, or a thread pool fed from an in-process queue) and persist job state to **DynamoDB or S3 JSON**. Add SQS only if you have time. A single task with min=max=1 avoids distributed-queue complexity for the demo.
  3. Use a Docker image built for **linux/arm64** (about 45% cheaper vCPU), pushed to ECR, then `create-express-gateway-service` in ap-south-1.
  4. Store the Sarvam and OpenAI keys in **Secrets Manager** (2 secrets = $0.80/month) and inject them as ECS secrets. The task role gets scoped `s3:PutObject/GetObject` on one bucket and `secretsmanager:GetSecretValue`.
  5. On the S3 bucket: block public access, SSE-S3 or SSE-KMS, a **lifecycle rule that expires `audio/` after 1 day**, and CORS for the demo origin's PUT.
- **Cost estimate (my arithmetic from the prices above):** one ARM task at 0.5 vCPU and 1 GB costs $0.0145/h. Add ALB $0.0239/h, about 1 LCU at $0.008/h, and about 3 public IPv4 at $0.015/h, for roughly **$0.06/h ≈ $1.5/day ≈ $45/month**. Running it from now through judging (about 3 days) costs roughly $5. A Lambda path costs close to $0 at demo volume: a 30 s job at 1 GB ARM is $0.0004. Vendor ASR dominates. For a 3-min call: Sarvam about ₹1.47, OpenAI gpt-transcribe about $0.0135, Transcribe about $0.018 per price list. The GPT reconciliation cost depends on the model chosen and was not researched.
- **Lambda alternative:** use a container-image Lambda behind a Function URL, or Lambda Web Functions. Upload audio via a presigned URL, because the 6 MB sync payload cap rules out direct uploads of most call audio. Trigger processing through **async invoke or an S3 event**, since async payload is capped at 1 MB, so pass only the S3 key. Poll `GET /jobs/{id}`. This is cheaper but adds cold starts and quota risk on a new account.
- **Avoid long synchronous requests through the ALB.** Use 202 plus polling, or server-sent events for progress. Multi-witness ASR plus LLM on a 5-min call can easily exceed tens of seconds.
- **Sarvam's 30 s REST limit means chunking.** A 3-min call needs about 6 REST requests. At 60 RPM on PAYG, throughput caps at roughly 10 such calls per minute, so use the **Batch API** for whole calls (2 h per file, 20 req/min) and REST only for the live demo.
- **Amazon Transcribe as a third witness:** build a per-user table-format custom vocabulary from learned names. Remember the 50 KB limit and Devanagari or Latin charset rules. hi-IN batch output gives word-level timestamps and confidences, which suit ROVER-style voting. Hinglish code-switching can trip language identification, and the vocabulary then gets dropped, so set `LanguageCode=hi-IN` explicitly.
- **Region:** ap-south-1, for Transcribe availability and same-region S3, Fargate and Secrets.

### Gaps
- **Lightsail containers** pricing and limits were not researched.
- The ALB default idle timeout (commonly 60 s) and whether Express Mode exposes it were not verified.
- API Gateway timeout limits were not re-verified.
- No official page confirms whether ECS Express Mode is available in ap-south-1. It is believed to be broadly available, but check this first.
- Presigned POST with a `content-length-range` condition, useful for capping upload size, was not covered by the fetched page.
- SSM Parameter Store (standard tier, free) pricing was not fetched.

---

## Q6. API design for a transcription-correction service (async jobs, webhooks, idempotency, evidence per edit, versioning)

### Takeaway
Copy the established ASR-vendor shape: **submit → 202 with an ID → webhook or poll → fetch the result**. Webhooks carry only `{id, status}` and the client fetches the full result. Retry deliveries for a bounded number of attempts. Make `POST /jobs` idempotent with an **`Idempotency-Key`** header (an IETF draft, not yet an RFC) and also dedupe on the audio SHA-256. Parakh's differentiator is the **per-edit evidence trace**, so make it first-class in the schema.

### Cited Findings
- **AssemblyAI:** `webhook_url` set at creation, with optional `webhook_auth_header_name` / `webhook_auth_header_value`, and custom query params for metadata. The webhook POST payload is only `transcript_id` and `status` (`completed` | `error`). The receiver must return 2xx **within 10 s**. **4xx is not retried.** Otherwise AssemblyAI retries up to 10 attempts about 10 s apart. Deliveries come from fixed source IPs. The recommended flow is to receive, ack, then `GET /v2/transcript/{id}`. The response carries a `webhook_status_code`, [AssemblyAI webhooks](https://www.assemblyai.com/docs/deployment/webhooks)
- **Deepgram:** with `callback` set, it responds immediately with a `request_id` and processes asynchronously. On non-2xx it retries **up to 10 times, 30 s apart**. The method is POST by default, or PUT via `callback_method`, [Deepgram callback docs](https://developers.deepgram.com/docs/callback). Dedupe on `request_id` because retries can duplicate deliveries (community guidance, not official), [Hookdeck guide](https://hookdeck.com/webhooks/platforms/guide-to-deepgram-webhooks-features-and-best-practices)
- **Idempotency-Key header:** IETF httpapi WG draft-07 (Oct 2025), still an active Internet-Draft on the Standards Track, not an RFC. Its purpose is to make POST and PATCH fault-tolerant. Earlier drafts said a server SHOULD return **409** if a retry arrives while the original is in flight, and **422** if a key is reused with a different payload, [IETF datatracker](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/); [draft-07](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html)
- Sarvam's own batch model shows the job pattern in the vendor layer: jobs of up to 20 files, poll no faster than plan limits, SDK `wait_until_complete()` with 5 s polling, [Sarvam rate limits](https://docs.sarvam.ai/api/getting-started/ratelimits)

### Inferences
- **Endpoints (v1):**
  - `POST /v1/uploads` → `{audio_id, upload_url, expires_at, required_headers:{x-amz-checksum-sha256}}`
  - `POST /v1/jobs` with headers `Idempotency-Key` and `Authorization`, body `{audio_id | audio_url, user_id, language_hint:"hi-IN", witnesses:["sarvam","openai","aws"], context:{contact_ids? | names[]}, webhook:{url, secret}, retention:{audio_ttl_h:24}}` → `202 {job_id, status:"queued", links}`
  - `GET /v1/jobs/{id}` → `{status: queued|transcribing|reconciling|completed|failed|partial, progress, witnesses:[{name, status, latency_ms, error?}], cost:{…}}`
  - `GET /v1/jobs/{id}/result` → transcript plus edits (below)
  - `DELETE /v1/jobs/{id}`: erases audio, transcript and token vault (DPDP erasure). `DELETE /v1/users/{id}/memory`: erases learned names.
- **Evidence per edit**, the differentiator to show judges:
  ```json
  {"edit_id":"e3","span":{"start_ms":41200,"end_ms":42900,"char":[118,131]},
   "before":"राहुल शर्मा","after":"Rahul Sharma",
   "type":"name","confidence":0.91,
   "evidence":[{"source":"sarvam","text":"राहुल शर्मा","conf":null},
               {"source":"openai","text":"Rahul Sharma","conf":-0.12},
               {"source":"contacts","match":"Rahul Sharma (contact #c_19)","score":0.94},
               {"source":"user_memory","hits":3}],
   "rule":"contact_match>0.9 & 2/3 witnesses agree","model":"gpt-x@2026-…","pipeline_version":"parakh-0.4.1"}
  ```
- **Idempotency:** store `(user_id, Idempotency-Key) → {request_hash, job_id}` for 24 h. Same key with the same body returns the original 202. Same key with a different body returns 422. Same key while still processing returns the existing job, or 409. Separately, the **audio SHA-256** (from the S3 checksum) plus `pipeline_version` and context hash is the cache key for skipping repeat vendor calls.
- **Webhooks:** send only `{job_id, status, event_id}`. Sign with HMAC-SHA256 over `timestamp.body` in an `X-Parakh-Signature` header. Treat 2xx within 10 s as success, never retry 4xx, and retry others with exponential backoff, up to 10 attempts. The client fetches the result. For the demo, polling alone is fine and webhooks can be a slide-level "designed for".
- **Versioning:** use a URL prefix `/v1`. Put `pipeline_version` and vendor model IDs in every result so stored transcripts are reproducible. Make additive fields only within v1.
- **Partial results:** a `partial` status lists the failed witnesses, so clients know the output came from degraded consensus.

### Gaps
- Rev.ai API conventions were not researched.
- AssemblyAI's behaviour on 5xx (counted against the retry limit or not) is ambiguous in its docs.
- The idempotency status codes in the current draft-07 (as opposed to earlier drafts) were not confirmed.

---

## Q7. Observability and cost control (per-request cost, latency percentiles, OTel/CloudWatch, caching, rate limiting, retries, circuit breakers)

### Takeaway
At this scale, keep it simple. Write **one structured JSON log line per vendor call and per job** to CloudWatch Logs, with latency, status, audio seconds, tokens and computed cost. Derive p50/p95 with Logs Insights or Embedded Metric Format (EMF). Add a **token-bucket limiter per vendor** (Sarvam REST 60 RPM, batch 20 RPM on PAYG). Use **exponential backoff with jitter** only on retryable codes (429, 503 and 5xx; never 402 or 4xx). Put a **per-witness circuit breaker** in front of each vendor so the job degrades to fewer witnesses. Cache by audio hash. CloudWatch is cheap at demo volume.

### Cited Findings
- **Sarvam retry semantics:** 429 `rate_limit_exceeded_error`. Retry 503 "like a 429, using fixed exponential backoff". **402 means credits are exhausted, so retrying won't fix it.** No Retry-After header is documented. Burst WebSocket opens can be rejected with close code 1003, [Sarvam rate limits](https://docs.sarvam.ai/api/getting-started/ratelimits)
- AWS guidance for throttled API calls: "Retry throttled requests using exponential backoff with jitter", [Lambda quotas page](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- OpenAI gpt-transcribe default limits start at 5,000 RPM (Build tier), so Sarvam's limits are the binding constraint, [OpenAI gpt-transcribe](https://developers.openai.com/api/docs/models/gpt-transcribe)
- **CloudWatch Mumbai prices:** log ingestion $0.67/GB (Standard class), log storage $0.03/GB-month, custom metrics $0.30/metric-month (first 10K), API requests $0.01 per 1K, [CloudWatch price list ap-south-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/ap-south-1/index.json). **X-Ray:** $5 per 1M traces stored after the free 100K, $0.50 per 1M traces accessed after the free 1M, [X-Ray price list ap-south-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSXRay/current/ap-south-1/index.json)
- The OpenTelemetry GenAI semantic conventions have moved out of the main semconv site into a dedicated repo, [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai), [opentelemetry.io notice](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- Vendor webhook retry policies (AssemblyAI: 10 attempts about 10 s apart, no retry on 4xx; Deepgram: 10 retries 30 s apart) are reference points for outbound retry budgets, [AssemblyAI](https://www.assemblyai.com/docs/deployment/webhooks); [Deepgram](https://developers.deepgram.com/docs/callback)
- S3 SigV4 presigned uploads can carry a SHA-256 checksum header, [S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html), which gives a server-verified content hash usable as a cache key.

### Inferences
- **Cost accounting:** keep a static price table in code (`sarvam_stt_inr_per_min=0.49`, `openai_gpt_transcribe_usd_per_min=0.0045`, `aws_transcribe_usd_per_sec=0.0001`, and the LLM's $/1M input and output tokens). After each call, emit `{"evt":"vendor_call","job_id","vendor","model","audio_s","in_tok","out_tok","latency_ms","status","retries","cost_usd"}` and aggregate per job into `cost.total_usd`. Show it in the demo UI, for example "this call cost ₹3.10 across 3 witnesses". Judges respond well to that.
- **Latency percentiles:** use CloudWatch Logs Insights, e.g. `filter evt="vendor_call" | stats pct(latency_ms,50), pct(latency_ms,95), count() by vendor`. You can also emit EMF so metrics appear without PutMetricData calls. Keep custom metrics to a handful at $0.30 each per month. A full OTel collector is optional. If you add it, use the GenAI convention attribute names so traces port later.
- **Rate limiting:** run an async token bucket per vendor and endpoint (`sarvam_rest: 1 req/s burst 5`, `sarvam_batch: 1 per 3 s`), shared within the single process. With more than one task you would need a DynamoDB- or Redis-backed limiter, so stay at one task for the demo.
- **Retries:** use `tenacity` or similar with full-jitter exponential backoff (base 0.5 s, cap 8 s, at most 3 attempts) on 429, 5xx and timeouts. **Never** retry 400, 401, 402 or 413. Give each attempt an explicit timeout, for example 25 s for Sarvam REST chunks and 60 s for OpenAI transcription of a few minutes of audio.
- **Circuit breaker and graceful degradation:** keep a per-witness breaker (open after 5 consecutive failures or more than 50% errors in 60 s, half-open probe after 30 s). The reconciler takes N≥1 witnesses: with 3, majority vote plus context; with 2, agreement plus contact gazetteer; with 1, context-only corrections at a raised confidence threshold. Mark the job `partial` with `degraded_witnesses`.
- **Caching:** key = `sha256(audio) + vendor + model + params`, mapped to the raw witness output in S3 (`cache/…`). Reconciliation key = `sha256(witness outputs) + context_hash + pipeline_version`. This replaces the on-disk cache, survives container restarts, and lets the demo replay instantly if a vendor is down at judging time. Expire the cache with an S3 lifecycle rule that matches the retention promise.
- **Budget guardrails:** set an AWS Budgets alert (for example $20), cap Sarvam credits, and add a per-user daily cap of audio minutes in the API that returns 429 with a clear message.
- **Log hygiene:** never log raw transcripts, phone numbers or contact names. Log token IDs and lengths only, and set Logs retention to 1 year for DPDP breach-detection logs while keeping log content minimal.

### Gaps
- The current stability status and exact attribute names of the OTel GenAI conventions were not retrieved.
- CloudWatch Application Signals and EMF pricing specifics were not retrieved.
- No published SLOs or uptime figures were found for Sarvam or OpenAI transcription endpoints.
- GPT model pricing for the reconciliation step was not researched.
