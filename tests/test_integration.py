# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from datetime import timedelta
from odoo import fields


class TestProcurementWorkflow(TransactionCase):
    """Test full procurement workflow integration"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

        # Create test vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'supplier_rank': 1,
        })

        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'purchase_ok': True,
            'standard_price': 100.00,
        })

        # Create manager user
        cls.manager = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_integration_manager',
            'groups_id': [(6, 0, [
                cls.env.ref('test_app.group_procurement_manager').id,
            ])],
        })

    def test_full_workflow(self):
        """Test complete workflow: MR → PR → PO"""

        # Step 1: Create Material Request
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Integration test',
        })

        # Add line to MR
        self.env['test_app.material.request.line'].create({
            'material_request_id': mr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Step 2: Submit and Approve MR
        mr.action_submit()
        self.assertEqual(mr.state, 'submitted')

        mr.with_user(self.manager).action_approve()
        self.assertEqual(mr.state, 'approved')

        # Step 3: Create Purchase Request
        pr = self.env['test_app.purchase.request'].create({
            'vendor_id': self.vendor.id,
            'date_requested': fields.Date.today(),
        })

        # Link MR to PR
        mr.purchase_request_id = pr.id

        # Add line to PR (consolidated from MR)
        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Step 4: Approve PR
        pr.with_user(self.manager).action_approve()
        self.assertEqual(pr.state, 'approved')

        # Step 5: Convert PR to PO
        pr.action_convert_to_po()

        # Verify PR converted
        self.assertEqual(pr.state, 'converted')
        self.assertTrue(pr.purchase_order_id)

        # Verify PO was created correctly
        po = pr.purchase_order_id
        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(po.origin, pr.name)
        self.assertTrue(po.order_line)
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line[0].product_id, self.product)

    def test_material_request_to_purchase_order_link(self):
        """Test traceability from MR to PO"""

        # Create and approve MR
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Traceability test',
        })

        self.env['test_app.material.request.line'].create({
            'material_request_id': mr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 3.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        mr.action_submit()
        mr.with_user(self.manager).action_approve()

        # Create and approve PR
        pr = self.env['test_app.purchase.request'].create({
            'vendor_id': self.vendor.id,
            'date_requested': fields.Date.today(),
        })

        mr.purchase_request_id = pr.id

        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 3.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        pr.with_user(self.manager).action_approve()

        # Convert to PO
        pr.action_convert_to_po()
        po = pr.purchase_order_id

        # Verify traceability chain
        self.assertEqual(mr.purchase_request_id, pr)
        self.assertEqual(pr.purchase_order_id, po)
        self.assertIn(mr, po.material_request_ids)

    def test_multiple_mrs_consolidate_to_single_po(self):
        """Test multiple material requests consolidating into one PO"""

        # Create two material requests
        mr1 = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'First request',
        })

        self.env['test_app.material.request.line'].create({
            'material_request_id': mr1.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 2.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        mr2 = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=10),
            'reason': 'Second request',
        })

        self.env['test_app.material.request.line'].create({
            'material_request_id': mr2.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 3.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Approve both MRs
        mr1.action_submit()
        mr1.with_user(self.manager).action_approve()
        mr2.action_submit()
        mr2.with_user(self.manager).action_approve()

        # Create single PR for both MRs
        pr = self.env['test_app.purchase.request'].create({
            'vendor_id': self.vendor.id,
            'date_requested': fields.Date.today(),
        })

        # Link both MRs to the PR
        mr1.purchase_request_id = pr.id
        mr2.purchase_request_id = pr.id

        # Add consolidated line (total quantity: 2 + 3 = 5)
        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,  # Consolidated
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Verify PR has both MRs
        self.assertEqual(pr.material_request_count, 2)
        self.assertIn(mr1, pr.material_request_ids)
        self.assertIn(mr2, pr.material_request_ids)

        # Approve and convert to PO
        pr.with_user(self.manager).action_approve()
        pr.action_convert_to_po()

        # Verify single PO created with both MRs linked
        po = pr.purchase_order_id
        self.assertEqual(len(po.material_request_ids), 2)
        self.assertIn(mr1, po.material_request_ids)
        self.assertIn(mr2, po.material_request_ids)

        # Verify PO line has consolidated quantity
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line[0].product_qty, 5.0)

    def test_purchase_order_receipt_marks_mr_done(self):
        """Test that receiving PO marks related MRs as done"""

        # Create and approve MR
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Receipt test',
        })

        self.env['test_app.material.request.line'].create({
            'material_request_id': mr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        mr.action_submit()
        mr.with_user(self.manager).action_approve()
        self.assertEqual(mr.state, 'approved')

        # Create PR and convert to PO
        pr = self.env['test_app.purchase.request'].create({
            'vendor_id': self.vendor.id,
            'date_requested': fields.Date.today(),
        })

        mr.purchase_request_id = pr.id

        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        pr.with_user(self.manager).action_approve()
        pr.action_convert_to_po()

        po = pr.purchase_order_id

        # Confirm PO
        po.button_confirm()

        # Verify MR is still approved (not done yet)
        self.assertEqual(mr.state, 'approved')

        # Validate receipt
        if po.picking_ids:
            picking = po.picking_ids[0]
            # Set quantities on move lines
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            # Validate picking
            picking.button_validate()

            # MR should now be marked as done
            self.assertEqual(mr.state, 'done')
