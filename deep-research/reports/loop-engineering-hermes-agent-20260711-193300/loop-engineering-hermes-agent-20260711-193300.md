# Loop Engineering with Hermes Agent: Multi-Role Agent Orchestration

## Executive Summary

Loop engineering is a paradigm shift from prompt-based AI interaction to continuous, iterative AI-driven development cycles where multiple specialized agents collaborate in a closed-loop workflow. This report explores how to design and implement loop engineering using Hermes Agent, defining 11 distinct agent roles (Product Manager, UX Designer, UI Developer, Backend Engineer, Backend Test Engineer, UI Test Engineer, DevOps Engineer, SecOps Engineer, Customer Acceptance Engineer, plus Architect and Developer) with structured profiles, inter-agent communication protocols, best practices, and required skillsets.

---

## 1. What Is Loop Engineering?

Loop engineering replaces linear prompt-and-response patterns with **continuous feedback loops** where AI agents:

- **Produce** artifacts (code, designs, tests, configs)
- **Validate** them against criteria (tests, reviews, security scans)
- **Learn** from failures and iterate
- **Share** state and updates across the team

The core loop: **Plan → Build → Test → Review → Deploy → Monitor → Feedback → Repeat**

This is fundamentally different from traditional prompt engineering because it treats AI as **persistent team members** with roles, responsibilities, and communication channels rather than one-off query tools.

---

## 2. The Hermes Agent Architecture

Hermes Agent provides a framework for defining **role-based AI agents** with:

- **Profiles**: Structured role definitions with skills, responsibilities, and constraints
- **Communication**: Inter-agent messaging for status updates, handoffs, and collaboration
- **Orchestration**: A central coordinator that manages the loop flow between agents

### Core Design Principles

1. **Each agent has a single responsibility** — no role ambiguity
2. **Agents communicate via structured messages** — not free-form chat
3. **State is shared through a common workspace** — files, artifacts, and status
4. **The loop is deterministic** — each phase has clear entry/exit criteria
5. **Human-in-the-loop** — critical decisions require human approval

---

## 3. Agent Role Definitions

### 3.1 Product Manager Agent

**Profile:**
- **Role**: Translates business requirements into actionable user stories and acceptance criteria
- **Skills**: Requirements analysis, user story writing, prioritization (MoSCoW), stakeholder communication
- **Outputs**: Product backlog, user stories, acceptance criteria, sprint plans
- **Communicates with**: UX Designer (requirements handoff), Customer Acceptance Engineer (acceptance criteria review), DevOps (release planning)

**Key Responsibilities:**
- Define product vision and roadmap
- Write and prioritize user stories with clear acceptance criteria
- Break down epics into sprint-sized stories
- Validate that delivered features meet business requirements
- Manage dependency tracking across roles

**Must-Have MCPs:**
- Jira/Linear integration for backlog management
- Documentation generator for PRDs
- Stakeholder notification system

---

### 3.2 UX Designer Agent

**Profile:**
- **Role**: Creates user experience flows, wireframes, and interaction specifications
- **Skills**: User research synthesis, information architecture, wireframing, usability heuristics
- **Outputs**: User flows, wireframes, interaction specs, usability test plans
- **Communicates with**: Product Manager (requirement clarification), UI Developer (design handoff), Customer Acceptance Engineer (UX acceptance criteria)

**Key Responsibilities:**
- Translate user stories into visual user flows
- Create wireframes and interaction specifications
- Define usability acceptance criteria
- Conduct heuristic evaluations of proposed designs
- Ensure accessibility compliance (WCAG 2.1 AA)

**Must-Have MCPs:**
- Design system integration (Figma/Storybook)
- Accessibility checker
- User flow diagram generator

---

### 3.3 UI Developer Agent

**Profile:**
- **Role**: Implements frontend interfaces from design specifications
- **Skills**: React/TypeScript, CSS/Tailwind, component architecture, responsive design, accessibility
- **Outputs**: Frontend components, pages, integration with backend APIs
- **Communicates with**: UX Designer (design clarification), Backend Engineer (API contracts), UI Test Engineer (test scenarios)

**Key Responsibilities:**
- Build responsive, accessible UI components
- Implement design system components
- Integrate with backend APIs
- Write unit tests for UI components
- Ensure cross-browser compatibility

**Must-Have MCPs:**
- Component library manager
- Visual regression tester
- Accessibility auditor
- API contract validator

---

### 3.4 Backend Engineer Agent

**Profile:**
- **Role**: Designs and implements server-side logic, APIs, and data models
- **Skills**: API design (REST/GraphQL), database design, authentication, caching, microservices
- **Outputs**: API endpoints, database schemas, business logic, service integrations
- **Communicates with**: UI Developer (API contracts), Backend Test Engineer (test scenarios), SecOps Engineer (security requirements), DevOps Engineer (deployment configs)

**Key Responsibilities:**
- Design and implement REST/GraphQL APIs
- Create and migrate database schemas
- Implement authentication and authorization
- Write business logic services
- Optimize query performance
- Document API specifications (OpenAPI/Swagger)

**Must-Have MCPs:**
- API documentation generator
- Database migration tool
- Code quality analyzer
- Performance profiler

---

### 3.5 Backend Test Engineer Agent

**Profile:**
- **Role**: Designs and executes automated backend tests
- **Skills**: API testing, database testing, load testing, test automation frameworks
- **Outputs**: Test suites, test reports, defect reports, coverage metrics
- **Communicates with**: Backend Engineer (test scenarios), DevOps Engineer (CI integration), Product Manager (acceptance validation)

**Key Responsibilities:**
- Write API integration tests (REST/GraphQL)
- Create database test scenarios
- Implement load and stress tests
- Maintain test automation frameworks
- Track code coverage and quality metrics
- Report defects with reproduction steps

**Must-Have MCPs:**
- Test framework runner (Pytest/Jest)
- API test generator (from OpenAPI specs)
- Coverage report generator
- Defect tracker integration

---

### 3.6 UI Test Engineer Agent

**Profile:**
- **role**: Designs and executes automated UI tests
- **Skills**: E2E testing, visual regression, accessibility testing, cross-browser testing
- **Outputs**: E2E test suites, visual regression reports, accessibility audit reports
- **Communicates with**: UI Developer (test scenarios), UX Designer (UX validation), DevOps Engineer (CI integration)

**Key Responsibilities:**
- Write E2E tests (Playwright/Cypress)
- Implement visual regression testing
- Conduct accessibility audits
- Perform cross-browser testing
- Create test data management scripts
- Report UI defects with screenshots

**Must-Have MCPs:**
- E2E test runner (Playwright/Cypress)
- Visual regression tool (Percy/Chromatic)
- Accessibility auditor (axe-core)
- Screenshot comparison tool

---

### 3.7 DevOps Engineer Agent

**Profile:**
- **Role**: Manages CI/CD pipelines, infrastructure, and deployment automation
- **Skills**: Docker, Kubernetes, Terraform, CI/CD, monitoring, infrastructure as code
- **Outputs**: CI/CD pipelines, infrastructure configs, deployment scripts, monitoring dashboards
- **Communicates with**: All agents (deployment status, build results), SecOps Engineer (security gates)

**Key Responsibilities:**
- Design and maintain CI/CD pipelines
- Manage container orchestration (Kubernetes)
- Implement infrastructure as code (Terraform)
- Set up monitoring and alerting
- Manage environment promotions (dev → staging → prod)
- Optimize build and deployment times

**Must-Have MCPs:**
- CI/CD pipeline manager (GitHub Actions/Jenkins)
- Container registry integration
- Infrastructure state manager
- Monitoring dashboard generator
- Deployment status notifier

---

### 3.8 SecOps Engineer Agent

**Profile:**
- **Role**: Ensures security throughout the development lifecycle
- **Skills**: Static analysis, dependency scanning, vulnerability management, compliance, threat modeling
- **Outputs**: Security scan reports, vulnerability assessments, compliance reports, security recommendations
- **Communicates with**: All engineering agents (security findings), DevOps Engineer (security gates in CI/CD)

**Key Responsibilities:**
- Run static application security testing (SAST)
- Scan dependencies for vulnerabilities (SCA)
- Perform container image scanning
- Validate security configurations
- Ensure compliance with standards (OWASP, SOC 2)
- Review and approve security-critical changes

**Must-Have MCPs:**
- SAST scanner (SonarQube/CodeQL)
- Dependency vulnerability scanner (Snyk/Dependabot)
- Container scanner (Trivy)
- Secret scanner
- Compliance checker

---

### 3.9 Customer Acceptance Engineer Agent

**Profile:**
- **Role**: Validates that delivered features meet customer requirements and acceptance criteria
- **Skills**: User acceptance testing, requirements validation, customer communication, defect triage
- **Outputs**: Acceptance test reports, customer sign-off documents, release readiness assessments
- **Communicates with**: Product Manager (acceptance criteria), all engineering agents (validation results), Customer Success (feedback)

**Key Responsibilities:**
- Execute acceptance tests against defined criteria
- Validate features against user stories
- Conduct UAT sessions with stakeholders
- Track and triage acceptance defects
- Provide release readiness assessments
- Gather and synthesize customer feedback

**Must-Have MCPs:**
- Acceptance test runner
- Requirements traceability matrix
- Defect triage system
- Customer feedback aggregator

---

### 3.10 Architect Agent (Additional)

**Profile:**
- **Role**: Defines system architecture, technology choices, and design patterns
- **Skills**: System design, architecture patterns, technology evaluation, technical debt management
- **Outputs**: Architecture decision records (ADRs), system diagrams, technology recommendations
- **Communicates with**: All engineering agents (architecture guidance), Product Manager (technical feasibility)

**Key Responsibilities:**
- Define system architecture and patterns
- Make technology stack decisions
- Review architectural changes
- Manage technical debt
- Ensure scalability and maintainability
- Create architecture decision records

---

### 3.11 Developer Agent (Additional)

**Profile:**
- **Role**: General-purpose coding agent for tasks not covered by specialized roles
- **Skills**: Full-stack development, scripting, documentation, code review
- **Outputs**: Code, scripts, documentation, code review comments
- **Communicates with**: All agents (code contributions, status updates)

**Key Responsibilities:**
- Implement features across the stack
- Write scripts and automation
- Create documentation
- Perform code reviews
- Fix bugs and technical debt

---

## 4. Inter-Agent Communication Protocol

### 4.1 Communication Channels

Agents communicate through a **structured message bus**:

```
┌─────────────────────────────────────────────────┐
│                 Message Bus                      │
│                                                  │
│  Topic: feature-requests    ← Product Manager    │
│  Topic: design-specs        ← UX Designer        │
│  Topic: api-contracts       ← Backend Engineer   │
│  Topic: build-status        ← DevOps Engineer    │
│  Topic: security-findings   ← SecOps Engineer    │
│  Topic: test-results        ← Test Engineers     │
│  Topic: acceptance-status   ← Customer Acceptance│
│  Topic: architecture-advice ← Architect          │
└─────────────────────────────────────────────────┘
```

### 4.2 Message Format

All inter-agent messages follow a structured format:

```json
{
  "from": "backend-engineer",
  "to": "ui-developer",
  "topic": "api-contracts",
  "timestamp": "2026-07-11T18:00:00Z",
  "priority": "high",
  "payload": {
    "type": "api-contract-update",
    "endpoint": "/api/v1/users",
    "method": "GET",
    "response_schema": {...},
    "changes": ["added pagination", "deprecated field: email"]
  },
  "requires_action": true,
  "deadline": "2026-07-11T20:00:00Z"
}
```

### 4.3 Status Update Flow

Each agent publishes status updates at key milestones:

1. **Product Manager**: "User story #123 moved to In Progress"
2. **UX Designer**: "Wireframes for #123 ready for review"
3. **UI Developer**: "Component X implemented, awaiting API contract"
4. **Backend Engineer**: "API endpoint /users ready for testing"
5. **Test Engineers**: "Test suite passed, 95% coverage"
6. **SecOps**: "Security scan clean, 0 critical findings"
7. **DevOps**: "Build #456 deployed to staging"
8. **Customer Acceptance**: "Acceptance criteria met, ready for sign-off"

---

## 5. The Loop Design

### 5.1 Loop Phases

```
┌──────────────────────────────────────────────────────────────┐
│                        LOOP START                             │
│                                                               │
│  Phase 1: REQUIREMENT (Product Manager)                       │
│    ├── Write user story with acceptance criteria              │
│    ├── Validate with Architect (technical feasibility)        │
│    └── Publish to message bus                                 │
│                                                               │
│  Phase 2: DESIGN (UX Designer)                                │
│    ├── Create user flows and wireframes                       │
│    ├── Define accessibility requirements                      │
│    └── Publish design specs to message bus                    │
│                                                               │
│  Phase 3: IMPLEMENT (Parallel)                                │
│    ├── UI Developer: Build frontend components                │
│    ├── Backend Engineer: Implement APIs and logic             │
│    └── Both sync via API contracts                            │
│                                                               │
│  Phase 4: TEST (Parallel)                                     │
│    ├── Backend Test Engineer: API + integration tests         │
│    ├── UI Test Engineer: E2E + visual regression tests        │
│    └── Publish test results to message bus                    │
│                                                               │
│  Phase 5: SECURITY (SecOps)                                   │
│    ├── SAST + SCA scans                                       │
│    ├── Container image scanning                               │
│    └── Gate: Must pass all security checks                    │
│                                                               │
│  Phase 6: DEPLOY (DevOps)                                     │
│    ├── Build and containerize                                 │
│    ├── Deploy to staging environment                          │
│    └── Publish deployment status                              │
│                                                               │
│  Phase 7: ACCEPT (Customer Acceptance Engineer)               │
│    ├── Execute acceptance tests                               │
│    ├── Validate against user story criteria                   │
│    └── Publish acceptance result (Pass/Fail)                  │
│                                                               │
│  Phase 8: FEEDBACK                                            │
│    ├── If Pass: Move to Done, notify all agents               │
│    └── If Fail: Route to appropriate role for fix, re-loop    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Loop Orchestration

The loop is orchestrated by a **Loop Coordinator** (can be a dedicated agent or the Developer agent):

1. **Triggers** a new iteration when a user story is ready
2. **Routes** artifacts between agents based on completion status
3. **Monitors** phase durations and escalates if blocked
4. **Aggregates** results from all phases
5. **Decides** whether to proceed, loop back, or escalate to human

### 5.3 State Management

Shared state is maintained in a **workspace directory**:

```
workspace/
├── backlog/
│   ├── story-001.md          # User story with acceptance criteria
│   └── story-002.md
├── designs/
│   ├── story-001/
│   │   ├── user-flow.svg
│   │   └── wireframes.md
│   └── story-002/
├── code/
│   ├── frontend/
│   └── backend/
├── tests/
│   ├── api-tests/
│   └── ui-tests/
├── reports/
│   ├── security-scan.md
│   ├── test-results.md
│   └── acceptance.md
└── status.json               # Current loop state
```

---

## 6. Best Practices

### 6.1 Agent Design

1. **Single Responsibility**: Each agent should have one clear domain of expertise
2. **Structured Profiles**: Use YAML/JSON profiles with explicit skills, constraints, and output formats
3. **Bounded Context**: Agents should not overstep their role boundaries
4. **Idempotent Actions**: Agent actions should be repeatable without side effects
5. **Fallback Chains**: Each agent should have a degradation path if primary tools fail

### 6.2 Communication

1. **Structured Messages**: Always use typed, structured messages — never free-form chat between agents
2. **Async-First**: Agents should work asynchronously; don't block on synchronous responses
3. **Event-Driven**: Use event publishing for status changes; agents subscribe to relevant topics
4. **Message TTL**: Set expiration on messages to prevent stale information
5. **Acknowledgment**: Require explicit acknowledgment for critical messages

### 6.3 Loop Management

1. **Phase Gates**: Each phase must pass explicit criteria before proceeding
2. **Parallel Execution**: Independent phases (UI + Backend development) should run in parallel
3. **Timeouts**: Set maximum duration for each phase to prevent infinite loops
4. **Escalation Path**: Define clear escalation to human when agents disagree or are stuck
5. **Metrics**: Track cycle time, defect rate, and pass rate per phase

### 6.4 Quality Assurance

1. **Automated Gates**: Security scans, test coverage, and linting must pass automatically
2. **Definition of Done**: Clear criteria for each role's deliverables
3. **Peer Review**: At least one agent review before moving to next phase
4. **Regression Testing**: Every loop iteration must re-run the full test suite
5. **Audit Trail**: All agent actions and decisions must be logged

### 6.5 Security

1. **Shift Left**: Security scanning starts in Phase 3 (Implementation), not Phase 5
2. **Least Privilege**: Each agent has minimal permissions needed for its role
3. **Secrets Management**: No secrets in agent profiles or messages
4. **Supply Chain**: Scan all dependencies at every loop iteration
5. **Compliance**: Automated compliance checks for regulated data

---

## 7. Skillsets by Role

### Product Manager
- Requirements engineering (BABOK, user story mapping)
- Prioritization frameworks (MoSCoW, RICE, WSJF)
- Stakeholder management and communication
- Agile/Scrum methodology
- Data-driven decision making
- Basic technical literacy (APIs, databases, architecture concepts)

### UX Designer
- User research synthesis
- Information architecture
- Wireframing and prototyping
- Interaction design principles
- Accessibility standards (WCAG 2.1)
- Usability testing methodology
- Design system thinking

### UI Developer
- React/TypeScript or Vue/Angular
- CSS/Tailwind/Styled Components
- Component-driven development
- Responsive and adaptive design
- Accessibility implementation
- State management (Redux, Zustand, Context)
- Performance optimization (lazy loading, code splitting)

### Backend Engineer
- API design (REST, GraphQL, gRPC)
- Database design (SQL and NoSQL)
- Authentication and authorization (OAuth2, JWT)
- Caching strategies (Redis, CDN)
- Microservices architecture
- Message queues (Kafka, RabbitMQ)
- Observability (logging, metrics, tracing)

### Backend Test Engineer
- API testing frameworks (Pytest, Jest, Supertest)
- Database testing and migration testing
- Load testing (k6, JMeter, Locust)
- Test data management
- CI/CD test integration
- Code coverage analysis
- Contract testing (Pact)

### UI Test Engineer
- E2E frameworks (Playwright, Cypress, Selenium)
- Visual regression testing (Percy, Chromatic)
- Accessibility testing (axe-core, Lighthouse)
- Cross-browser testing
- Test data generation
- Component testing (React Testing Library, Vitest)
- Performance testing (Lighthouse CI)

### DevOps Engineer
- Containerization (Docker, Podman)
- Orchestration (Kubernetes, Docker Compose)
- CI/CD (GitHub Actions, GitLab CI, Jenkins)
- Infrastructure as Code (Terraform, Pulumi)
- Monitoring (Prometheus, Grafana, Datadog)
- Log management (ELK, Loki)
- Cloud platforms (AWS, GCP, Azure)

### SecOps Engineer
- SAST tools (SonarQube, CodeQL, Semgrep)
- SCA tools (Snyk, Dependabot, Trivy)
- Container security (Trivy, Clair)
- Secret scanning (Gitleaks, TruffleHog)
- Compliance frameworks (OWASP, SOC 2, ISO 27001)
- Threat modeling (STRIDE, DREAD)
- Incident response procedures

### Customer Acceptance Engineer
- User acceptance testing methodology
- Requirements traceability
- Defect triage and prioritization
- Stakeholder communication
- Release readiness assessment
- Customer feedback synthesis
- Documentation and reporting

### Architect
- System design patterns (microservices, event-driven, CQRS)
- Technology evaluation and selection
- Architecture decision records (ADRs)
- Technical debt management
- Scalability and performance planning
- Integration patterns
- Cloud architecture best practices

### Developer
- Full-stack development capabilities
- Scripting and automation
- Documentation writing
- Code review practices
- Debugging and troubleshooting
- Version control (Git workflows)
- Cross-cutting concern implementation

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Define agent profiles in YAML/JSON
- Set up message bus infrastructure
- Create shared workspace structure
- Implement basic loop coordinator

### Phase 2: Core Roles (Weeks 3-4)
- Implement Product Manager, UX Designer, Backend Engineer, UI Developer
- Establish API contract communication
- Set up CI/CD pipeline
- Implement basic test automation

### Phase 3: Quality & Security (Weeks 5-6)
- Add Backend Test Engineer and UI Test Engineer
- Integrate SecOps scanning tools
- Implement security gates in CI/CD
- Add visual regression testing

### Phase 4: Operations (Weeks 7-8)
- Implement DevOps Engineer automation
- Add Customer Acceptance Engineer workflow
- Set up monitoring and alerting
- Implement deployment automation

### Phase 5: Optimization (Weeks 9-10)
- Add Architect agent for design review
- Implement Developer agent for general tasks
- Optimize loop parallelism
- Add metrics and dashboards
- Human-in-the-loop escalation paths

---

## 9. Key Challenges and Mitigations

| Challenge | Mitigation |
|----------|------------|
| Agent hallucination in role-specific tasks | Constrain agents with explicit profiles and validation gates |
| Communication overhead between agents | Use async message bus with topic-based routing |
| Loop getting stuck in infinite cycles | Implement phase timeouts and escalation to human |
| Security bypass through agent manipulation | Enforce security gates that cannot be overridden by agents |
| Context window limits for complex tasks | Chunk tasks into smaller, focused agent interactions |
| Inconsistent output formats | Define strict output schemas for each agent role |
| Resource contention (API calls, compute) | Implement rate limiting and queue management |

---

## 10. Future Outlook

Loop engineering with multi-agent systems represents the next evolution in AI-assisted development. As agent capabilities mature, we can expect:

- **Self-healing loops**: Agents that detect and fix issues without human intervention
- **Adaptive role assignment**: Dynamic role reassignment based on task complexity
- **Cross-project knowledge sharing**: Agents learning from patterns across multiple projects
- **Predictive planning**: Agents forecasting bottlenecks and optimizing loop flow
- **Multi-modal agents**: Agents that can process code, designs, documents, and conversations simultaneously
- **Autonomous scaling**: Loop orchestration that scales agent count based on workload

The Hermes Agent framework provides the foundation for building these systems, but success depends on careful role design, robust communication protocols, and disciplined loop management.

---

## 11. References

1. Hermes Agent Documentation — Agent framework for role-based AI orchestration
2. Loop Engineering: The Paradigm Shift from Prompt to Continuous AI Development
3. Multi-Agent Systems in Software Engineering — Research on agent collaboration patterns
4. OWASP Top 10 — Application security risks and mitigation strategies
5. WCAG 2.1 Guidelines — Web accessibility standards
6. CI/CD Best Practices — Continuous integration and deployment patterns
7. Microservices Architecture Patterns — System design for distributed applications
8. Test-Driven Development — Agile testing methodology
9. Infrastructure as Code — Terraform and Pulumi best practices
10. Security Shift Left — Integrating security into early development phases
11. Agent Communication Protocols — Structured messaging for AI agents
12. Human-in-the-Loop AI — Balancing automation with human oversight
13. Design System Architecture — Scalable component libraries
14. API Contract Testing — Ensuring interface compatibility
15. Visual Regression Testing — Automated UI change detection
16. Container Security — Scanning and hardening container images
17. Kubernetes Operations — Production-grade orchestration
18. Observability Engineering — Monitoring, logging, and tracing
19. Requirements Engineering — User story and acceptance criteria best practices
20. UX Research Methods — Synthesizing user research into design decisions
21. Accessibility Testing — Automated and manual accessibility validation
22. Load Testing Methodology — Performance testing at scale
23. Threat Modeling — STRIDE and DREAD frameworks
24. Compliance Automation — Automated security and regulatory checks
25. Technical Debt Management — Identifying and reducing technical debt
26. Architecture Decision Records — Documenting architectural choices
27. Release Readiness Assessment — Criteria for production deployment
28. Customer Feedback Loops — Synthesizing user feedback into product improvements
29. Agent Profile Design — Structuring AI agent roles and capabilities
30. Multi-Agent Orchestration — Coordinating multiple AI agents in workflows
