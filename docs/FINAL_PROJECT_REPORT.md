# Analytics-Driven Decision Support Framework for Enterprise Food Operations and Employee Health Management

## Final Project Report

**Course No.:** S1-26_MBAZG622T  
**Course Title:** Project  
**Student:** Shubham Kumar  
**BITS ID:** 2024HB21026  
**Program:** MBA in Business Analytics  
**Project Area:** Bangalore, Karnataka, India  
**Reporting date:** November 2026

> **Pagination note.** This document contains **60 explicitly numbered authored report pages**. The `<div class="page-break"></div>` markers separate the authored pages in compatible exports. Markdown alone cannot guarantee physical page dimensions; the actual rendered page count depends on the export tool, fonts, margins, table wrapping, and inserted diagrams. No PDF page count is claimed or fabricated.

> **Evidence labels used throughout:** **Code-inspected** means a claim was checked against the listed repository artifact; **user-reported** means the project owner described it but it was not independently exercised for this report; **proposed** means a management recommendation or target; **illustrative assumption** means a hypothetical input used only to explain a calculation. No field survey, production trial, financial return, model accuracy, or successful test execution is asserted.

<div class="page-break"></div>

## Page 01 - Report purpose, authorship, and decision lens

This final report presents the Enterprise Cafeteria Operating System (ECOS) as a management-oriented decision-support prototype for enterprise food operations and employee wellness. The report retains the approved project title, student, course, programme, project-area, and student identifier fields explicitly present in the user's mid-semester source. It expands the project framing into a final-stage management narrative: what operating problem is being addressed, how roles and processes could change, which controls would be needed, what evidence exists in the repository, and what must happen before any production or outcome claim is justified.

The central managerial question is not whether a dashboard can display many features. It is whether a coordinated service can make decisions more timely, explainable, and governable across menu planning, ordering, stock visibility, demand planning, employee choice, and management review. The application is treated as a prototype enabling that hypothesis to be examined. It is not treated as a proven operating intervention, a clinical tool, a validated forecast product, or a finance-verified business case.

The report uses a deliberately explicit evidence discipline. Repository documentation and source files support statements about interfaces, workflows, and implemented code. The owner has separately reported that an integrated demo works; this is recorded as user-reported context, not as this report's test result. Business benefits, financial cases, KPI targets, operating policies, governance designs, and deployment stages are recommendations or examples unless otherwise labelled. This separation is necessary for credible academic reporting and for responsible managerial decisions.

The intended audience includes project assessors, cafeteria and facilities managers, finance and procurement partners, employee representatives, IT and data-governance leaders, and the project owner preparing a demonstration. Each group can use the document differently: as a traceability record, a process-design proposal, a risk review, an evaluation plan, or a roadmap for a controlled pilot. The report therefore joins business reasoning with bounded technical evidence rather than allowing implementation detail to substitute for management analysis.

<div class="page-break"></div>

## Page 02 - Executive summary

ECOS addresses a recognizable enterprise-service problem: food-service decisions are often fragmented across menu lists, consumption histories, stock records, employee preferences, and manager judgement. When those information sources are disconnected, operators may struggle to coordinate a changing menu with anticipated demand, explain the basis of recommendations, or distinguish an attractive digital interface from a reliable operating capability. The approved project frames an analytics-enabled decision-support prototype for enterprise food operations and employee health management. Its seven stated objectives span operational analytics, menu intelligence, food-knowledge relationships, explainable decision support, supply-chain dependency analytics, nutrition-aware choice, and management communication.

The repository supports a narrower and more evidence-based final characterization. Code-inspected dashboard pages comprise five employee destinations—Home, Menu, My orders, My wellness, and Profile—and seven manager destinations—Today, Live orders, Inventory, Menu management, Forecasting, Executive, and Copilot. Menu modes include For you, Full menu, and Plan my day. Manager inventory views include Stock, Today's consumption, Edit stock, and Risk & impact. A CSV/XLSX template workflow is described as validating then committing edits, with movement history, affected dishes, and replenishment context. The employee demo payment path is explicitly described by the UI as taking no money. These are capabilities of a prototype, not proof of deployed service performance.

The model-training pipeline is implemented in code: it specifies a 200-tree RandomForestRegressor, depth 8, leaf minimum 2, deterministic seed 42, chronological service-date split of roughly 80/20, and comparison with a same-weekday-four baseline. It requires minimum usable history thresholds, and model serving is gated on the candidate model not exceeding baseline MAE. However, the presence of training code is not evidence that a trained artifact is active, that a forecast is accurate, or that a production model has been validated. The predictor can fall back when no active model or adequate history is available.

Management should proceed by instrumenting a bounded pilot, validating operational data and controls, measuring user adoption and service outcomes, and only then considering investment or scale. No survey sample, field result, realized savings, ROI, or test run is claimed here. The decision recommendation is therefore **advance to governed evaluation, not production-scale rollout**.

<div class="page-break"></div>

## Page 03 - Management decision brief

The immediate management decision is whether to use the current prototype as a structured demonstration and learning instrument, and whether to sponsor the next phase of evidence collection. The available evidence supports a positive answer to the first question: the UI and documented service boundaries can help stakeholders inspect an integrated operating concept. It does not yet support an unconditional business case, a service-level commitment, or an assumption that recommendations and forecasts will outperform existing practice.

The proposed decision is a staged authorization. First, continue demonstrations using synthetic or otherwise approved demo data and clear labels. Second, define one cafeteria, a short evaluation window, named process owners, a minimum data-quality checklist, privacy guardrails, and stop conditions before a live pilot. Third, collect baseline and post-change measures using the same definitions, without presenting a pilot association as causal impact unless a credible comparison design exists. Fourth, hold a go/no-go review with operations, finance, procurement, IT, privacy, and employee representation.

Three conditions should govern any pilot. **Operational safety:** a human manager remains responsible for confirming stock, menu changes, replenishment, and forecast-based actions; the software does not autonomously order from suppliers. **Information integrity:** menu, allergen, and nutrition statements require an accountable source and review cadence; displayed wellness indicators are not medical assessments. **Economic integrity:** demo order values are not audited revenue, mock payment is not cash collection, and any savings estimate is scenario analysis until reconciled with procurement and finance evidence.

The first executive dashboard should emphasize leading indicators and control health rather than headline growth. Useful early indicators include order completion, cancellation and stockout rates, inventory reconciliation variance, forecast coverage and error by relevant segment, menu-data completeness, user adoption by role, and open incidents. Targets must be set after baseline measurement and capacity review; none are invented in this report.

The decision brief is intentionally conservative. A well-governed experiment can still create substantial learning if results are neutral or unfavorable. By contrast, premature scaling could amplify data errors, employee distrust, waste, and false confidence in model outputs. The recommended managerial stance is therefore ambitious about learning, cautious about claims, and explicit about accountability.

<div class="page-break"></div>

## Page 04 - Contents and navigation

Use the page links below to navigate the 60 authored report pages. Page numbers identify authored sections in this Markdown source; they do not represent a guaranteed PDF page count.

1. [Report purpose and authorship](#page-01---report-purpose-authorship-and-decision-lens) · 2. [Executive summary](#page-02---executive-summary) · 3. [Decision brief](#page-03---management-decision-brief)
4. [Evidence, methods, and claim boundaries](#page-04---evidence-methods-and-claim-boundaries) · 5. [Project context and approved objectives](#page-05---project-context-and-approved-objectives) · 6. [Problem diagnosis](#page-06---problem-diagnosis-and-value-proposition)
7. [Stakeholder needs](#page-07---stakeholder-needs-and-influence) · 8. [Strategic fit](#page-08---strategic-fit-and-positioning) · 9. [Objectives and success criteria](#page-09---objectives-and-success-criteria)
10. [Scope and boundaries](#page-10---scope-boundaries-and-assumptions) · 11. [Employee experience](#page-11---employee-experience-and-service-design) · 12. [Manager experience](#page-12---manager-work-and-decision-rights)
13. [Service blueprint](#page-13---service-blueprint-and-operating-model) · 14. [Process redesign](#page-14---business-process-redesign) · 15. [Menu operations](#page-15---menu-portfolio-and-menu-governance)
16. [Inventory management](#page-16---inventory-control-and-waste-management) · 17. [Procurement](#page-17---procurement-and-supplier-operating-model) · 18. [Demand forecasting](#page-18---demand-planning-and-forecast-use)
19. [Forecast pipeline](#page-19---forecast-model-pipeline-and-readiness) · 20. [Forecast evaluation](#page-20---forecast-evaluation-and-interpretation) · 21. [Marketing and behaviour](#page-21---marketing-consumer-behaviour-and-choice-architecture)
22. [Wellness ethics](#page-22---employee-wellness-ethics-and-inclusion) · 23. [Data and information model](#page-23---data-and-information-management) · 24. [Architecture overview](#page-24---architecture-and-system-context)
25. [Modules and connections](#page-25---module-design-and-dependencies) · 26. [Order lifecycle](#page-26---order-lifecycle-and-service-recovery) · 27. [Decision support and copilot](#page-27---decision-support-and-copilot-boundaries)
28. [Architecture gap analysis](#page-28---architecture-gap-analysis) · 29. [Operations and service management](#page-29---operations-and-service-management) · 30. [Controls and risk matrix](#page-30---risk-and-control-matrix)
31. [Privacy and governance](#page-31---privacy-governance-and-responsible-data-use) · 32. [Analytics governance](#page-32---analytics-governance-and-model-oversight) · 33. [Management accounting](#page-33---management-accounting-and-cost-model)
34. [Investment appraisal](#page-34---investment-appraisal-with-hypothetical-inputs) · 35. [Benefits realization](#page-35---benefits-realization-plan) · 36. [Balanced scorecard](#page-36---balanced-scorecard)
37. [KPI dictionary: service and adoption](#page-37---kpi-dictionary-service-and-adoption) · 38. [KPI dictionary: analytics and control](#page-38---kpi-dictionary-analytics-and-control) · 39. [Project lifecycle](#page-39---project-management-lifecycle-and-quality)
40. [Evaluation protocol](#page-40---reproducible-evaluation-protocol) · 41. [Pilot design](#page-41---pilot-design-and-decision-gates) · 42. [Adoption and change](#page-42---adoption-and-change-management)
43. [Training and communications](#page-43---training-communications-and-feedback) · 44. [Risk register](#page-44---enterprise-risk-register) · 45. [Limitations](#page-45---limitations-and-threats-to-validity)
46. [Roadmap: first 90 days](#page-46---roadmap-first-90-days) · 47. [Roadmap: 3–12 months](#page-47---roadmap-three-to-twelve-months) · 48. [Managerial recommendations](#page-48---managerial-recommendations)
49. [Ownership and governance](#page-49---ownership-accountability-and-governance) · 50. [Demonstration plan](#page-50---viva-and-demo-plan) · 51. [Viva questions](#page-51---viva-preparation-and-defensible-answers)
52. [Traceability](#page-52---objective-to-evidence-traceability) · 53. [Process and control traceability](#page-53---process-to-control-traceability) · 54. [Evaluation worksheets](#page-54---evaluation-worksheets-and-data-contract)
55. [Formulas and assumptions](#page-55---formulas-assumptions-and-example-calculations) · 56. [Glossary](#page-56---glossary-and-interpretation-rules) · 57. [Source register](#page-57---project-evidence-register)
58. [Management literature](#page-58---management-literature-and-reference-notes) · 59. [Future research](#page-59---future-research-and-extension-criteria) · 60. [Conclusion](#page-60---conclusion-and-final-managerial-position)

<div class="page-break"></div>

## Page 05 - Evidence, methods, and claim boundaries

This report uses a documentary case-study approach. It combines the user's mid-semester report as the record of approved project framing and objectives, repository documentation as an implementation map, selected application files as evidence of visible workflows, and user-provided verified facts about model configuration and interface details. It does not conduct a new employee survey, interview, field observation, live API call, database query, production deployment, or independent end-to-end test. The scope was limited to the requested root-level project context, API documentation, entry point, dashboard modules, and model-training/prediction files. The backend source tree was not explored for this report; exhaustive backend audit work belongs to another task.

**Table 1. Evidence classification and permitted inference**

| Label | Evidence basis | What may be stated | What may not be inferred |
|---|---|---|---|
| Code-inspected | Named repository files | A workflow or configuration exists in source | It ran successfully in a target environment |
| Documented | [API_ENDPOINTS.md](../API_ENDPOINTS.md), API contract, project guide | A contract or documented design is described | A live service currently honors it |
| User-reported | Owner's explicit statement | A demo is reported to work; a fact is attributed to the owner | Independent verification, reliability, or scale |
| Proposed | This report's management design | A future practice or decision gate is recommended | Current production capability |
| Illustrative assumption | Hypothetical numeric example | A formula can be explained transparently | A forecast, saving, ROI, or field result |

The approved source identifies a primary project objective and seven more specific objectives. This report preserves that intent while distinguishing the approved aspirational scope from the implemented prototype. Every empirical statement is expected to have a named source, date or version, population or data window where relevant, and a reproducible extraction rule. When an element is unknown, the report records the gap rather than filling it with plausible-sounding figures.

The method is appropriate for a project report whose current evidence base is primarily design and implementation artifacts. It is not sufficient to establish causal wellness effects, consumer conversion, financial payback, or operational improvement. Those questions require the prospective evaluation plan later in this report.

<div class="page-break"></div>

## Page 06 - Project context and approved objectives

The approved mid-semester source names the project **“Analytics-Driven Decision Support Framework for Enterprise Food Operations and Employee Health Management.”** It describes a food-intelligence prototype connecting operational decisions and employee wellness. Its refined problem framing recognizes that nutrition information, recipe information, operational data, and employee choice are distributed across artifacts with different definitions and levels of completeness. The managerial difficulty is therefore not simply to put a recommendation algorithm in front of users; it is to improve the way the enterprise curates, connects, interprets, and acts on information.

The approved primary objective is to design and develop an analytics-driven decision-support framework that improves enterprise food operations and supports employee health management through predictive analytics and decision support. Seven objective themes are recorded in the source: operational analytics for preparation time and complexity; menu intelligence for similarity and substitution; a structured food knowledge graph across dishes, ingredients, nutrients, allergens, categories and other relationships; exploration of explainable decision support through Graph RAG; supply-chain dependency analytics; nutrition-aware employee recommendations and transparency; and an interactive dashboard for managerial communication.

The source expressly places Graph RAG in optional or exploratory scope and excludes it from completed-achievement claims. This is important because scope drift can make an academic project appear more complete than the artifact supports. The final project should be assessed against both intent and evidence: some themes can be realized as an interface or data workflow, some remain future extensions, and a stated objective does not automatically imply a production implementation.

**Table 2. Approved ambition translated into management questions**

| Objective theme | Managerial question | Evidence discipline |
|---|---|---|
| Operational analytics | Can planning be made more consistent? | Separate training code from validated operational prediction |
| Menu intelligence | Can choices and substitutions be explained? | Measure relevance and data coverage, not just display |
| Food relationships | Are ingredients and dietary attributes traceable? | Validate sources and allergen declarations |
| Explainable support | Can users understand why an insight appears? | Treat Graph RAG as exploratory unless verified |
| Supply dependencies | Which stock risks warrant attention? | Distinguish impact indicators from supplier procurement |
| Wellness | Can choice be informed without coercion? | Avoid clinical or employee-performance inference |
| Dashboard | Can each role act on relevant information? | Measure task completion and error rates prospectively |

The report uses the mid-semester source as an approved objective record, not as independent evidence of outcomes. See [MidSem_Report.docx](../MidSem_Report.docx).

<div class="page-break"></div>

## Page 07 - Problem diagnosis and value proposition

An enterprise cafeteria is a small but interdependent operating system. Menu changes affect ingredient needs; ingredient availability affects feasible substitutions; expected attendance and ordering behavior affect production; production decisions affect service waiting and leftover stock; consumer experience affects return behavior; and nutrition and allergen information affect trust and choice. When information sits in separate spreadsheets, point-of-sale records, recipe files, and informal communication channels, managers must reconcile these signals manually. The result can be duplicated effort, late exception discovery, inconsistent menu descriptions, and limited ability to explain why an operational choice was made.

The business problem should be stated as a coordination and decision-quality problem rather than as an assumed performance failure. No baseline wastage rate, stockout level, employee dissatisfaction score, revenue leakage, or preparation delay has been measured for this report. The proposition is that a common, role-appropriate information layer could make relevant information more visible and decision pathways more traceable. That proposition needs local evidence before benefits can be claimed.

The value proposition has two sides. For employees, it is convenient access to menu choices, order history, and declared dietary information, with recommendations that remain optional. For managers, it is a consolidated view of orders, stock, menu operations, historical behavior, and planning indicators that can structure review. The value is not “AI” as an end in itself: it is fewer avoidable information handoffs, better exception visibility, and more disciplined follow-up—if the data and process controls are trustworthy.

**Figure 1. Enterprise food-service value chain (planned diagram).** [Management value chain diagram](assets/management-value-chain.svg) is a planned authored diagram, not a screenshot. It should show demand signals → planning → menu and procurement coordination → preparation and service → employee feedback → review and learning. The figure is a conceptual map; it is not evidence that every link is automated.

A sound diagnosis starts by interviewing process owners and observing the current-state work before changing it. The team should map how a menu is approved, how a stock discrepancy is resolved, when production quantities are committed, how substitutions are communicated, and how an employee corrects an order. The prototype can then be assessed against verified friction points rather than a generic narrative about digital transformation.

<div class="page-break"></div>

## Page 08 - Stakeholder needs and influence

The platform's intended value depends on several stakeholder groups whose incentives do not always align. Employees want convenient choice, reliable availability, accurate descriptions, clear pricing, and confidence that dietary information is handled respectfully. Cafeteria supervisors need a timely operational picture, manageable exceptions, and practical authority to correct bad data. Menu planners need an approval process that balances variety, nutritional considerations, cost, ingredients, and kitchen capacity. Procurement and suppliers need dependable specifications, order quantities, lead times, and change notices. Finance needs reconciled costs and transparent assumptions. IT and data-governance teams need controlled access, supportability, privacy safeguards, and evidence of readiness. Employee representatives need clarity that wellness indicators will not become a mechanism for monitoring or discrimination.

Stakeholder engagement should be designed around decisions, not around an undifferentiated request for feedback. For each group, specify the question, evidence, and decision it can influence. Employees can review menu clarity and discoverability; operators can test whether stock and order views match their shift routines; procurement can validate how a proposed replenishment suggestion would be translated into an actual request; finance can approve cost definitions; privacy and HR can review the boundaries of wellness data; and IT can define service and recovery requirements.

**Table 3. Stakeholder influence and engagement**

| Stakeholder | Primary need | Decision right to clarify | Engagement evidence |
|---|---|---|---|
| Employee | Choice, trust, accurate menu data | Consent, preference settings, feedback route | Usability session; no claimed sample yet |
| Shift manager | Fast exception handling | Hold, amend, or reject an operational suggestion | Observed task walk-through |
| Menu owner | Feasible menu and substitutions | Approve publication and recipe version | Menu change log |
| Procurement | Actionable specification and supplier timing | Approve supplier-facing order | Requisition and approval record |
| Finance | Auditable costs and benefit logic | Validate accounting definitions | Reconciliation and sign-off |
| IT/privacy | Secure, supportable service | Approve deployment and data access | Readiness review |
| Employee representative | Fair, non-coercive use | Escalate unacceptable wellness practice | Governance meeting notes |

A responsible design makes disagreement visible. An employee might prioritize price while a menu planner prioritizes variety; a manager might prioritize stock availability while wellness communication emphasizes a healthier option. The system should present relevant trade-offs and provide a clear human decision owner rather than hiding value choices inside an opaque score. Stakeholder acceptance is not a one-time sign-off: needs, operating conditions, and trust can change over time.

<div class="page-break"></div>

## Page 09 - Strategic fit and positioning

Strategy is a set of choices and trade-offs, not an inventory of features. ECOS can be positioned as a decision-support layer that helps a cafeteria coordinate employee-facing service and manager-facing operations. It should not be positioned as a replacement for established procurement systems, a medical intervention, or an autonomous production planner. This narrower position aligns the prototype to a manageable strategic question: can integrated, role-specific information improve service coordination and management learning without creating disproportionate privacy, operational, or financial risk?

Porter's distinction between operational effectiveness and strategy is useful here. A digital interface may make existing processes faster, but sustainable value depends on choosing a distinct activity system that fits the organization's service model and capabilities. The proposed activity system includes reliable menu stewardship, accessible employee choice, timely order visibility, disciplined inventory review, forecast-informed human planning, and recurring performance review. If any element is missing—for example, if stock data is stale or no one owns menu attributes—the dashboard can make a weak process more visible without making it better.

The strategic intent should therefore be expressed as a hypothesis with testable conditions: *if* managers have timely, sufficiently complete information and clear decision rights, *then* they can assess demand, stock, and menu choices more consistently; *if* employees see accurate information and retain choice, *then* trust and convenience may improve. Both links require measurement. Technology availability is not the same as adoption, and adoption is not the same as an improved outcome.

**Table 4. Strategic choice and trade-off**

| Choice | Benefit sought | Trade-off to manage |
|---|---|---|
| Decision aid, not autopilot | Human judgement remains accountable | Requires manager time and training |
| Optional recommendations | Preserves employee autonomy | Lower click-through may be appropriate |
| Phased service scope | Makes controls tractable | Some manual handoffs remain |
| Transparent food attributes | Supports informed choice | More stewardship work and uncertainty disclosure |
| Evidence-led scaling | Limits premature commitment | Slower visible expansion |

The recommendation is to evaluate ECOS as a complement to the organization's operating model. Before positioning the product externally or using it to justify investment, management should confirm that the target cafeteria's strategy, service promise, labor arrangements, procurement rules, and data environment fit this activity system.

<div class="page-break"></div>

## Page 10 - Objectives and success criteria

Objectives should distinguish deliverables, operational outcomes, and longer-term impacts. A screen or API endpoint is a deliverable. A lower reconciliation delay or higher menu-data completeness is an operational outcome. Improved employee well-being or reduced environmental waste is a possible impact requiring a stronger design and longer time horizon. Conflating these levels encourages teams to claim impact from implementation progress.

**Table 5. Objective hierarchy for the next evaluation stage**

| Level | Example objective | Evidence needed |
|---|---|---|
| Deliverable | Provide role-specific menu, order, inventory, and planning views | Versioned build; acceptance criteria |
| Process outcome | Make exceptions visible to the responsible manager | Timestamped queue and disposition records |
| Service outcome | Improve order completion or availability | Defined denominator and baseline |
| Resource outcome | Improve stock planning or reduce avoidable leftovers | Physical counts and waste measurement |
| Employee outcome | Support informed, voluntary menu choice | Privacy-safe, non-coercive measurement |

The approved project objectives should be mapped to evidence and status in the traceability appendix. For the present report, “implemented” means code-inspected capability only when linked to a source file. “In progress” can describe a pipeline present in code but not an evaluated artifact. “Exploratory” identifies a concept that requires research or further implementation. “Not evidenced” means the current evidence set does not establish completion; it does not prove that no work exists elsewhere.

Each objective should be converted into a SMART measure only after the local baseline, data availability, operational constraints, and accountable owner are known. A target chosen before those conditions are measured is a management aspiration, not a forecast of likely performance. The pilot charter should state the metric formula, observation window, unit of analysis, inclusion rules, data source, owner, review frequency, and a guardrail metric. For example, an order-completion target should be balanced with cancellation and substitution rates so that apparent completion does not mask poor customer experience.

Success is multi-dimensional. A pilot that improves planning but increases employee concern about data use may not be acceptable. A recommendation that receives many clicks but fails to convert into completed, available orders may not create commercial value. A model that has lower aggregate error but fails on a high-impact meal period may not be operationally useful. The evaluation must define non-negotiable quality and fairness conditions alongside outcome objectives.

<div class="page-break"></div>

## Page 11 - Scope, boundaries, and assumptions

The current report treats ECOS as a prototype with employee and manager role experiences, documented API boundaries, menu and order workflows, inventory views, forecasting and executive views, and a read-only copilot interface. A user has reported an integrated demo is working; the report does not independently verify runtime state. No live service or database was contacted. The report makes no assumption that a target architecture diagram is identical to current implementation.

The distinction between the approved vision and present evidence matters. The approved outline includes knowledge graph and Graph RAG themes, but the mid-semester source describes Graph RAG as optional and expressly excludes it from completed achievements. The current copilot should be described as rule-based and read-only by default, not as an LLM agent. Qdrant is an optional enrichment path with catalog dependencies; it is not a guaranteed central runtime component. The application uses synchronous PyMongo rather than Motor. These details constrain both architecture narratives and deployment expectations.

The following assumptions are for planning only: a cafeteria has an accountable menu owner; staff can review stock and service records; operating hours and meal periods are known; approved menu and ingredient information can be maintained; and employees can use a digital interface or receive an equivalent service. Each must be confirmed at a pilot site. The data may not represent seasonal patterns, holidays, special events, supplier disruptions, or changes in attendance.

**Table 6. Scope boundary**

| Included as current evidence | Not assumed as delivered |
|---|---|
| Role-specific dashboard pages and API mapping | 10 independently complete, production-grade modules |
| Inventory edit workflow with validation-before-commit description | Full enterprise inventory accounting |
| Forecast user interface and training pipeline code | Active, accurate, continuously monitored model |
| Demo checkout copy and order-value display | Cash revenue, payment settlement, or audited sales |
| Simplified replenishment context | Supplier master, purchase-order approval, or supplier transmission |
| Rule-based read-only copilot behavior | General-purpose generative AI or autonomous actions |

Scope changes should be authorized through a change log that records the new requirement, business owner, user impact, data need, control impact, effort estimate, acceptance test, and displaced priority. This prevents a widening feature list from silently weakening the evidence quality or the project’s management focus.

<div class="page-break"></div>

## Page 12 - Employee experience and service design

The employee experience is the demand-facing side of the service. Code-inspected dashboard configuration identifies five employee pages: Home, Menu, My orders, My wellness, and Profile. Menu modes are For you, Full menu, and Plan my day. These interface groupings suggest a user journey from discovering choices through placing and reviewing an order, but actual usability, comprehension, and task success have not been independently measured for this report.

The design opportunity is to make the service clear at the moment of choice. Employees need to know what is available, how much it costs, whether declared dietary and allergen information is complete, what the recommendation means, whether the order is committed, and what to do if a dish is unavailable. The UI's demo payment message states “no money is taken.” That wording is a useful safeguard, but a production service would need a separate approved payment design, clear price and refund rules, and reconciliation controls. It must not be interpreted as evidence that the present prototype collects money.

Personalization should be explainable, adjustable, and optional. “For you” can be useful when the employee understands why an item appears and can easily reset or ignore preferences. It can become intrusive if it uses sensitive inferred characteristics, creates persistent health labels, or makes one option appear institutionally endorsed. A default should not quietly convert into a prescription. Full menu access must remain visible, and the interface should not penalize users who choose differently.

The wellness page should explain its limits next to any score. Verified UI facts indicate that the monthly score uses collected orders only, starts at a baseline of 20, adds 10 for a healthy portion and 5 for another qualifying rule, and is capped at 100; pending orders do not count. The exact interpretation and content of “healthy” must be documented and reviewed. This score is not a clinical outcome, a diagnosis, or a measure of an employee's overall diet.

**Proposed employee-service principles:** clear availability; accessible language and interaction; transparent price and dietary data; accessible non-personalized alternatives; easy correction and support; and no employment consequence from wellness participation. These principles should be tested through task-based sessions and employee representation before pilot release.

<div class="page-break"></div>

## Page 13 - Manager work and decision rights

Managers operate the service under changing conditions: demand surprises, menu substitutions, deliveries, staff capacity, data quality issues, and employee escalations. The dashboard identifies seven manager destinations—Today, Live orders, Inventory, Menu management, Forecasting, Executive, and Copilot. This segmentation is useful because managers need both an operational “now” view and a planning or review view. The repository confirms that named UI views exist; it does not establish how frequently managers will use them, whether all data refreshes meet a service standard, or whether tasks are more efficient.

Decision rights must accompany each view. Who may pause an item when availability is uncertain? Who can amend a menu description? Who reviews stock discrepancies? Who can change a planning assumption? Who confirms a forecast-informed production quantity? Who approves a replacement ingredient and checks allergen implications? A dashboard without accountable decision owners creates an attractive observation layer but can leave exceptions unresolved.

**Table 7. Recommended manager decision-rights matrix**

| Decision | Responsible operator | Accountable owner | Required check |
|---|---|---|---|
| Mark item temporarily unavailable | Shift lead | Cafeteria manager | Confirm physical stock and inform employees |
| Amend published menu | Menu steward | Operations owner | Verify price, ingredients, allergens, effective date |
| Commit stock adjustment | Authorized stock editor | Inventory owner | Reconcile against source evidence |
| Use forecast as planning input | Planner/manager | Operations owner | Review coverage, baseline, exceptions, and capacity |
| Create supplier request | Procurement | Procurement approver | Apply delegated authority and supplier terms |
| Resolve employee issue | Service desk or manager | Employee-service owner | Record resolution and protect personal data |

The inventory interface includes Stock, Today's consumption, Edit stock, and Risk & impact tabs. The described CSV/XLSX workflow validates data before commit and provides movement history, affected dishes, and replenishment context. This is potentially valuable because validation and impact visibility can reduce silent changes. Still, the authorization model, concurrency behavior, physical-count process, rollback, and audit retention should be verified before real stock records depend on the feature.

Managers need a concise operating cadence: start-of-shift exception check; pre-service availability confirmation; in-service issue handling; end-of-service reconciliation; and weekly review of demand, inventory, menu, and feedback signals. The cadence should fit actual labor and service rhythms rather than imposing another dashboard task. Each recurring review should produce a named decision, owner, due date, and follow-up status.

<div class="page-break"></div>

## Page 14 - Service blueprint and operating model

A service blueprint joins customer-facing actions, backstage work, support systems, and evidence. It is useful for ECOS because a successful employee transaction depends on more than a button click: the menu must be current, stock must be credible, order events must be interpreted, and someone must resolve service exceptions. A blueprint can expose the points at which information or authority is missing.

**Figure 2. Management value-chain blueprint (planned diagram).** The planned [management value-chain diagram](assets/management-value-chain.svg) should distinguish employee touchpoints from kitchen and management activity. It is an authored conceptual diagram, not a screenshot, and must not imply that every handoff is automated.

**Table 8. Draft service blueprint**

| Stage | Employee-facing action | Backstage work | Evidence/control |
|---|---|---|---|
| Discover | Browse menu and optional recommendations | Maintain dish, price, ingredient and availability records | Versioned menu and attribute owner |
| Select | Review item and declared information | Check available quantity and current substitutions | Availability timestamp and review |
| Commit | Confirm demo order | Record order state and trigger operational visibility | Idempotent event and clear confirmation |
| Prepare | Wait for fulfillment | Kitchen sequences work and manages exceptions | Status history and escalation owner |
| Collect/resolve | Receive order or contact support | Manager handles missing item, delay, or substitution | Resolution code and service recovery log |
| Learn | Review history and provide optional feedback | Aggregate behavior and plan future service | Privacy-minimized analytics |

For each step, the operating model should specify the service owner, frontline role, data steward, technology support contact, escalation threshold, and fallback if the service is unavailable. A manual fallback is not a failure; it is part of a resilient service. For example, managers may need an approved printed or shared menu and a documented stock update process when the dashboard is down.

The employee journey should not expose internal operational complexity, but it should communicate meaningful uncertainty. If an item is at risk of running out, the interface should not promise availability beyond what the operator can support. Conversely, managers should not see a “risk” indicator without knowing its data timestamp, rule, and expected action. The service blueprint turns those presentation decisions into explicit requirements for ownership, service behavior, and evidence.

This operating model is a proposal for a pilot workshop, not a claim that the current application already provides all event histories, fallback workflows, or service-level monitoring described above.

<div class="page-break"></div>

## Page 15 - Business process redesign

Process redesign should remove unnecessary handoffs while retaining the controls required for safety, fairness, and financial integrity. ECOS is an opportunity to standardize how the cafeteria publishes menus, confirms availability, reviews demand, updates inventory, and communicates changes. It should not merely digitize a fragmented process without asking whether tasks can be clarified, consolidated, or retired.

Begin with a current-state map based on observation and staff interviews. Record the input, trigger, actor, decision, system or artifact used, waiting time, rework, and customer-facing consequence for each step. Then classify each friction point as a data problem, policy problem, capacity problem, interface problem, or ownership problem. This classification prevents a software change from being used to conceal a root cause that is actually an unclear approval policy or an unreliable source record.

**Table 9. Proposed future-state control points**

| Process | Redesign principle | Control that must remain |
|---|---|---|
| Menu publication | One stewarded record and effective date | Approval of price, ingredients, and declarations |
| Availability updates | Prompt, role-based exception update | Physical confirmation and update attribution |
| Inventory adjustment | Validate, preview impact, then commit | Authorized user, reason, history, reconciliation |
| Demand planning | Compare forecast and baseline with judgement | Manager override and reason capture |
| Substitution | Make affected dishes and attributes visible | Re-check allergen and dietary disclosure |
| Feedback review | Summarize themes at appropriate aggregation | No punitive use of identifiable health signals |

The UI-described edit flow—CSV/XLSX template, validation, then commit—can support a two-step process in which a user previews errors before changing stock. The process should also define how duplicate uploads, stale templates, partial failures, corrections, and concurrent edits are handled. Each of these is a test case for the pilot, not a verified property inferred from the presence of a screen.

Process measures should capture both speed and quality. A shorter update time is not an improvement if it increases incorrect quantities. A higher number of menu changes is not inherently good if employees cannot rely on descriptions. A lower stock balance may reflect reduced overstock or merely under-recording. Establish a balanced measure set, perform regular sample-based reconciliation, and discuss exceptions in the operational review rather than rewarding a single metric in isolation.

The redesign owner should document the current and future process side by side, including training, manual fallback, responsibility changes, control evidence, and unresolved constraints. This will make the management contribution assessable independently of the code.

<div class="page-break"></div>

## Page 16 - Menu portfolio and menu governance

Menu management is a portfolio decision. A menu must balance employee preference, affordability, nutritional transparency, ingredient availability, kitchen capability, supplier lead times, cultural inclusion, and margin requirements. No single ranking formula should resolve these value choices without an accountable menu owner. The employee interface offers For you, Full menu, and Plan my day modes; managers have a Menu management page. These are useful interaction points, but the quality of the service depends on stewardship of the underlying menu attributes and decision rules.

Menu governance should define a standard dish record: stable identifier; customer-facing name; category; serving period; price; recipe or ingredient reference; declared allergens; dietary tags; source and effective date; availability status; portion definition; and owner. Changes should be versioned. A substitution is not just a supply decision; it can alter ingredient, allergen, nutritional, cost, and consumer-expectation information. The system should preserve the history of what was published at the time an order was placed.

**Table 10. Menu portfolio dimensions**

| Dimension | Management question | Example review evidence |
|---|---|---|
| Demand | Which options are selected and completed? | Orders, cancellations, availability, period |
| Coverage | Are segments and meal periods adequately served? | Menu mix and employee feedback |
| Nutrition transparency | Are declared attributes sourced and current? | Steward sign-off and source record |
| Economics | Are price and ingredient costs understood? | Finance-approved cost model |
| Operations | Can the kitchen prepare consistently? | Capacity, prep-time observations, exception log |
| Resilience | Can a dish be substituted safely? | Approved alternatives and ingredient dependency |

Menu similarity or redundancy analytics should inform discussion rather than automatically remove an item. Two dishes that look similar may serve different cultural or dietary needs; conversely, superficially different dishes may share a critical ingredient. Portfolio review should include an explanation of the comparison basis, relevant attributes, and data coverage. A manager should be able to override an automated suggestion and record why.

Allergen declarations require particular care. The UI's disclaimer says nutrition values are estimates and declared allergens are not a cross-contact guarantee. This limitation should be displayed at the point of decision, and the operating process must provide a route for employees to seek authoritative clarification. Where the source data cannot support a confident declaration, a clearly marked unknown is safer than a fabricated certainty.

<div class="page-break"></div>

## Page 17 - Inventory control and waste management

Inventory policy should link demand, menu design, shelf life, replenishment lead time, storage capacity, and physical control. ECOS exposes manager inventory tabs for Stock, Today's consumption, Edit stock, and Risk & impact. The described interface supports validation-before-commit CSV/XLSX edits, movement history, affected-dish information, and replenishment context. This creates a foundation for more disciplined review but does not establish a complete inventory ledger or an optimized replenishment policy.

An operating inventory process needs a clear definition of the stock quantity being shown: on hand, available to promise, reserved, in transit, or estimated consumption. Units of measure must be standardized; a case, kilogram, portion, and recipe quantity cannot be compared without explicit conversion rules. Each adjustment should identify the user, time, item, quantity, unit, reason, and source evidence. Periodic physical counts should be compared with system balances, and variance should trigger investigation rather than automatic overwrite.

**Table 11. Inventory management controls**

| Risk condition | Preventive/detective practice | Decision owner |
|---|---|---|
| Stale stock record | Timestamp and regular count cadence | Inventory owner |
| Unit mismatch | Controlled item master and conversion review | Data steward |
| Unapproved adjustment | Role authorization and reason code | Operations manager |
| Duplicate import | File/version identifier and preview validation | Authorized editor |
| Hidden substitution risk | Show affected dishes and attributes | Menu steward |
| Waste not captured | Standard reason and quantity capture | Shift lead |

“Risk & impact” can be a valuable view if the risk score is interpretable. Managers need to know whether a high score reflects low balance, high expected usage, lead-time uncertainty, or an ingredient's dependency across many dishes. Ingredient criticality may be represented as a simple operational rule, but it should not be presented as a probability of stockout unless calibrated and validated against historical outcomes.

Waste reduction is a plausible benefit area, not a result established here. To evaluate it, define edible waste, preparation waste, spoilage, and post-service surplus separately; measure quantities using a consistent method; note menu and attendance context; and avoid treating lower recorded waste as lower actual waste without audit. Inventory improvements should be balanced against service availability: leaner stocks can reduce holding cost but increase the likelihood of unavailable items.

The recommended operating policy is human-approved, exception-driven replenishment with clear minimum/maximum assumptions and documented override. No autonomous supplier order or end-to-end procurement workflow is evidenced.

<div class="page-break"></div>

## Page 18 - Procurement and supplier operating model

Procurement converts a planning signal into a binding commercial action. The project documentation labels procurement as simplified. The described prototype does not provide a complete supplier master or purchase-order workflow. Therefore, a replenishment indicator, ingredient-risk display, or manager decision to restock must not be described as a supplier order, approved commitment, or procurement integration.

Before any procurement process is connected, management needs a governed item and supplier master, approved vendor status, contractual terms, unit-price history, lead times, minimum order quantities, delivery calendars, substitutions, approval authority, and invoice-matching procedures. The process must distinguish a forecast quantity, a suggested requirement, a requisition, an approved purchase order, a supplier acknowledgement, a receipt, and an invoice. Those states have different legal, operational, and financial meaning.

**Table 12. Procurement maturity ladder**

| Stage | Capability | Evidence required to progress |
|---|---|---|
| 1. Visibility | Show stock and consumption context | Reconciled item and unit definitions |
| 2. Suggested action | Present a replenishment scenario | Documented assumptions and human review |
| 3. Requisition | Create an internal request | Approval workflow and duplicate prevention |
| 4. Purchase order | Commit through authorized procurement | Supplier master, terms, approvals, audit trail |
| 5. Receipt and match | Record delivery and invoice | Quantity/price match and discrepancy resolution |

The system should make uncertainty explicit. A suggested replenishment quantity may be sensitive to unobserved event demand, lead-time variability, spoilage, or menu substitutions. Managers should see the assumptions and be able to adjust or defer an action. Procurement staff should be able to reject an inappropriate suggestion without losing the underlying planning evidence.

The commercial evaluation should consider total cost of ownership, not only unit price. Relevant elements include order minimums, delivery frequency, handling, storage, spoilage, emergency purchases, contract flexibility, and the labor required to review exceptions. Supplier collaboration may help improve data quality and availability, but it also increases integration and governance complexity.

The recommended next step is a process workshop with procurement and finance to draw the actual requisition-to-payment workflow and map ECOS concepts to it. Until that work is complete, the report treats procurement as a simplified decision-support view only. It makes no claim that suppliers are connected or that purchasing savings have been realized.

<div class="page-break"></div>

## Page 19 - Demand planning and forecast use

Forecasting is valuable only when a forecast is linked to a decision, a time horizon, and an accountable owner. The manager Forecasting interface allows a 0–30% buffer, dates, and meal periods, and supports model retraining. The existence of those controls makes it possible to explore different planning inputs; it does not prove that the resulting forecast is accurate or that a particular buffer is optimal.

A forecast should be understood as one estimate among several signals. The manager should consider historical demand, expected attendance, event calendars, menu changes, availability constraints, weather or local conditions where appropriate, and operational capacity. The system must identify the forecast horizon and unit (for example, order count or servings) and indicate when the underlying history is sparse or structurally changed. The 0–30% buffer is a user-controlled planning parameter, not a statistically estimated confidence interval unless the model explicitly defines it that way.

**Table 13. Forecast-to-action decision record**

| Decision field | Required interpretation |
|---|---|
| Forecast quantity | Predicted demand for a stated dish/period/date and unit |
| Baseline quantity | Comparable reference, such as same-weekday history |
| Buffer | Explicit operational uplift; owner and rationale recorded |
| Constraints | Stock, staff, preparation time, menu availability |
| Manager decision | Adopt, adjust, or override; reason captured |
| Realized outcome | Observed order/consumption measure using same definition |

The appropriate objective depends on the cost of errors. Under-forecasting may create stockouts or missed service; over-forecasting may contribute to surplus and waste. Those costs vary by dish, shelf life, event importance, and substitution options. A single aggregate error metric cannot encode all such trade-offs. Managers should review forecast performance by meal period and item category, with minimum sample-size safeguards and clear exception flags.

Forecasts should be compared with a simple baseline. If a complex model does not consistently improve the decision-relevant performance over an uncomplicated reference, management should prefer the simpler approach or continue a controlled trial. Model availability must not be treated as an instruction to follow the prediction. The operator retains responsibility for production quantities and should be able to record contextual information that the model does not capture.

The proposed governance loop is: forecast; inspect data coverage; compare to baseline; review constraints; decide with a human; observe outcome; investigate error; and retrain only under a documented policy. This is an operating discipline, not merely a model endpoint.

<div class="page-break"></div>

## Page 20 - Forecast model pipeline and readiness

The verified model-training facts supplied for this report describe an implemented training pipeline in `ml/train.py`. It uses a 200-tree `RandomForestRegressor`, maximum depth 8, minimum leaf samples 2, and random seed 42. It sorts service dates chronologically and uses an approximately 80/20 split. The pipeline evaluates the candidate against a same-weekday-four baseline using MAE and WAPE. Minimum usable history is 12 customer and 20 dish rows across at least five dates. Candidate serving is gated so the model is active only if its MAE does not exceed the baseline MAE; the recorded metadata includes `demo_order_share`. The sklearn version must match for the intended model-artifact compatibility.

These are code/configuration facts, not model-performance results. This report has not inspected or executed a training run, checked whether an active artifact exists, confirmed training-data provenance, measured a test-set score, or reviewed a deployment manifest. A configured threshold is not proof that the threshold was met. “Retrain models” in the UI is a control affordance; production readiness requires permissions, job lifecycle, artifact approval, monitoring, rollback, and traceability.

The predictor in `ml/predictor.py` can use fallback logic when no active model or sufficient history is available. Fallback is a resilience behavior, but it must be visible to the operator. A user should know whether a displayed number comes from an active candidate model, historical rule, or fallback. If the interface does not currently make this distinction, it should be added before a pilot relies on the forecast.

**Table 14. Minimum readiness evidence before forecasting influences production**

| Readiness area | Required artifact |
|---|---|
| Data | Versioned source, data dictionary, date range, inclusion/exclusion rules |
| Evaluation | Chronological holdout results by relevant segment, baseline comparison |
| Operational | Forecast horizon, unit, buffer meaning, manager override process |
| Model governance | Artifact ID, dependency versions, approver, activation date, rollback |
| Monitoring | Coverage, drift indicators, error review cadence, escalation threshold |

The same-weekday-four baseline should be precisely specified: what four observations are selected, how missing days are handled, whether the comparison uses only information available at forecast time, and whether splits avoid leakage. The term “same weekday” may conceal different meal periods, holidays, or menu availability. Evaluation should be performed before choosing a serving threshold and should preserve the original temporal sequence.

For the source-level evidence, see [ml/train.py](../ml/train.py) and [ml/predictor.py](../ml/predictor.py). No active trained artifact or performance score is claimed.

<div class="page-break"></div>

## Page 21 - Forecast evaluation and interpretation

Forecast evaluation must answer two different questions: does the model estimate demand more accurately than a useful reference, and does using the estimate improve the decision under the cafeteria's real constraints? The first is a statistical question; the second is an operational and economic question. A model can reduce average error while still causing costly misses on high-impact items, or perform well offline but fail when menu availability, attendance, or data capture changes.

The pipeline records MAE and WAPE in comparison with a same-weekday-four baseline. MAE is the average absolute difference between observed and predicted values in the forecast unit. WAPE divides the sum of absolute errors by the sum of actual values, usually expressing the result as a percentage when the denominator is nonzero. Each has interpretation limits: MAE is scale-dependent and does not indicate the direction of error; WAPE can be unstable when total actual volume is low and can hide subgroup performance. Both should be shown alongside sample counts, coverage, signed bias, and a clear statement of the test window.

**Table 15. Evaluation questions and management response**

| Question | Evidence | Possible response |
|---|---|---|
| Is the evaluation chronological? | Split dates and feature-time rules | Redesign split if future information leaks |
| Is there enough history? | Rows and service dates by segment | Defer or pool only with justified comparability |
| Does model beat baseline? | Holdout MAE/WAPE and uncertainty | Keep baseline if results are inconclusive |
| Are misses asymmetric? | Over/under error and cost context | Adjust planning rule, not hide error |
| Is fallback observable? | Output source and status | Label fallback; restrict use if ambiguous |
| Does use help operations? | Pilot decisions and realized outcomes | Expand only after controlled evidence |

Minimum thresholds in the training code are eligibility checks, not guarantees of statistical power. Twelve customer rows, twenty dish rows, and five dates can satisfy a technical gate while still providing little evidence for rare events, seasonal changes, or subgroup differences. The evaluation report should show how much data each segment contributes and avoid presenting a global result as universal.

The model's recorded `demo_order_share` metadata should be interpreted and documented. If it indicates the share of demonstration orders or any synthetic/demo-origin component, evaluation must distinguish demo behavior from operational demand. No model accuracy or performance result is reported here because none was independently verified.

<div class="page-break"></div>

## Page 22 - Marketing, consumer behaviour, and choice architecture

An employee-facing menu interface is also a marketing channel. Ordering patterns may be influenced by availability, perceived price, descriptive wording, social context, default placement, recommendations, convenience, and the timing of the decision. A “For you” placement can improve discovery, but it can also shape attention. Responsible marketing therefore asks not only whether a feature increases interaction, but whether it gives employees a fair, understandable choice and whether the business outcome is measured correctly.

Recommendation share is not true conversion. A click, view, or share of recommendation exposure does not prove that the employee selected the item, completed the order, received it, consumed it, or would not have selected it without the recommendation. A credible funnel distinguishes exposure, engagement, selection, committed order, fulfilled order, cancellation, substitution, and repeat behavior. Each stage needs a consistent event definition and privacy-appropriate aggregation.

**Table 16. Consumer-behavior measurement ladder**

| Stage | Example measure | Interpretation boundary |
|---|---|---|
| Visibility | Recommendation impression count | Exposure opportunity only |
| Interest | Detail view or save | Attention, not purchase intent |
| Selection | Item added or chosen | May still be abandoned |
| Commitment | Order confirmed | Not necessarily fulfilled or paid |
| Fulfillment | Order completed | Does not establish consumption |
| Repeat | Return selection over time | Association, not causal loyalty |

Marketing tests should be pre-registered where feasible: specify the hypothesis, eligible audience, treatment and comparison logic, guardrails, observation window, and decision threshold. A/B tests in a workplace context require particular care. Employees may not have equal exposure; managers may influence participation; a supposedly “personalized” offer could disclose inferred preferences. Opt-out and a visible full-menu alternative should remain available.

The business should avoid health-based pressure tactics such as shame, ranking, or rewards that make employees feel monitored. Menu labels should be factual and sourced; claims such as “healthy,” “high protein,” or “recommended” require transparent criteria. If the interface uses a wellness score, marketing communication must not imply that the score represents medical advice or a complete diet assessment.

Price and availability effects can confound recommendation performance. If an item appears more often because it is cheaper or reliably in stock, its higher selection share cannot be attributed solely to personalization. Analytics should segment by price, exposure, meal period, and availability, while limiting data collection to what is needed. The objective is informed choice and reliable service, not maximizing clicks at any cost.

<div class="page-break"></div>

## Page 23 - Employee wellness, ethics, and inclusion

Workplace wellness analytics operate in a sensitive setting because the employer-employee relationship contains an inherent power imbalance. Even a well-intentioned feature may feel compulsory if a manager can see identifiable choices or if employees believe participation affects performance review, access to benefits, or workplace standing. ECOS should therefore treat wellness information as a voluntary service signal with strict purpose limits, not as a workforce-management score.

The UI describes a monthly score based only on collected orders: baseline 20, plus 10 for a qualifying healthy portion and 5 for another qualifying rule, capped at 100; pending orders do not count. This is a rule-based prototype indicator, not a medical assessment. The rubric, definitions, and evidence supporting labels should be disclosed. A score built from cafeteria orders cannot represent food consumed elsewhere, dietary needs, health status, affordability, fasting, cultural practice, or a person's overall well-being. Absence of data must not be interpreted as a negative wellness outcome.

The interface disclaimer distinguishes estimates from measured nutrition and states that declared allergens do not guarantee absence of cross-contact. That nuance should remain prominent and accessible at the point of choice. A production process should include source provenance, review dates, version history, correction mechanisms, and an escalation route for employees who need authoritative clarification. If the kitchen cannot verify cross-contact controls, it should not imply a guarantee.

**Table 17. Ethical guardrails**

| Principle | Required practice |
|---|---|
| Voluntariness | No penalty for non-use or opting out |
| Purpose limitation | No repurposing for performance or discipline |
| Minimization | Collect the minimum needed; aggregate wherever possible |
| Transparency | Explain scoring, limitations, and data sources |
| Inclusion | Preserve full choice across dietary, cultural, and access needs |
| Contestability | Enable correction and human review |
| Non-clinical boundary | No diagnosis, treatment, or clinical inference |

The organization should assess whether wellness features should be disabled by default, stored separately from operational records, or aggregated only above a privacy threshold. These decisions require HR, privacy, legal, employee-representative, and security review. This report does not determine legal compliance. Applicable privacy obligations must be reviewed by qualified counsel for the deployment jurisdiction and data flows.

Wellness success should be assessed through voluntary, privacy-preserving feedback and service quality measures, not solely through score movement. A responsible system may create value by making information clearer even when no measurable behavior change is observed.

<div class="page-break"></div>

## Page 24 - Data and information management

The platform's management value is bounded by the quality, meaning, and stewardship of its data. A dish identifier that changes between menus, inconsistent units for stock, missing service dates, and stale allergen declarations can produce operationally misleading analytics even when the code is functioning as written. Data governance is therefore a core operating capability rather than a preparatory IT task.

Start with a data catalogue that records each dataset, business owner, steward, source system, refresh frequency, retention rule, sensitivity, definition, and permitted purpose. Build a data dictionary for each decision-relevant field. For example, “order count” should specify whether cancelled or pending orders are included; “stock” should specify unit and timestamp; “consumption” should distinguish sales or orders from physical usage; and “healthy portion” should identify the exact rule and approver.

**Table 18. Proposed minimum data-quality dimensions**

| Dimension | Example test | Owner |
|---|---|---|
| Completeness | Required dish fields populated | Menu steward |
| Validity | Units, dates, and values within defined rules | Data steward |
| Consistency | Same item, unit, and status definitions across views | Product/data owner |
| Timeliness | Refresh age visible and within agreed threshold | Operations owner |
| Uniqueness | No duplicate item or event identifiers | Application owner |
| Accuracy | Sampled record matches authoritative source | Operational controller |
| Lineage | Output links to source version and transformation | Analytics owner |

Quality checks should operate before and after data ingestion. A rejected file should state the row, column, and corrective action without exposing unrelated personal data. A committed change should have a versioned audit trail, who/when/why metadata, and a path to correct an error. When data are incomplete or stale, the interface should degrade safely: label the uncertainty, suppress unsupported recommendations, or require confirmation.

Data collection should be purpose-specific. Do not retain identifiable employee order history indefinitely just because storage is inexpensive. Define retention and deletion schedules, roles authorized to access each field, and a process for access, correction, and deletion requests where applicable. Aggregation and de-identification reduce but do not eliminate privacy risk; re-identification may remain possible in small groups or rare categories.

A data steward must be assigned for menu facts, stock definitions, and KPI logic before a pilot. The person is accountable for definitions and quality exceptions, not necessarily for coding. Without stewardship, the organization risks treating the dashboard as the source of truth when it may only be a new view over inconsistent records.

<div class="page-break"></div>

## Page 25 - Architecture and system context

ECOS uses a Streamlit dashboard and a FastAPI service, with MongoDB documented as the data store. The root entry point `app.py` starts the API with Uvicorn bound to `127.0.0.1`, waits on a local health URL, and launches the Streamlit dashboard; running the root file under Streamlit instead renders the dashboard path. The source comments describe the backend as private to the container while the UI is exposed. The deployment notes supplied for this report state that Docker exposes UI port 7860 and maps host port 8501. These are configuration-level observations, not proof of a deployed production topology.

The application uses synchronous PyMongo, not Motor. This matters for capacity planning: concurrency and long-running database work should be assessed under expected load, and the team should not describe the persistence layer as asynchronous. A deployment review should evaluate connection lifecycle, timeout behavior, pool sizing, health checks, and graceful degradation under the actual hosting environment. This report does not inspect backend implementation details or conduct an exhaustive architecture audit.

The architecture vision includes ten target modules, while the actual user experience has employee and manager roles. The module list documented in [API_ENDPOINTS.md](../API_ENDPOINTS.md) includes user/profile, menu/catalog, ordering, inventory, recommendations, forecasting, analytics/KPIs, simplified procurement, feedback/customer behavior, and read-only AI copilot, plus platform endpoints. A module in a documented map is not equivalent to a fully production-ready bounded service.

**Figure 3. System context (planned diagram).** [System context diagram](assets/system-context.svg) is a planned authored diagram. It should show employee and manager actors, Streamlit UI, FastAPI service, MongoDB, optional catalog enrichment dependencies, and external boundaries. It is not a screenshot and should clearly mark optional or future connections.

The optional Qdrant enrichment path depends on catalog inputs and should be described as optional, not assumed for every user journey. The current copilot is rule-based and read-only by default; the slim requirements do not include the optional LangChain stack. These distinctions prevent an architecture figure from implying an LLM-powered, always-connected, or autonomous system.

**Figure 4. Target architecture reference.** [Architecture.png](../Architecture.png) is an existing project artifact. It is referenced as the project's architecture image, not represented as a runtime screenshot or as proof of all depicted features being implemented.

<div class="page-break"></div>

## Page 26 - Module design and dependencies

Modular decomposition helps management reason about ownership, change impact, and failure boundaries. The documented API map organizes functions across user/profile, menu/catalog, ordering, inventory, recommendations, forecasting, analytics/KPIs, simplified procurement, feedback/customer behavior, and AI copilot. It also identifies platform functions. The executive decision is whether these capabilities form a coherent operating product with clear handoffs, or remain a set of adjacent features with inconsistent data definitions.

Dependencies should be mapped in terms of business information, not only network calls. Recommendations depend on trustworthy menu attributes and availability. Ordering depends on clear item identity, price, and confirmation state. Inventory risk depends on stock units, consumption definitions, and recipe-to-ingredient relationships. Forecasting depends on service-date history and a baseline definition. Analytics depends on consistent lifecycle events. Copilot responses depend on the rules and source records available to it. When upstream definitions are weak, downstream presentation can make uncertainty appear authoritative.

**Figure 5. Module connections (planned diagram).** The planned [module-connections diagram](assets/module-connections.svg) should show the ten target modules, shared data definitions, optional enrichment boundaries, and manual approval points. It must distinguish verified application behavior from conceptual dependency lines.

**Table 19. Recommended module ownership**

| Capability | Business owner | Technology/data owner | Key contract |
|---|---|---|---|
| Menu/catalog | Menu steward | Product/data team | Versioned dish and declared attributes |
| Ordering | Service operations | Application owner | Lifecycle state and idempotent event |
| Inventory | Stock controller | Data/API owner | Item, unit, balance, movement |
| Forecasting | Operations planner | Analytics owner | Horizon, unit, model/baseline status |
| Recommendations | Employee-service owner | Product/analytics owner | Explainable rule and opt-out |
| Executive KPIs | Leadership sponsor | Finance/data owner | Approved metric dictionary |
| Copilot | Operations owner | Product owner | Read-only scope, cited basis, fallback |

The recommended architecture governance artifact is a change-impact map. For each proposed feature, identify affected modules, data contracts, permissions, employee messages, operational controls, and evaluation measures. A change to allergen metadata may affect menu display, recommendation eligibility, employee trust, and incident handling. A change to order status may affect forecasting, executive metrics, service recovery, and audit interpretation.

Module boundaries should follow cohesive business capability and accountability. Avoid creating “AI” as a separate authority that bypasses established decisions. The copilot should remain an access path to approved decision rules, not a shadow workflow that can issue commitments or make health judgements.

<div class="page-break"></div>

## Page 27 - Order lifecycle and service recovery

An order is a sequence of states, not a single count. Management reporting can become misleading if submitted, pending, accepted, prepared, collected, cancelled, and refunded records are treated as equivalent. The UI distinguishes pending orders from collected orders in the wellness calculation, and its payment message states that no money is taken. Executive captions explicitly identify order values as demo values rather than audited revenue. These boundaries should inform any proposed analytics contract.

**Figure 6. Order lifecycle (planned diagram).** [Order lifecycle diagram](assets/order-lifecycle.svg) is a planned authored diagram, not a screenshot. It should label only verified states as current and use a different visual style for proposed stages such as paid, refunded, or supplier fulfillment if those are not implemented.

**Table 20. Proposed order-state semantics**

| State or event | Meaning for management | Must not be confused with |
|---|---|---|
| Draft/cart | Employee is considering a choice | Demand commitment |
| Submitted/pending | Request is recorded but not completed | Fulfilled service or collected order |
| Accepted | Operations has acknowledged request | Pickup or consumption |
| Prepared/ready | Item is ready under local process | Completed collection |
| Collected/completed | Service reports fulfillment | Payment settlement or consumption |
| Cancelled/failed | Request did not complete | Zero demand or employee dissatisfaction |

The actual state vocabulary should be confirmed against the API contract and UI before the diagram is finalized. This report does not invent an exact lifecycle implementation. A pilot should define a single authoritative transition table, allowed transitions, timestamps, actor, reason, and recovery action. Duplicate submissions, retries, delayed updates, and out-of-order events should be covered in acceptance tests.

Service recovery is a management capability. When an item is unavailable, the employee needs a timely message, acceptable alternative or refund policy if applicable, and a human support route. Because the current demo payment takes no money, payment-related refund requirements are future production requirements rather than current capabilities. In a real paid service, the order lifecycle and financial ledger must reconcile exactly; an order-value display cannot replace transaction settlement evidence.

Metrics should derive from event states with explicit denominators. Completion rate should not count an order as completed merely because it was submitted. Average service time should define start and end events and address outliers. Cancellation analysis should distinguish employee choice from stockout or operator cancellation. These definitions are prerequisites for management interpretation.

<div class="page-break"></div>

## Page 28 - Decision support and copilot boundaries

Decision support should make it easier for a manager to find relevant, approved information and apply judgement. The current copilot is characterized as rule-based and read-only by default, not an LLM interface. This is materially different from a generative assistant that synthesizes arbitrary language or takes actions. The report therefore describes it as a constrained presentation layer over known rules and data, subject to the source files and runtime behavior that are later verified.

A read-only design reduces some action risks but does not remove all risks. Incorrect or stale data can still be presented persuasively. A rule may encode an unsuitable threshold. A result may omit the context a manager needs. A user may interpret a heuristic as a probability. The interface should state its knowledge boundary, show the relevant data timestamp and rule basis, identify uncertainty, and direct the user to the authoritative record or responsible owner.

**Table 21. Copilot interaction standard**

| Interaction | Expected design |
|---|---|
| Request for stock risk | Explain rule and current balance timestamp |
| Request for forecast | Label model, baseline, fallback, horizon, unit |
| Request for menu substitution | Show ingredient and declared-attribute checks |
| Request for wellness advice | Decline clinical advice; point to menu facts and support |
| Request to place a purchase order | State that supplier ordering is outside the current simplified workflow |
| Missing data | Explain absence; do not infer a fact |

The optional Qdrant enrichment path is not a default dependency for all operations. Catalog enrichment may improve retrieval or similarity only if the underlying catalog is valid, the index is current, and retrieval quality is measured. If a vector result is ever introduced into a user-facing decision, the system should disclose the source, ranking basis, and confidence limitations and provide a non-vector fallback.

Any future LLM integration should pass a separate design review: approved use cases, data minimization, prompt-injection and output-risk assessment, retrieval provenance, hallucination testing, access control, monitoring, vendor/data-transfer review, human approval, and an incident process. This report does not claim that such an LLM stack is installed or used by default. Keeping the current rule-based scope clear protects the project's credibility and gives management a controlled path to extension.

<div class="page-break"></div>

## Page 29 - Architecture gap analysis

The architecture map is useful as a target-state view, but management must know the difference between a target module, a prototype feature, a verified integration, and a production control. The report relies on the documented API map and inspected dashboard entry points rather than an exhaustive backend audit. Detailed endpoint-level or security conclusions are intentionally outside scope.

**Table 22. Target-to-evidence gap assessment**

| Target area | Current evidence | Gap or qualification | Management consequence |
|---|---|---|---|
| Employee/manager experience | Five employee and seven manager pages | Only two actual role groups are described | Do not imply ten role types |
| Menu and ordering | UI flows and API documentation | Demo checkout; no money taken | Separate order value from revenue |
| Inventory | Stock, consumption, edit, risk views | Replenishment context is not full procurement | Keep human approval |
| Procurement | Simplified module documented | No supplier master or purchase orders | Do not claim supplier integration |
| Forecasting | UI controls and train/predict code | No verified active artifact or score | Treat as evaluation candidate |
| Analytics | Executive view and documented KPI area | Demo order values are not audited revenue | Reconcile before finance use |
| Copilot | Rule-based, read-only by default | Not an LLM by default | Avoid autonomous/agent claims |
| Catalog enrichment | Qdrant optional | Dependencies and enrichment are optional | Mark pathway as conditional |
| Database access | MongoDB with synchronous PyMongo | Not Motor/asynchronous client | Review capacity and I/O behavior |
| Scheduling | On-demand jobs described | No real scheduler | Assign trigger and operating cadence |

The on-demand job boundary deserves special attention. A retraining or refresh operation that runs only when invoked does not provide a scheduled service-level guarantee. A production operating model must specify who or what triggers the job, how completion is observed, what happens on failure, how stale outputs are labeled, and who approves activation. A scheduled pipeline would add infrastructure and operational responsibilities that should be costed and tested.

Gap analysis should lead to sequenced decisions, not a demand to “finish everything.” The first priority is to protect employee and stock decisions from incorrect interpretation; the second is to establish auditable lifecycle and metric definitions; the third is to improve planning evidence; and only then should optional advanced enrichment be considered. This ordering favors trust and management utility over breadth.

The gap table is an analytical summary, not a vulnerability assessment, code audit, or production-readiness certification.

<div class="page-break"></div>

## Page 30 - Operations and service management

A dependable service requires operational ownership beyond application code. Managers need a daily operating rhythm, clear escalation, service support, incident tracking, and a recovery mode. The root `app.py` documents a local health-check wait for backend startup and a Streamlit launch flow. This is helpful for a demo lifecycle, but it is not evidence of production monitoring, autoscaling, uptime, backup, or incident response.

The proposed service model should define service hours, user support channel, severity levels, response expectations, ownership on each shift, and fallback procedures. A dashboard outage during meal service should not prevent the cafeteria from serving employees. An approved offline menu and manual order/stock process should be available, with a reconciliation step when the system returns. Staff should know which records may be re-entered, which must not be duplicated, and who can declare the service restored.

**Table 23. Operational review cadence**

| Cadence | Review focus | Output |
|---|---|---|
| Shift start | Availability, pending exceptions, data freshness | Named owner and shift risks |
| Before service | Menu and stock confirmation | Current availability and substitution notice |
| During service | Delay, stockout, order issue | Resolution and employee communication |
| Shift close | Orders, stock movement, waste, incidents | Reconciliation and carry-forward actions |
| Weekly | Forecast errors, menu mix, repeat issues | Approved process changes |
| Monthly | Scorecard, privacy and governance, benefits | Continue/change/stop decision |

The service owner should maintain a known-error register, change calendar, dependency inventory, backup and recovery plan, and access review schedule. If an optional vector database or external catalog is unavailable, the system should fail in a controlled way and communicate that a result is unavailable rather than silently presenting stale enrichment.

Operations should distinguish incidents from requests. A menu correction, missing order, wrong stock balance, access issue, suspected data exposure, and forecast anomaly have different urgency and containment requirements. Each needs a route, response owner, evidence retention rule, and closure code. Trend reviews should search for systemic causes instead of treating recurring incidents as isolated user mistakes.

No service-level or uptime target is proposed here because workload, platform, hosting, support coverage, and baseline service expectations have not been measured. Targets should be negotiated with the business owner and validated against operational capacity before being published.

<div class="page-break"></div>

## Page 31 - Risk and control matrix

Risk management connects uncertainty to ownership, prevention, detection, response, and residual exposure. A risk list without a control owner is not an operating control; a control without evidence cannot be tested. The matrix below is a management design for a pilot and should be calibrated in a workshop with cafeteria operations, finance, procurement, IT, privacy, and employee representatives.

**Table 24. Pilot risk and control matrix**

| Risk | Preventive control | Detective control | Response/owner |
|---|---|---|---|
| Stale or incorrect menu attributes | Stewarded approval and effective dates | Scheduled completeness review | Correct/pause item; menu owner |
| Allergen declaration misunderstood | Prominent limitation and staff route | Review employee incidents/questions | Escalate, correct disclosure; food-safety owner |
| Stock edit error | Role access, validation preview, reason code | Reconciliation and movement review | Reverse/correct; inventory owner |
| Forecast over-trusted | Baseline comparison and human approval | Error and override review | Suspend output; operations/analytics owner |
| Demo value called revenue | Persistent demo label and metric dictionary | Finance review of reports | Retract/correct; finance owner |
| Wellness use feels coercive | Purpose limitation and opt-out | Privacy-safe feedback channel | Disable feature/investigate; HR/privacy |
| Order state ambiguity | State definitions and transition checks | Exception report | Reconcile; service owner |
| Integration/job unavailable | Dependency and fallback plan | Health/status monitoring | Manual service and recovery; IT |
| Data misuse or exposure | Minimize and restrict access | Access audit/incident monitoring | Contain, notify, remediate per policy |
| Adoption failure | Co-design and role training | Task completion and user feedback | Redesign process; change lead |

For each risk, the pilot charter should record likelihood and impact using a defined scale, inherent risk, control owner, evidence artifact, residual risk, review date, and escalation threshold. Numeric risk scores should be treated as prioritization aids, not objective probabilities unless calibrated. A high-impact low-frequency scenario can warrant strong controls even if a simple product score appears modest.

Risk appetite should be explicit. The organization may tolerate a temporary forecast fallback or a delayed reporting view; it should not tolerate misleading allergen assurance or hidden employee monitoring. The business sponsor should approve these boundaries, while technical teams implement proportionate controls.

The matrix is not a vulnerability audit. It does not evaluate exploitable weaknesses, penetration-test results, authentication implementation, or detailed code security. Such work requires a separately scoped review and must not be inferred from this management risk treatment.

<div class="page-break"></div>

## Page 32 - Privacy governance and responsible data use

Privacy governance should begin with the purpose of each data field and the decision it supports. Employee order data may be necessary to fulfill an order, but that does not make every secondary use appropriate. Wellness analytics, recommendation personalization, service recovery, operational forecasting, and financial reconciliation each require a distinct purpose statement and access rule. Data should not be retained or linked simply because a future analysis might be interesting.

The recommended approach is a privacy-by-design assessment before any live pilot. Document data categories, identifiers, sources, users, processing purpose, retention, storage, transfer, deletion, and access. Identify whether any field could reveal dietary restrictions, religious practice, health status, or other sensitive inference. Determine whether individual-level analysis is necessary or whether an aggregate view can meet the operational objective. In small workforces, aggregation can still permit re-identification and should be reviewed contextually.

**Table 25. Data-use decision checklist**

| Question | Required answer before pilot |
|---|---|
| Why is the data collected? | Specific, approved service or evaluation purpose |
| Who can see identifiable data? | Named roles and least-privilege rule |
| How long is it kept? | Retention schedule and deletion evidence |
| Can the employee correct it? | Clear contact and correction path |
| Can it affect employment? | Explicit prohibition for wellness participation/score |
| Is an external service involved? | Data-transfer and contract review |
| What happens after a breach or misuse? | Escalation, containment, and notification process |

The NIST Privacy Framework is a useful risk-management reference, not a certification or legal-compliance substitute. The NIST AI Risk Management Framework may help structure governance if advanced AI is later introduced, but the current rule-based read-only copilot should not be mischaracterized as an AI system that uses a large language model by default. Jurisdiction-specific requirements, including applicable Indian law and organizational policy, should be reviewed by qualified legal and privacy professionals.

Management should separate wellness and operational analytics where feasible. Restrict access to identifiable histories, set minimum group sizes for reporting, suppress small-cell combinations, and log privileged access. If an employee opts out of personalization, the system should respect that choice without reducing access to the full menu or service.

Privacy controls are not merely technical. Managers and staff need a clear script explaining what is collected, what is not collected, why, for how long, and whom to contact. Trust depends on the lived practice matching that explanation.

<div class="page-break"></div>

## Page 33 - Analytics governance and model oversight

Analytics governance governs how data become a recommendation, a forecast, or a management KPI. It should identify the owner of the business question, the owner of the method, the source of data, the person who approves changes, the user who acts on output, and the process for correction. The governance model must cover simple rules as well as statistical models. A rule-based score can still create unfair or misleading outcomes if its assumptions are hidden.

**Table 26. Analytics lifecycle controls**

| Lifecycle step | Control evidence |
|---|---|
| Define use case | Approved decision, user, and prohibited uses |
| Prepare data | Source, lineage, quality checks, exclusions |
| Develop | Versioned code and reproducible dependency set |
| Evaluate | Baseline, chronological test, subgroup and error review |
| Approve | Named business and analytics approvers |
| Deploy | Artifact identity, activation date, rollback plan |
| Monitor | Coverage, input drift, output, error, override, incident |
| Retire | Deactivation rationale, archive, user communication |

For the implemented Random Forest pipeline, the governance packet should include exact feature definitions, training-data cut-off, chronological split, baseline calculation, MAE/WAPE by relevant segment, minimum history rule, sklearn version, artifact hash, and activation decision. The serving gate based on MAE not exceeding baseline is a useful guardrail, but it should be coupled with segment-level performance and operational cost review. A candidate that barely meets an aggregate gate could still be unsuitable for a high-risk item or sparse period.

Overrides are valuable evidence. Managers should be able to record whether they accepted, adjusted, or ignored an output and why. High override rates may indicate poor model fit, missing context, low trust, or a good human process that correctly recognizes exceptions. They should trigger inquiry, not punishment. Likewise, low override rates do not prove good performance; they may signal automation bias.

The production model should be monitored against baseline and observed outcome, with a defined process for drift, data gaps, and deterioration. If the model or data pipeline fails, the fallback should be explicit, safe, and visible. On-demand retraining requires an owner and trigger; it is not a schedule. No training artifact, active model, or measured accuracy is established by this report.

If any future generative capability is considered, add controls for retrieved-source grounding, hallucination, prompt misuse, data leakage, and human confirmation. The present report does not claim such capability is active.

<div class="page-break"></div>

## Page 34 - Management accounting and cost model

Management accounting can turn the project from a feature discussion into a resource-allocation decision. The first requirement is to separate the prototype's demo metrics from financial records. The Executive view explicitly captions demo order values as not audited revenue, and the demo checkout states that no money is taken. Those labels must remain visible in screenshots and presentations. An order value can be useful for interface illustration, but it is not recognized sales, collected cash, contribution margin, or audited revenue.

A future cost model should distinguish one-time and recurring costs. One-time categories may include process discovery, implementation, data cleanup, integration, training, privacy assessment, and change management. Recurring categories may include hosting, database service, model monitoring, support, menu stewardship, data quality work, supplier integration, security review, and staff time spent resolving exceptions. Opportunity costs matter: a manager's time to validate data is a real resource even if no new invoice is issued.

**Table 27. Recommended cost-center view**

| Cost category | Example driver | Evidence source |
|---|---|---|
| Technology | Hosting, storage, database, monitoring | Approved cloud estimate/invoice |
| Implementation | Engineering, integration, migration | Time records and vendor statements |
| Operations | Support, incident handling, menu/data stewardship | Staff hours and service logs |
| Change | Training, communication, backfill | Attendance and effort records |
| Control | Privacy, audit, testing, legal review | Approved engagement and time |
| Transition | Parallel running, manual fallback, retirement | Project plan and process records |

Cost allocation should map to the organization that realizes the benefit. Cafeteria operations may carry staffing and waste costs, while employees realize convenience and the business may realize retention or wellness benefits. If costs and benefits sit in different budgets, a cross-functional sponsor is needed to avoid rejecting a good enterprise investment because of local budget boundaries.

Benefits should be classified as cashable savings, cost avoidance, capacity released, service quality, risk reduction, or employee experience. Only cashable and finance-validated benefits should enter a conventional cash-flow case. Capacity released is not a cash saving unless staffing or overtime changes accordingly. Cost avoidance requires a counterfactual and should be disclosed as such.

The finance partner should approve the baseline, cost center, valuation method, period, and evidence threshold before the pilot begins. This report intentionally supplies no local costs, sales, savings, or accounting results. It provides only a framework for collecting them.

<div class="page-break"></div>

## Page 35 - Investment appraisal with hypothetical inputs

An investment appraisal should make uncertainty visible and keep scenario arithmetic separate from observed project outcomes. The following example is entirely hypothetical and exists only to illustrate methods; its values are not ECOS estimates, market quotations, forecasts, or realized savings. Before a real decision, finance must replace every input with approved local evidence and document the counterfactual.

**Illustrative assumption set:** suppose a hypothetical pilot and first-year operating setup costs ₹12 lakh in year 0; a hypothetical annual net benefit of ₹8 lakh is assumed in years 1–3; the discount rate is assumed at 10%; no tax, inflation, salvage value, working-capital change, or residual value is included. These round numbers are not derived from user data.

**Formula 1. Net present value**

\[
NPV = -I_0 + \sum_{t=1}^{n} \frac{B_t - C_t}{(1+r)^t}
\]

With the purely illustrative inputs above, NPV = \(-₹12\text{ lakh} + ₹8\text{ lakh}/1.10 + ₹8\text{ lakh}/1.10^2 + ₹8\text{ lakh}/1.10^3\), approximately ₹7.9 lakh. The calculation does not demonstrate that ECOS will earn this return; it demonstrates why validated benefit and cost inputs matter. A three-year payback or NPV should not be presented without a defined investment horizon, uncertainty range, and sensitivity analysis.

**Table 28. Illustrative scenario sensitivity (hypothetical only)**

| Scenario | Annual net benefit assumption | Discount-rate assumption | Interpretation |
|---|---:|---:|---|
| Downside | ₹3 lakh | 12% | Benefits may not cover full lifecycle cost |
| Base illustration | ₹8 lakh | 10% | Arithmetic example only |
| Upside | ₹12 lakh | 8% | Requires stronger evidence and capacity |

The scenario table is not a probability distribution. A real appraisal should test adoption, data-quality effort, support cost, operating disruption, benefit ramp-up, and potential disbenefits. It should include a “do nothing” or “continue current process” counterfactual and compare against lower-cost alternatives such as a standardized spreadsheet, existing enterprise tooling, or process redesign without a new platform.

Use break-even analysis to ask what minimum benefit would be necessary to justify total lifecycle cost. For a service intervention, benefits may be partly non-financial; management can use a weighted scorecard alongside financial NPV, but should not translate every employee-experience improvement into an invented rupee value. If the investment case remains uncertain, a limited pilot can be framed as an option purchase: a bounded cost buys information that improves a later scale decision.

<div class="page-break"></div>

## Page 36 - Benefits realization plan

Benefits realization starts before implementation. Each benefit needs a named owner, baseline, target-setting process, metric definition, evidence source, measurement cadence, dependencies, and realization date. A project team can deliver software without realizing the expected benefit if the process, training, decision rights, and data quality do not change. The sponsor should own the benefit case after handover rather than leaving it with the developer.

**Table 29. Benefits register template**

| Benefit hypothesis | Leading indicator | Outcome evidence | Accountable owner |
|---|---|---|---|
| Faster exception awareness | Time from event to visible queue | Resolution time and service log | Operations manager |
| Better stock decisions | Count/reconciliation completeness | Availability, variance, waste data | Inventory owner |
| More informed menu choice | Attribute completeness and views | Employee feedback and completed selection | Menu/employee-service owner |
| Improved demand planning | Forecast coverage and baseline comparison | Actual service outcomes and override rationale | Planner |
| Better management review | KPI definition and freshness | Decisions recorded and actions closed | Executive sponsor |

All benefits remain hypotheses until measured. A “before/after” comparison can be misleading if the menu, staffing, attendance, season, or supplier conditions also change. The evaluation plan should record context and, where feasible, use a comparison site, staggered rollout, matched periods, or interrupted time series. If the design cannot support causal attribution, use cautious language: the metric changed during the pilot, not because of it.

Benefits should include disbenefits and distributional effects. A time-saving workflow may shift work from managers to employees; a lean inventory policy may reduce holding cost but increase stockout risk; personalized recommendations may raise selection of featured items but reduce perceived autonomy. The benefits register should therefore include counter-metrics and employee feedback, not only sponsor-selected gains.

A monthly realization review should classify each hypothesis as not yet measurable, on track, at risk, realized, or discontinued. A benefit that cannot be measured because data are unavailable should not be silently treated as delivered. The owner should create a corrective action, adjust the metric, or close the hypothesis with a documented reason.

After project handover, preserve the original baseline and calculation logic, version any definition changes, and report both favorable and unfavorable evidence. Finance should validate cashable claims. Operations should validate service outcomes. Employee representatives and privacy owners should review wellness-related measures. This governance makes the business case credible even if the outcome is mixed.

<div class="page-break"></div>

## Page 37 - Balanced scorecard

The Balanced Scorecard can connect strategy with a balanced set of financial, customer, internal-process, and learning measures. Its value for ECOS is not to populate four boxes with optimistic targets; it is to ensure leaders do not optimize one result at the expense of another. Kaplan and Norton's original work emphasizes measures that translate strategy into action. For this prototype, the scorecard should be staged: first establish definitions and baseline, then approve targets, then review outcomes and trade-offs.

**Table 30. Proposed ECOS pilot scorecard**

| Perspective | Strategic question | Candidate measure | Guardrail |
|---|---|---|---|
| Financial/stewardship | Is the service economically responsible? | Validated lifecycle cost and cashable benefit | Demo order value excluded from revenue |
| Employee/customer | Is the experience clear and trustworthy? | Task completion, issue resolution, voluntary feedback | Full-menu access and wellness opt-out |
| Internal process | Are service and stock decisions controlled? | Availability, reconciliation, exception closure | Accuracy and safety checks |
| Learning/capability | Is the organization learning from evidence? | Data completeness, model/baseline review, staff readiness | No scale-up without decision gate |

The scorecard should include leading and lagging indicators. Data completeness and employee training are leading indicators; fulfillment and measured waste are lagging indicators. Leading indicators help diagnose why outcomes may change, but they are not substitutes for outcomes. A training completion rate alone says nothing about whether staff can perform a task; pair it with a short observed proficiency check.

Each measure needs a target owner and review cadence. Targets should not be chosen to reward activity for its own sake. For instance, a higher recommendation click-through rate might increase attention without improving order completion or employee trust. It should be accompanied by completed-order and opt-out measures. Lower stock levels should be paired with stockout and service-recovery measures.

Scorecard design should also prevent metric gaming. If managers are rewarded for low cancellation, they may avoid recording cancellations; if employees are scored on wellness, they may feel pressured to order through the system. Independent reconciliation, clear definitions, and a no-punitive-use rule help preserve integrity.

At the monthly review, leaders should ask whether each perspective is improving, whether trade-offs are acceptable, what data quality limitations remain, and whether the next decision should be continue, adapt, pause, or stop. No numerical target is asserted in this report because local baselines and operating constraints are not available.

<div class="page-break"></div>

## Page 38 - KPI dictionary: service and adoption

An executive metric is only as good as its definition. This page proposes a KPI dictionary starter set; each measure requires local validation before use. A metric should have a stable name, purpose, formula, numerator and denominator, inclusion rules, time grain, segment, data owner, target process, and known limitations.

**Table 31. Service and adoption KPI definitions**

| KPI | Proposed formula/definition | Interpretation limit |
|---|---|---|
| Order completion rate | Completed orders ÷ eligible submitted orders | Define cancellation, substitution, and eligibility |
| Availability rate | Item-periods available ÷ item-periods offered | Requires reliable availability status history |
| Stockout incidence | Confirmed stockout events per defined service volume | Event definitions and reporting completeness matter |
| Exception resolution time | Resolution timestamp − logged timestamp | Report median and distribution, not just mean |
| Menu data completeness | Required populated fields ÷ required fields | Completeness does not prove correctness |
| Employee task success | Participants completing defined task unaided ÷ participants attempting | Study sample/design must be reported |
| Adoption by role | Active eligible users with a defined qualifying action ÷ eligible users | Login is not value; avoid coercive targets |
| Repeat selection | Employees selecting an item again within a stated window | Does not establish loyalty or satisfaction |

**Formula 2. Completion rate**

\[
\text{Completion Rate} = \frac{\text{Orders reaching the approved completed state}}{\text{Eligible submitted orders}} \times 100\%
\]

The denominator should exclude only documented cases such as duplicate test records and should be reported with the exclusion count. If demo orders are involved, keep the measure labeled as demo behavior and do not call it sales conversion. If a completed state means collected but not paid, do not call it paid conversion.

Adoption should be treated as a service diagnostic, not as an employee performance score. A low rate may reflect accessibility, awareness, unreliable connectivity, a poor menu, or a deliberate preference for another ordering channel. Collect reasons through a voluntary, privacy-safe feedback path and maintain equivalent service access where required.

Use cohort and shift segments only when sample sizes permit responsible interpretation. Small groups can reveal individual behavior. Suppress or combine small cells according to an approved privacy rule. Report the date range, data freshness, and count of eligible observations with every dashboard metric.

KPI owners should review metric logic after process changes. If an order state or menu workflow changes, the historical series may no longer be directly comparable. Preserve versions and annotate breaks instead of silently rewriting prior periods.

<div class="page-break"></div>

## Page 39 - KPI dictionary: analytics and control

The analytics and control scorecard should measure not only predicted outcomes but the quality of the decision process. Forecast error, baseline comparison, data coverage, stock reconciliation, and override rationale each reveal a different failure mode. Combining them into one composite score can conceal important differences.

**Table 32. Analytics/control KPI definitions**

| KPI | Proposed formula/definition | Control interpretation |
|---|---|---|
| MAE | Mean of \(|actual - forecast|\) on defined holdout | Same unit as target; segment results required |
| WAPE | \(\sum |actual-forecast| / \sum actual\) | Unstable when denominator is zero or tiny |
| Forecast coverage | Eligible item-periods with a valid forecast ÷ eligible item-periods | Report fallback and missing status separately |
| Baseline improvement | \((MAE_{baseline}-MAE_{candidate})/MAE_{baseline}\) | Positive only if candidate has lower MAE |
| Forecast bias | Mean of \(forecast-actual\) | Direction matters for surplus/shortage trade-offs |
| Reconciliation variance | Absolute difference between recorded and physical quantity | Use unit and count date; investigate rather than normalize |
| Edit audit completeness | Stock changes with actor, reason, time, and source ÷ all changes | A complete log is not proof the change was correct |
| Model override rate | Outputs changed or rejected ÷ reviewed outputs | Requires context and reasons, not punitive interpretation |

**Formula 3. Baseline improvement**

\[
\text{Baseline Improvement} = \frac{MAE_{\text{baseline}} - MAE_{\text{candidate}}}{MAE_{\text{baseline}}}
\]

If the baseline MAE is zero, the ratio is undefined and should not be reported as a percentage. A candidate meeting the code's overall MAE gate should still be examined for segment failures, sparse data, and asymmetric error cost. Model coverage should be reported so that a low error calculated only on easy cases is not mistaken for broad utility.

The model pipeline compares a candidate with a same-weekday-four baseline; this report does not claim the baseline calculation or metric results were independently reproduced. The next evaluation should record dataset version, training cut-off, split dates, model dependency version, and random seed, then preserve a reproducible report. No accuracy target is recommended before the baseline and decision cost have been established.

Control KPIs should have explicit escalation thresholds and actions. A threshold without response capacity is merely an alert. If the stock reconciliation variance exceeds an approved tolerance, the owner should investigate item mapping, unit conversion, timing, shrinkage, and process adherence. If forecast coverage drops, managers should switch to a labeled baseline or manual plan.

<div class="page-break"></div>

## Page 40 - Project management lifecycle and quality

A robust project lifecycle provides governance from discovery to handover. The report recommends stage gates rather than an unbounded “build until complete” approach. Each gate should have business evidence, technical evidence, control review, accountable approval, and documented exit criteria. A feature should not advance merely because its code has merged.

**Table 33. Proposed project lifecycle**

| Stage | Core work | Gate evidence |
|---|---|---|
| Discover | Stakeholder interviews, current-state map, baseline plan | Approved problem and process owner |
| Define | Scope, requirements, data contracts, risk assessment | Signed pilot charter and acceptance criteria |
| Design | Service blueprint, role design, privacy and control design | Review by operations, IT, finance, privacy |
| Build | Implement prioritized workflows with traceability | Versioned release and test evidence |
| Verify | Functional, usability, data, performance, recovery tests | Defect disposition and readiness decision |
| Pilot | Controlled operation and measurement | Baseline, monitoring, incident and feedback logs |
| Evaluate | Compare outcomes, costs, and limitations | Finance and business benefit review |
| Handover/retire | Ownership, support, documentation, decommissioning | Operational acceptance or safe shutdown |

Project quality includes fitness for purpose, not just defect-free code. Requirements should state who uses a capability, what decision it supports, what data it consumes, what failure looks like, and what control evidence must be retained. Traceability should connect requirement → design → implementation → test → acceptance → KPI. For a menu allergen display, this means linking the requirement to the source data steward, UI disclaimer, review process, and a test that checks the declared field and limitation appear correctly.

Change control should protect the approved objective. When new scope is proposed, estimate business value, operational dependencies, privacy impact, cost, test effort, and displaced work. A lightweight decision log should capture date, alternatives, assumptions, approver, and revisit trigger. This prevents a demo request from becoming an implicit production obligation.

The final integration phase should include a full user journey across role boundaries: employee places a demo order; manager sees an operational consequence; inventory and menu data remain coherent; a decision is documented; and employee-facing status is understandable. This is a proposed test scenario, not a claim that the report author executed it.

Handover should include runbooks, service ownership, environment and dependency information, data-retention rules, recovery process, backlog, and known limitations. If no team can own the service after the project, the correct decision may be to archive the prototype rather than deploy it without support.

<div class="page-break"></div>
