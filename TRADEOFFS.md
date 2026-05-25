# TRADEOFFS.md - What We Deliberately Did NOT Build and Why

This document explains three significant features that were explicitly left out of the MVP, the reasoning, and what would be needed to add them later.

---

## 1. Emissions Calculation Engine

### What We Did NOT Build
A system that:
- Takes normalized energy/travel/material data
- Applies emissions factors (from EPA, DEFRA, etc.)
- Calculates and stores CO2e (carbon dioxide equivalent)
- Generates emissions reports by scope, category, facility, etc.

### Current State
The platform prepares data: normalized quantities in standard units (kWh, L, km, nights), properly scoped (Scope 1/2/3), with complete audit trail.

Example output:
```json
{
  "data_type": "FLIGHT",
  "scope": "SCOPE_3",
  "category_code": "3.6",
  "distance_km": 5570,
  "cabin_class": "business",
  "amount": 5570,
  "unit": "KM",
  "date": "2025-02-15"
}
```

What the client must do:
1. Extract rows from our API
2. Apply their emissions factors (EPA, DEFRA, ISO 14064, etc.)
3. Calculate: 5570 km × business_factor × RFI_multiplier × co2_factor = kg CO2e
4. Load into their ESG reporting system

### Why Not Include It

1. **Emissions Factors Are Volatile**
   - EPA factors update yearly
   - DEFRA factors update quarterly
   - ISO 14064 varies by certification body
   - If we embed factors, they become outdated quickly
   - Maintenance burden falls on us

2. **Factors Vary By Standard**
   - EPA uses different factors than DEFRA than ISO
   - Client must use their chosen standard
   - We can't know which they prefer
   - Embedding one standard alienates others

3. **Regional Factors Matter**
   - Electricity emissions depend on grid mix
   - UK grid = 150g CO2/kWh (mostly renewables)
   - Poland grid = 500g CO2/kWh (mostly coal)
   - US grid = 200-400g depending on state/utility
   - Can't embed static factors

4. **Custom Factors Are Common**
   - Large orgs negotiate with grid operators
   - Some use supplier-specific factors (renewable contracts)
   - Some use forward-looking factors (future grid mix)
   - Enforcement: "use EPA factors by default" leads to friction

5. **Our Core Strength is Data Ingestion, Not Emissions**
   - We're good at parsing messy data and normalizing it
   - Emissions calculation is separate expertise
   - Libraries like Scopes or Normalization already solve this
   - Avoids mission creep

### What Would Be Needed to Add It Later

**Simple version** (6-8 weeks):
- Add `EmissionsRow` model to store calculated emissions
- Embed EPA factors as JSON config
- Add calculation endpoint: POST `/api/emissions/calculate/`
- Return: kg CO2e by scope/category
- Basic audit trail

**Production version** (3-4 months):
- Support multiple factor libraries (EPA, DEFRA, ISO)
- Regional factor selection (pick country/utility)
- Custom factor upload per org
- Versioning (factors updated, can recalculate historical data)
- Benchmarking (compare org's emissions to peers)
- Scenario planning (what-if: renewable energy contracts?)

**Integration** (1-2 months):
- API to export emissions to ESG platforms (CDP, EcoVadis, etc.)
- Reports: by scope, category, facility, time period
- Drill-down: from total emissions → energy source → specific purchases

### Risk of Not Including It

**Minimal risk:**
- Analyst has clean data, can do calculations in Excel if needed
- Encourages clients to use their preferred ESG platform
- Reduces scope creep
- Not in assignment requirements

---

## 2. User Authentication and Role-Based Access Control

### What We Did NOT Build
- User login system (email/password or SSO)
- Role definitions (Analyst, Manager, Admin)
- Permission checks (Analyst can approve, Manager can configure sources)
- Audit logging of "who did what"
- Multi-org support with admin isolation

### Current State
Single shared instance:
```
GET /api/organizations/?org_id=org-acme-001
```

No authentication. Assumes analyst is trusted (local deployment or internal network).

### Why Not Include It

1. **Out of Assignment Scope**
   - Assignment: "prototype in Django and React"
   - Build data ingestion and analyst review
   - Authentication not mentioned

2. **Deployment Model Uncertainty**
   - Is this single-tenant (one client per deployment)?
   - Is this multi-tenant SaaS (many clients)?
   - If SaaS, do they use Auth0, Okta, or internal auth?
   - Can't design without knowing deployment model

3. **Security Complexity**
   - Requires HTTPS/TLS in production
   - Password hashing, session management
   - CSRF protection, rate limiting
   - Could introduce vulnerabilities if done poorly

4. **Different Auth Per Client**
   - Enterprise clients want SSO (Okta, Azure AD)
   - Mid-market want email/password
   - SMBs want API keys
   - Can't solve all at once

5. **Standard Stack Available**
   - If needed, use Django-allauth or Django-rest-auth
   - Or integrate with Auth0 / Okta
   - No need to build it from scratch

### What Would Be Needed to Add It Later

**Basic email/password auth** (4-5 weeks):
- User model (email, password_hash, org_id)
- Login endpoint: POST `/api/login/` → JWT token
- Middleware to check JWT on every request
- CORS configuration for token
- Logout endpoint
- Password reset flow

**Role-based permissions** (3-4 weeks):
- Role model (Analyst, Manager, Admin per org)
- Permission matrix:
  - Analyst: read rows, approve, flag, can't configure sources
  - Manager: everything + configure sources, delete rows
  - Admin: everything + add users
- Decorator to check permissions on endpoints

**SSO integration** (2-3 weeks):
- Add Auth0 or Okta connector
- Use OIDC/OAuth2 flow
- Map Auth0 groups to roles
- Keep email as org membership key

**Audit trail of approvals** (1-2 weeks):
- ApprovalLog already captures "approved_by" field
- Just need user object instead of string
- Probably already working

### Risk of Not Including It

**Moderate risk:**
- Can't deploy to shared environment (everyone sees all data)
- Can't verify who approved what (audit trail weak)
- Not suitable for multi-client SaaS

**Mitigation:**
- Document: "This is single-tenant prototype, add auth before multi-tenant deployment"
- Provide architecture sketch: where to add auth middleware
- Make sure org_id is set correctly (even without login, could hardcode in dev)

---

## 3. Automatic Data Reconciliation and Correction

### What We Did NOT Build
- Matching rows from different sources to same activity
- Correction of obviously wrong values
- Reconciliation against client's internal records
- Automatic de-duplication across sources

### Current State
- Each source ingested independently
- Rows flagged if they look wrong, but not corrected
- Analyst must manually verify and approve
- Example: SAP says "1500 L Diesel", Utility says "60 kWh Electricity" - both marked as Scope 2, but SAP should be Scope 1

### Why Not Include It

1. **Requires Domain Expertise We Don't Have**
   - We don't know what "legitimate" data looks like for their business
   - We don't know their facility structure, cost centers, etc.
   - Automated "correction" might corrupt data

2. **Liability Risk**
   - If we auto-correct and get it wrong, who's responsible?
   - Analyst must verify anyway, so automation saves no effort
   - Better to flag and let analyst decide

3. **Cross-Source Reconciliation Is Hard**
   - SAP might say "500 L Diesel"
   - Vendor invoice might say "450 L Diesel" (20% margin for blending)
   - Are they same activity or different vendors?
   - Depends on business process we don't know

4. **Audit Trail Becomes Murky**
   - If system auto-corrects, auditor asks: "Why?"
   - If reasons are embedded, hard to audit
   - Better to show original and ask analyst to approve

5. **Each Client's Rules Are Different**
   - Some clients accept "estimated" meter reads
   - Others require "actual" only
   - Some consolidate multiple facilities per meter
   - Others keep them separate
   - Can't automate without per-client config

### What Would Be Needed to Add It Later

**Duplicate detection across sources** (3-4 weeks):
- Model: `ReconciliationRule` (org_id, match_fields, confidence_threshold)
- Example: "If SAP fuel + Utility electricity same date ± 2 days, same location, mark as potential duplicate"
- ML: fuzzy matching on facility names, dates, amounts
- Frontend: show suggested matches, analyst clicks to merge
- ApprovalLog: track merges for audit trail

**Value correction** (4-5 weeks):
- Common corrections:
  - Typo: "1500" should be "150" (spike detection)
  - Unit: "1500" reported as kg but usually L (material history)
  - Format: "01.02.2024" (European) reported as "2024-01-02" (parsed wrong)
- For each: show suggestion, analyst approves or rejects
- Audit: what was original, what was corrected, by whom

**Reconciliation against internal records** (6-8 weeks):
- Client uploads "master file" (what they think is true)
- System compares ingested data to master
- Flags mismatches: "Your account shows $5000 in fuel, we ingested $4800"
- Analyst investigates discrepancy
- Requires integration with client's ERP/GL

### Risk of Not Including It

**Low risk for MVP:**
- Analyst can manually review, no big deal for 28 sample rows
- In production (~1000 rows/month), analyst time is 1-2 hours, acceptable
- Better to let analyst handle than risk auto-corruption

**Future burden:**
- If dataset grows to 10K+ rows/month, manual review becomes painful
- At that point, implement reconciliation engine
- Price it as paid feature (high-value for enterprise)

---

## Trade-Off Matrix

| Feature | Effort | Risk | Value | Decision |
|---------|--------|------|-------|----------|
| **Emissions Calc** | 8-12 weeks | Medium (factors outdated) | High | Later |
| **User Auth** | 4-6 weeks | Medium (if poorly done) | High | Later |
| **Reconciliation** | 8-12 weeks | Low (just suggestions) | Medium | Later |
| **API Docs** | 1-2 weeks | Low | Medium | Included |
| **Sample Data** | 2-3 weeks | Low | High | Included |
| **Data Flagging** | 3-4 weeks | Low | High | Included |
| **Approval Workflow** | 2-3 weeks | Low | High | Included |

---

## What We DID Build

(And why these were prioritized)

### 1. Data Ingestion from 3 Sources ✓
- **Why Essential**: Core requirement
- **Effort**: 6 weeks
- **Risk**: Low (well-defined formats)
- **Value**: Enables everything else

### 2. Data Normalization ✓
- **Why Essential**: Core requirement
- **Effort**: 4 weeks
- **Risk**: Low (clear rules)
- **Value**: Makes downstream work possible

### 3. Analyst Review Dashboard ✓
- **Why Essential**: Core requirement
- **Effort**: 3 weeks
- **Risk**: Low (UI is straightforward)
- **Value**: Let's analysts see data

### 4. Approval Workflow ✓
- **Why Essential**: Core requirement
- **Effort**: 2 weeks
- **Risk**: Low
- **Value**: Auditable approval

### 5. Data Quality Flagging ✓
- **Why Important**: Catches issues early
- **Effort**: 3 weeks
- **Risk**: Low (explicit rules)
- **Value**: Saves analyst time

### 6. Audit Trail ✓
- **Why Important**: Required for compliance
- **Effort**: 2 weeks
- **Risk**: Low
- **Value**: Auditors need this

---

## Recommendations for Future Prioritization

### If Client Wants Single Feature Next
1. **User Authentication** (highest ROI): Required for multi-client SaaS
2. **Emissions Calculation** (nice-to-have): Client probably has this elsewhere
3. **Reconciliation** (scales with volume): Important at 1000+ rows/month

### If Scaling Beyond MVP
1. Add user auth (security)
2. Add role-based access (multi-client support)
3. Add emissions calc (complete solution)
4. Add reconciliation (operational efficiency)

### If Client Feedback Suggests Urgency
1. **Highest Priority**: What's failing during pilot?
   - Data parsing breaking? → Improve parsers
   - Analyst workflow too slow? → Add bulk operations
   - Auditor unhappy? → Improve audit trail
2. **Medium Priority**: What would increase usage?
   - Hard to see data? → Better filtering/search
   - Hard to understand flags? → Better UX
3. **Lower Priority**: Feature requests (usually not urgent)

---

## Summary

Three major features were left out:

1. **Emissions Calculation** - Not our domain, factors are volatile, client likely has own standard
2. **User Authentication** - Out of assignment scope, deployment model unclear, many ways to solve
3. **Reconciliation** - Risky to automate, analyst review is safer, adds value only at scale

All three are implementable in 4-12 weeks if needed. But MVP prioritized getting data in, normalized, reviewed, and approved. That's the foundation everything else builds on.

The goal: **a sharp MVP that does one thing well**, not a bloated system that tries to do everything poorly.
