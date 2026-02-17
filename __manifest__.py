# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

{
    'name': 'Material Request Management',
    'version': '1.0.0',
    'category': 'Procurement',
    'summary': 'Manage material requests with approval workflow and purchase order integration',
    'description': """
Material Request Management System
===================================

This module introduces a comprehensive material request workflow:
- Employees can request materials they need for their work
- Managers review and approve/reject material requests
- Procurement officers consolidate approved requests by vendor
- Approved purchase requests convert to standard purchase orders

Features:
---------
* Employee material request creation and submission
* Manager approval/rejection workflow with reasons
* Purchase request consolidation by vendor
* Automatic conversion to purchase orders
* Complete traceability from request to PO to receipt
* Multi-company support with record-level security
* Email notifications for workflow events
* Reporting and analytics dashboards
    """,
    'author': 'Internal Development Team',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',

    'depends': [
        'hr',               # Employee and department data
        'purchase',         # Purchase order functionality
        'stock',            # Inventory and product data
        'purchase_stock',   # Purchase-inventory integration
        'mail',             # Chatter and notifications
    ],

    'data': [
        # Security
        'security/test_app_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence.xml',

        # Wizards (must be loaded before views that reference them)
        'wizard/material_request_reject_wizard_views.xml',
        'wizard/purchase_request_convert_wizard_views.xml',

        # Views - Material Requests
        'views/material_request_views.xml',

        # Views - Purchase Requests
        'views/purchase_request_views.xml',

        # Views - Purchase Order Extensions
        'views/purchase_order_views.xml',

        # Menus
        'views/menus.xml',

        # Reports
        'report/material_request_report_views.xml',
        'report/material_request_report.xml',
    ],

    'demo': [
        'demo/demo_data.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,

    'images': ['static/description/icon.png'],
}
