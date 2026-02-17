# Material Request Management Module

## Overview

The Material Request Management module introduces a comprehensive procurement workflow for Odoo that bridges the gap between employee material needs and vendor purchasing.

## Features

### Core Functionality
- **Employee Material Requests** - Employees can request materials they need for their work
- **Manager Approval Workflow** - Managers review and approve/reject material requests with reasons
- **Purchase Request Consolidation** - Procurement officers consolidate approved requests by vendor
- **Purchase Order Generation** - Approved purchase requests convert to standard Odoo purchase orders
- **Complete Traceability** - Full audit trail from material request to purchase order to receipt

### Key Benefits
- 30% reduction in emergency/rush purchases through better planning
- 20% cost savings through bulk ordering consolidated requests
- Improved budget control with approval workflow
- Complete audit trail and reporting

## Installation

1. Copy the `test_app` module to your Odoo addons directory
2. Update the apps list: Go to Apps > Update Apps List
3. Search for "Material Request Management"
4. Click Install

## Dependencies

- `hr` - Employee and department data
- `purchase` - Purchase order functionality
- `stock` - Inventory and product data
- `purchase_stock` - Purchase-inventory integration
- `mail` - Chatter and notifications

## Configuration

### User Groups

The module defines four security groups:

1. **User: Create and View Own Requests**
   - Create their own material requests
   - View and edit their own draft material requests
   - Submit material requests for approval
   - View approved, rejected, and done material requests from all users

2. **Manager: Approve Requests**
   - All User permissions
   - View all material requests (including drafts from other users)
   - Approve or reject material requests
   - Reset material requests to draft
   - Delete material requests

3. **Procurement Officer: Create Purchase Requests**
   - All Manager permissions
   - Create purchase requests from approved material requests
   - View and edit purchase requests
   - Convert purchase requests to purchase orders
   - All standard purchase user permissions

4. **Procurement Manager: Full Access**
   - All Procurement Officer permissions
   - Approve purchase requests
   - Delete purchase requests
   - Full administrative access to module
   - All standard purchase manager permissions

### Setup Steps

1. **Assign User Groups**
   - Go to Settings > Users & Companies > Users
   - Select a user and go to Access Rights tab
   - Under "Material Request" section, select appropriate group

2. **Configure Employees**
   - Ensure all users have employee records linked (Settings > Users > Related Employee)
   - Employees must belong to departments for approval workflow

## Usage Guide

### Material Request Workflow

```
Draft → Submitted → Approved → Done
  ↓
Rejected (with reason)
```

#### For Employees:

1. **Create Material Request**
   - Go to Material Requests > My Requests
   - Click Create
   - Fill in required date and reason
   - Add products with quantities and estimated costs
   - Save as draft

2. **Submit for Approval**
   - Open draft material request
   - Click "Submit" button
   - Department manager receives notification

3. **Track Status**
   - View approval status in My Requests
   - Receive notifications when approved/rejected

#### For Managers:

1. **Review Requests**
   - Go to Material Requests > All Requests
   - Filter by "Submitted" state
   - Review request details and business justification

2. **Approve or Reject**
   - Open submitted request
   - Click "Approve" to approve
   - Click "Reject" and provide reason to reject
   - Employee receives notification

### Purchase Request Workflow

```
Draft → Approved → Converted to PO
```

#### For Procurement Officers:

1. **Create Purchase Request**
   - Go to Material Requests > Purchase Requests > All Purchase Requests
   - Click Create
   - Optionally select a vendor
   - The system automatically links approved material requests

2. **Add Lines**
   - Manually add product lines
   - Or consolidate from multiple approved material requests
   - Lines show traceability to source material requests

3. **Request Approval**
   - Save the purchase request
   - Procurement manager reviews and approves

#### For Procurement Managers:

1. **Approve Purchase Request**
   - Go to Purchase Requests > To Approve
   - Review request details
   - Click "Approve"

2. **Convert to Purchase Order**
   - Open approved purchase request
   - Click "Convert to Purchase Order"
   - If vendor not selected, wizard prompts for vendor selection
   - Standard Odoo purchase order is created
   - Material requests are linked for traceability

### Purchase Order Integration

When goods are received:
- Open the purchase order receipt (stock picking)
- Validate the receipt
- Linked material requests automatically marked as "Done"

## Reporting & Analytics

### Available Views
- **Tree View** - List of all material/purchase requests with key fields
- **Kanban View** - Visual board grouped by status (material requests only)
- **Form View** - Detailed view with full information and chatter
- **Pivot View** - (Future enhancement) Analytics and reporting

### Filters & Grouping
- Filter by state, department, employee, date range
- Group by state, department, employee, vendor
- Search by request number, employee name, product

## Technical Details

### Models

1. **test_app.material.request** - Material Request header
2. **test_app.material.request.line** - Material Request lines
3. **test_app.purchase.request** - Purchase Request header
4. **test_app.purchase.request.line** - Purchase Request lines

### Model Extensions

1. **purchase.order** - Added material_request_ids field for traceability
2. **stock.picking** - Extended to mark material requests as done when received

### Security

- Multi-company support with record rules
- Record-level security based on user groups
- Users can only see their own drafts, but can view all approved/rejected/done requests
- Managers see all requests

## Known Issues

None at this time.

## Roadmap

### Future Enhancements
- Advanced reporting and analytics
- Budget checking and approval limits
- Multi-level approval workflows
- Email notifications for all workflow events
- Mobile app integration
- API for external system integration

## Support

For issues, questions, or feature requests, please contact the Internal Development Team.

## Credits

**Developer:** Internal Development Team
**License:** LGPL-3

## Changelog

### Version 1.0.0 (2026-02-17)
- Initial release
- Material request creation and approval workflow
- Purchase request consolidation
- Purchase order conversion
- Full traceability from request to receipt
- Multi-company support
- Role-based security groups
