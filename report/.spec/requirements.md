# Odoo Module Requirements Document - test_app

## Module Overview

**Module Name:** test_app
**Odoo Version:** 17.0
**Module Version:** 1.0.0
**Developer:** Internal Development Team
**Category:** Procurement

## Business Requirements Alignment

### Business Process Impact
This module introduces a comprehensive material request workflow that bridges the gap between employee material needs and vendor purchasing. In standard Odoo, there's no intermediate "Material Request" step - the procurement system goes directly from needs to purchase orders. This module adds:

1. **Employee Material Request** - Employees can request materials they need for their work
2. **Manager Approval** - Managers review and approve/reject material requests
3. **Purchase Request Consolidation** - Procurement officers consolidate approved requests by vendor
4. **Purchase Order Generation** - Approved purchase requests convert to standard purchase orders

This workflow provides visibility into internal needs, approval controls, and better procurement planning by aggregating requests before committing to vendors.

### ROI Assessment
- **Expected Benefits:**
  - 30% reduction in emergency/rush purchases through better planning
  - 20% cost savings through bulk ordering consolidated requests
  - Improved budget control with approval workflow
  - Complete audit trail of material requests to purchase orders
- **Implementation Cost:** 40-60 hours development + 20 hours testing
- **Payback Period:** 3-6 months through cost savings and efficiency gains

## Functional Requirements

### FR-1: Material Request Management

**User Story:** As an employee, I want to request materials I need for my work, so that I can get the resources required to perform my job duties.

#### Acceptance Criteria
1. **WHEN** an employee creates a material request, **THEN** the system should automatically assign their employee record and department
2. **IF** a material request is in draft state, **THEN** the employee should be able to edit products, quantities, and required date
3. **WHEN** an employee submits a material request, **THEN** the system should change state to 'submitted' and notify the department manager
4. **WHEN** a material request has all lines fulfilled via purchase orders, **THEN** the system should automatically mark it as 'done'

#### Business Rules
- **BR-1.1:** Only employees with active employee records can create material requests
- **BR-1.2:** Material requests must have at least one line item to be submitted
- **BR-1.3:** Draft material requests can be deleted by the creator; submitted/approved requests cannot be deleted
- **BR-1.4:** Each material request line must specify product, quantity, UOM, and estimated cost
- **BR-1.5:** Material requests are tracked by department for reporting and budget allocation
- **BR-1.6:** Integration with HR module required for employee and department data

#### Data Requirements
```python
# Material Request Model
material_request = {
    'name': 'Char, required, unique, auto-sequence (MR/####)',
    'employee_id': 'Many2one(hr.employee), required, default=current_user.employee',
    'department_id': 'Many2one(hr.department), related to employee, stored',
    'date_requested': 'Date, required, default=today',
    'date_required': 'Date, required',
    'reason': 'Text, optional, describe why materials needed',
    'state': 'Selection(draft/submitted/approved/rejected/done), default=draft, tracked',
    'line_ids': 'One2many(test_app.material.request.line), required',
    'total_estimated_cost': 'Monetary, computed from lines, stored',
    'currency_id': 'Many2one(res.currency), required, default=company_currency',
    'company_id': 'Many2one(res.company), required, default=user_company',
    'purchase_request_id': 'Many2one(test_app.purchase.request), readonly',
    'purchase_order_id': 'Many2one(purchase.order), computed via purchase_request',
    'approved_by': 'Many2one(res.users), set when approved',
    'approved_date': 'Datetime, set when approved',
    'rejected_reason': 'Text, required when rejected',
}

# Material Request Line Model
material_request_line = {
    'material_request_id': 'Many2one(test_app.material.request), required, cascade',
    'product_id': 'Many2one(product.product), required',
    'description': 'Text, optional, additional notes',
    'quantity': 'Float, required, default=1.0, digits=Product_UOM',
    'uom_id': 'Many2one(uom.uom), required, domain=product_uom_category',
    'estimated_unit_cost': 'Monetary, optional, employee estimate',
    'estimated_total_cost': 'Monetary, computed=quantity*unit_cost, stored',
    'currency_id': 'Many2one, related to material_request',
    'purchase_request_line_id': 'Many2one(test_app.purchase.request.line), readonly',
    'state': 'Selection, related to material_request for filtering',
}
```

### FR-2: Material Request Approval Workflow

**User Story:** As a department manager, I want to review and approve/reject material requests from my team, so that I can control spending and ensure requests are legitimate.

#### Acceptance Criteria
1. **WHEN** a material request is submitted, **THEN** managers with approval rights should receive a notification
2. **IF** a manager approves a material request, **THEN** the system should change state to 'approved' and make it available for purchase request creation
3. **WHEN** a manager rejects a material request, **THEN** the system should require a rejection reason and notify the requesting employee
4. **WHEN** a manager views material requests, **THEN** the system should show requests from their department by default
5. **IF** a material request is approved, **THEN** it should no longer be editable by the requesting employee

#### Business Rules
- **BR-2.1:** Only users in 'Material Request Manager' group can approve/reject requests
- **BR-2.2:** Managers can approve requests from any department (not restricted to their own)
- **BR-2.3:** Rejection requires a text reason to provide feedback to employee
- **BR-2.4:** Approval records timestamp and approving user for audit trail
- **BR-2.5:** Approved requests remain in approved state until converted to purchase request
- **BR-2.6:** Bulk approval wizard available to approve multiple requests at once

### FR-3: Purchase Request Creation

**User Story:** As a procurement officer, I want to consolidate approved material requests into purchase requests grouped by vendor, so that I can efficiently create purchase orders.

#### Acceptance Criteria
1. **WHEN** creating a purchase request, **THEN** the system should show all approved material requests not yet linked to a purchase request
2. **IF** multiple material requests contain the same product, **THEN** the purchase request should consolidate quantities into a single line
3. **WHEN** a purchase request is created, **THEN** all selected material requests should be linked and marked as included
4. **WHEN** viewing a purchase request, **THEN** users should see all source material requests and can drill down to details
5. **IF** a purchase request is cancelled, **THEN** linked material requests should return to approved state for reprocessing

#### Business Rules
- **BR-3.1:** Only approved material requests can be added to purchase requests
- **BR-3.2:** Each material request can only belong to one purchase request (Many2one relationship)
- **BR-3.3:** Purchase requests are typically organized by vendor, but vendor selection is optional at this stage
- **BR-3.4:** Purchase request lines consolidate quantities from multiple material request lines for the same product
- **BR-3.5:** Total estimated cost rolls up from all included material request lines
- **BR-3.6:** Integration with purchase module for vendor data

#### Data Requirements
```python
# Purchase Request Model
purchase_request = {
    'name': 'Char, required, unique, auto-sequence (PR/####)',
    'vendor_id': 'Many2one(res.partner), optional, domain=supplier',
    'date_requested': 'Date, required, default=today',
    'date_required': 'Date, computed=earliest_material_request_required_date',
    'state': 'Selection(draft/approved/converted/cancelled), default=draft, tracked',
    'material_request_ids': 'One2many(test_app.material.request), readonly after approval',
    'line_ids': 'One2many(test_app.purchase.request.line), required',
    'total_estimated_cost': 'Monetary, computed from lines, stored',
    'currency_id': 'Many2one(res.currency), required, default=company_currency',
    'company_id': 'Many2one(res.company), required, default=user_company',
    'purchase_order_id': 'Many2one(purchase.order), set when converted',
    'created_by': 'Many2one(res.users), default=current_user',
    'approved_by': 'Many2one(res.users), set when approved',
    'approved_date': 'Datetime, set when approved',
    'notes': 'Text, optional, procurement notes',
}

# Purchase Request Line Model
purchase_request_line = {
    'purchase_request_id': 'Many2one(test_app.purchase.request), required, cascade',
    'product_id': 'Many2one(product.product), required',
    'description': 'Text, optional',
    'quantity': 'Float, required, sum of material_request_lines',
    'uom_id': 'Many2one(uom.uom), required',
    'estimated_unit_cost': 'Monetary, computed=avg_of_material_requests',
    'estimated_total_cost': 'Monetary, computed=quantity*unit_cost, stored',
    'currency_id': 'Many2one, related to purchase_request',
    'material_request_line_ids': 'Many2many(test_app.material.request.line), readonly',
    'purchase_order_line_id': 'Many2one(purchase.order.line), set when converted',
}
```

### FR-4: Purchase Request to Purchase Order Conversion

**User Story:** As a procurement manager, I want to convert approved purchase requests into standard Odoo purchase orders, so that I can send orders to vendors and track delivery.

#### Acceptance Criteria
1. **WHEN** a purchase request is approved, **THEN** a "Convert to Purchase Order" button should be available
2. **WHEN** converting to purchase order, **THEN** the system should create a purchase.order record with all lines from the purchase request
3. **IF** vendor is specified on purchase request, **THEN** it should be used for the purchase order
4. **IF** vendor is not specified, **THEN** a wizard should prompt to select vendor before conversion
5. **WHEN** purchase order is created, **THEN** purchase request state should change to 'converted' and link established
6. **WHEN** purchase order is received, **THEN** source material requests should be marked as 'done'

#### Business Rules
- **BR-4.1:** Only approved purchase requests can be converted to purchase orders
- **BR-4.2:** Conversion creates standard purchase.order with origin reference to purchase request
- **BR-4.3:** Purchase order lines link back to purchase request lines for traceability
- **BR-4.4:** Material request lines track which purchase order line fulfills them
- **BR-4.5:** If purchase order is cancelled, purchase request remains in converted state (no automatic reversion)
- **BR-4.6:** Integration with stock module for tracking received quantities
- **BR-4.7:** Estimated costs from purchase request become unit prices on purchase order (can be edited)

### FR-5: Traceability and Reporting

**User Story:** As a procurement manager, I want to track material requests from initial request through to purchase order receipt, so that I can monitor fulfillment and analyze procurement patterns.

#### Acceptance Criteria
1. **WHEN** viewing a material request, **THEN** users should see linked purchase request and purchase order if they exist
2. **WHEN** viewing a purchase order, **THEN** users should see all source material requests in a smart button or info field
3. **WHEN** generating reports, **THEN** system should provide material request aging, approval rates, and fulfillment time analytics
4. **WHEN** searching material requests, **THEN** filters should include state, department, date ranges, product, and requester
5. **IF** a product is frequently requested, **THEN** procurement reports should highlight for inventory planning

#### Business Rules
- **BR-5.1:** All state transitions are tracked with timestamp and user for audit trail
- **BR-5.2:** Material requests link forward to purchase request and purchase order
- **BR-5.3:** Purchase orders link back to source material requests via custom field
- **BR-5.4:** Dashboard shows pending approvals, approved requests awaiting purchase, and fulfillment metrics
- **BR-5.5:** Reporting includes: request by department, approval time, fulfillment time, cost variance (estimated vs actual)

## User Interface Requirements

### Form Views

#### Material Request Form
- **Header:** Submit, Approve, Reject buttons based on state and permissions; statusbar showing draft/submitted/approved/rejected/done
- **Main Section:**
  - Auto-filled: name (sequence), employee, department
  - Editable: date_required, reason
  - Read-only after submit: all fields
- **Lines Tab:** Editable tree with product, description, quantity, UOM, estimated_unit_cost
- **Info Tab:** Show total_estimated_cost, purchase_request_id (with link), purchase_order_id (with link)
- **Footer:** Chatter for approval comments and communication

#### Purchase Request Form
- **Header:** Approve, Convert to PO buttons based on state; statusbar showing draft/approved/converted/cancelled
- **Main Section:** vendor_id (optional), date_required, notes
- **Material Requests Tab:** Tree view of linked material_request_ids (read-only)
- **Lines Tab:** Consolidated purchase request lines with quantity, estimated costs
- **Footer:** Chatter for procurement team communication

### List Views

#### Material Request List
- **Columns:** name, employee_id, department_id, date_required, total_estimated_cost, state, create_date
- **Sortable by:** date_required, date_requested, total_cost, state
- **Filterable by:** state, department, employee, date range, has_purchase_request
- **Bulk actions:** Bulk approval (for managers)
- **Color coding:** Overdue requests (date_required < today and state != done) in orange

#### Purchase Request List
- **Columns:** name, vendor_id, date_required, material_request_count, total_estimated_cost, state
- **Sortable by:** date, state, vendor, cost
- **Filterable by:** state, vendor, date range, has_purchase_order
- **Bulk actions:** None (individual approval required)

### Reports

#### Material Request Report (PDF)
- **Content:** Employee details, request date, required date, line items with quantities and costs, approval info
- **Format:** PDF with company branding, printable for approvals
- **Filters:** Individual material request
- **Access:** Available to request creator, approvers, and procurement

#### Procurement Analysis Dashboard
- **KPI Widgets:**
  - Pending approvals count
  - Approved requests awaiting purchase count
  - Average approval time (hours)
  - Average fulfillment time (request to delivery in days)
- **Charts:**
  - Material requests by department (pie chart)
  - Request volume over time (line chart)
  - Top 10 requested products (bar chart)
  - Cost variance: estimated vs actual (comparison chart)
- **Filters:** Date range, department, state
- **Export:** Excel export for detailed analysis

### Dashboards

#### Material Request Dashboard
- **My Requests Section:** Tree of current user's material requests
- **Pending Approvals Section:** (For managers) Requests awaiting approval
- **Approved Requests Section:** (For procurement) Approved requests ready for purchase request
- **Filters:** Quick filters for state, date range
- **Actions:** Direct approve/reject from dashboard

## Integration Requirements

### Odoo Core Modules

#### HR Module Integration
- **Dependency:** `hr` module required
- **Data Exchange:**
  - Employee data (hr.employee) for material_request.employee_id
  - Department data (hr.department) for grouping and filtering
- **Business Logic:** Default employee_id to current user's employee record
- **Validation:** Ensure user has active employee record before creating material request

#### Purchase Module Integration
- **Dependency:** `purchase` module required
- **Data Exchange:**
  - Vendor/supplier data (res.partner with is_supplier=True)
  - Product data (product.product)
  - Purchase order creation (purchase.order, purchase.order.line)
- **Business Logic:**
  - Create purchase.order from approved purchase.request
  - Set origin field to reference purchase request number
  - Link purchase order lines back to purchase request lines
- **Trigger Points:** When purchase request is converted, create corresponding purchase order

#### Stock/Inventory Module Integration
- **Dependency:** `stock` via `purchase` module
- **Data Exchange:**
  - Product UOM (uom.uom)
  - Product categories for filtering
  - Stock picking for delivery tracking
- **Business Logic:**
  - Validate UOM categories match product
  - Update material request to 'done' when purchase order delivery is completed
- **Trigger Points:** When purchase order picking is validated, update linked material requests

#### Accounting Module Integration (Optional)
- **Dependency:** `account` module (standard with purchase)
- **Data Exchange:**
  - Currency (res.currency) for multi-currency support
  - Company data (res.company) for multi-company
- **Business Logic:**
  - Support multiple currencies if configured
  - Respect company-specific purchase configurations
- **Trigger Points:** Inherit currency and fiscal settings from purchase module

### Third-party Integrations
- **External API:** None in initial version (future: integration with external procurement systems)
- **Data Import/Export:** Excel import/export for bulk material request creation
- **Webhooks:** None in initial version (future: notify external systems of purchase order creation)

## Security and Access Control

### User Groups and Permissions

#### Material Request User (test_app.group_material_request_user)
- **Inherits:** base.group_user (Employee)
- **Read Access:** Own material requests and approved requests from any department
- **Write Access:** Own draft material requests only
- **Create Access:** Create new material requests
- **Delete Access:** Delete own draft material requests only
- **Purpose:** Standard employees who request materials

#### Material Request Manager (test_app.group_material_request_manager)
- **Inherits:** test_app.group_material_request_user
- **Read Access:** All material requests
- **Write Access:** Approve/reject any material request, edit approved/submitted requests
- **Create Access:** Create material requests
- **Delete Access:** Delete draft and rejected material requests
- **Additional Rights:** Bulk approval, access to approval dashboard
- **Purpose:** Department managers and supervisors

#### Procurement Officer (test_app.group_procurement_officer)
- **Inherits:** test_app.group_material_request_manager
- **Read Access:** All material requests, purchase requests, and linked purchase orders
- **Write Access:** Create and manage purchase requests, convert to purchase orders
- **Create Access:** Create purchase requests
- **Delete Access:** Delete draft purchase requests
- **Additional Rights:** Access to procurement dashboard and analytics
- **Purpose:** Procurement team members

#### Procurement Manager (test_app.group_procurement_manager)
- **Inherits:** test_app.group_procurement_officer + purchase.group_purchase_manager
- **Full Access:** All CRUD operations on all module records
- **Admin Functions:** System configuration, security settings
- **Reports:** Access to all analytical reports
- **Export:** Data export capabilities
- **Purpose:** Procurement department head

### Record-level Security

#### Multi-company Rules
- **Rule:** Users see only material requests and purchase requests from their company
- **Domain:** `['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]`
- **Applies to:** All models (material.request, purchase.request)

#### Department Restrictions (Optional - can be enabled)
- **Rule:** Managers see only requests from their department
- **Domain:** `[('department_id', 'in', user.employee_id.department_id)]`
- **Configurable:** Can be disabled for cross-department visibility

#### Own Records Access
- **Rule:** Regular users see only their own draft/submitted requests (approved requests visible to all)
- **Domain:** `['|', ('employee_id.user_id', '=', user.id), ('state', 'in', ['approved', 'rejected', 'done'])]`
- **Applies to:** Material requests only

### Data Privacy
- **PII Handling:** Employee names and departments are stored; follows Odoo HR module privacy settings
- **GDPR Compliance:** Material requests archived when employee leaves (not deleted for audit trail)
- **Audit Trail:** All state changes tracked with user and timestamp via mail.thread

## Performance Requirements

### Response Time
- **Page Load:** Material request form loads within 2 seconds with up to 50 lines
- **Search Results:** List views return results within 1 second for up to 10,000 records
- **Dashboard Load:** Procurement dashboard loads within 3 seconds with real-time metrics
- **Report Generation:** PDF reports complete within 10 seconds
- **Conversion Process:** Purchase request to purchase order conversion completes within 5 seconds

### Scalability
- **Concurrent Users:** Support 100+ simultaneous users across multiple companies
- **Data Volume:**
  - Handle 50,000+ material requests efficiently
  - Handle 5,000+ purchase requests
  - Support 500+ active employees requesting materials
- **Storage Growth:** Approximately 1-2 GB per year based on transaction volume
- **Line Items:** Support up to 100 lines per material request, 200 lines per purchase request

### Availability
- **Uptime:** Inherits from Odoo platform (target 99.9% during business hours)
- **Backup:** Daily automated backups per Odoo infrastructure
- **Disaster Recovery:** 4-hour RTO (Recovery Time Objective)
- **Caching:** Use Odoo ORM caching for frequently accessed reference data (products, employees)

## Compliance and Standards

### Regulatory Compliance
- **Industry Standards:** General business procurement standards
- **Data Protection:** GDPR compliance for employee personal data
- **Financial Compliance:** Audit trail requirements for procurement transactions
- **Record Retention:** Material requests retained for 7 years for audit purposes

### Technical Standards
- **Coding Standards:**
  - PEP 8 for Python code
  - Odoo coding guidelines (OCA standards)
  - ESLint for any JavaScript components
- **Documentation:**
  - Inline docstrings for all Python methods
  - User manual covering workflows and features
  - Technical documentation for deployment and configuration
- **Testing:**
  - Unit tests with 80%+ code coverage
  - Integration tests for purchase order conversion
  - Access rights validation tests

### Quality Assurance
- **Code Review:** Peer review process for all code changes
- **Testing Protocol:**
  - Automated unit tests in CI/CD pipeline
  - Manual regression testing before releases
  - User acceptance testing with procurement team
- **Performance Monitoring:**
  - Monitor query performance for list views
  - Track conversion times for purchase request to PO
  - Alert on slow-running operations

## Constraints and Assumptions

### Technical Constraints
- **Odoo Version:** Must be compatible with Odoo 17.0 Community or Enterprise
- **Database:** PostgreSQL 12 or higher
- **Browser Support:** Chrome, Firefox, Safari, Edge (latest 2 versions)
- **Mobile:** Responsive design for tablet use (material request approval on tablets)
- **Dependencies:** Requires `hr`, `purchase`, `stock`, `purchase_stock` modules

### Business Constraints
- **Budget:** Internal development (no external budget required)
- **Timeline:** MVP completion in 4-6 weeks
- **Resources:** 1 developer full-time, testing support from procurement team
- **Training:** User training sessions required before go-live (2 hours per group)
- **Phased Rollout:** Pilot with one department, then company-wide

### Assumptions
- **User Base:** Estimated 100-200 employees will use material request feature
- **Volume:** Estimated 500-1000 material requests per month
- **Existing Data:** Company already has products, vendors, and employees configured in Odoo
- **Network:** Users have reliable network access to Odoo instance
- **Support:** IT team available for user support and troubleshooting

### Dependencies
- **Odoo Modules:** `hr`, `purchase`, `stock`, `purchase_stock` (all standard modules)
- **External Systems:** None (all functionality within Odoo)
- **Hardware:** Standard Odoo server requirements (4+ CPU, 8+ GB RAM for 100 users)
- **Network:** Standard corporate network with internet access for updates

## Success Criteria and Acceptance

### Functional Success Criteria
1. **Feature Completion:** All 5 functional requirements (FR-1 through FR-5) implemented and working
2. **User Acceptance:** 90%+ satisfaction from pilot user group (procurement and test department)
3. **Workflow Validation:** Complete workflow from material request to purchase order delivery works end-to-end
4. **Integration:** Seamless integration with HR, Purchase, and Stock modules confirmed

### Technical Success Criteria
1. **Code Quality:** Passes all pylint and flake8 checks with Odoo coding guidelines
2. **Test Coverage:** 80%+ automated unit test coverage for models and business logic
3. **Performance:** All performance requirements met (page load, search, reports)
4. **Security:** All user groups and record rules function correctly; no security vulnerabilities
5. **Documentation:** Complete user manual and technical documentation delivered

### Business Success Criteria
1. **Process Improvement:** 40%+ reduction in ad-hoc/untracked material requests
2. **Approval Efficiency:** 80%+ of material requests approved/rejected within 24 hours
3. **Cost Savings:** 15%+ cost savings from consolidated purchasing (measured after 6 months)
4. **User Adoption:** 95%+ of employees use system for material requests (no email/paper requests)
5. **Visibility:** 100% traceability from material request to purchase order receipt

## Risk Assessment

### High-Risk Items

#### R-1: Integration Complexity with Purchase Module
- **Risk:** Complex integration causing conversion errors or data inconsistency
- **Impact:** High - Core functionality depends on purchase order creation
- **Likelihood:** Medium
- **Mitigation:**
  - Study purchase.order model and creation patterns early
  - Create comprehensive integration tests
  - Prototype conversion logic before full implementation
- **Contingency:**
  - Simplify to manual purchase order creation with reference links
  - Phase 2 enhancement for automatic conversion

#### R-2: User Adoption Resistance
- **Risk:** Users continue using email/informal requests instead of system
- **Impact:** High - Module value depends on usage
- **Likelihood:** Medium
- **Mitigation:**
  - Involve procurement team in requirements and testing
  - Create simple, intuitive user interface
  - Provide comprehensive training and user guides
  - Management support and policy requiring system use
- **Contingency:**
  - Additional training sessions
  - Gamification or incentives for system usage
  - Simplified workflow if too complex

### Medium-Risk Items

#### R-3: Performance with Large Data Volumes
- **Risk:** Slow performance as material requests accumulate
- **Impact:** Medium - Affects user experience
- **Likelihood:** Low-Medium
- **Mitigation:**
  - Proper database indexing on key fields
  - Optimize computed fields with smart caching
  - Performance testing with simulated data volumes
- **Contingency:**
  - Archive old requests
  - Database query optimization
  - Additional indexes

#### R-4: Scope Creep - Additional Feature Requests
- **Risk:** Users request additional features during/after development
- **Impact:** Medium - Timeline and resource impact
- **Likelihood:** High
- **Mitigation:**
  - Clear requirements sign-off before development
  - Formal change request process
  - Phase 2 backlog for non-critical features
- **Contingency:**
  - Prioritize MVP features only
  - Schedule Phase 2 for enhancements

### Low-Risk Items

#### R-5: Odoo Version Compatibility
- **Risk:** Module breaks with Odoo updates
- **Impact:** Medium - Requires maintenance
- **Likelihood:** Low (stable within major version)
- **Mitigation:**
  - Follow Odoo 17 best practices and stable APIs
  - Test with latest Odoo 17 point releases
- **Contingency:**
  - Quick patch releases for fixes

## Glossary

**Business Terms:**
- **Material Request (MR):** Internal request from an employee for materials/products needed
- **Purchase Request (PR):** Consolidated request for procurement to create purchase order, aggregates multiple MRs
- **Requestor:** Employee who creates a material request
- **Approver:** Manager with authority to approve/reject material requests
- **Procurement Officer:** Team member responsible for creating purchase requests and purchase orders
- **Fulfillment:** Complete process from material request creation to receiving purchased goods

**Technical Terms:**
- **Model:** Python class representing database table in Odoo (e.g., test_app.material.request)
- **View:** XML definition of user interface elements (form, tree, search, kanban)
- **Action:** Configuration linking menus to models and views
- **Wizard:** Multi-step user interaction form (transient model)
- **State Machine:** Workflow with defined states and transitions (draft → submitted → approved)
- **Many2one:** Odoo field type for foreign key relationship (e.g., material_request_id)
- **One2many:** Odoo field type for reverse relationship (e.g., line_ids)
- **Many2many:** Odoo field type for junction table relationship
- **Chatter:** Odoo messaging/activity tracking feature (mail.thread)
- **Smart Button:** Button showing related record counts with drill-down capability

---

**Document Status:** Draft
**Last Updated:** 2026-02-16
**Next Review Date:** After requirements validation
**Approved By:** Pending
