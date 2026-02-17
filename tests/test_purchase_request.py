# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import timedelta
from odoo import fields


class TestPurchaseRequest(TransactionCase):
    """Test Purchase Request model functionality"""

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

        # Create test manager
        cls.manager = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_pr_manager',
            'groups_id': [(6, 0, [cls.env.ref('test_app.group_procurement_manager').id])],
        })

        # Create approved material request
        cls.material_request = cls.env['test_app.material.request'].create({
            'employee_id': cls.employee.id,
            'date_requested': fields.Date.today() - timedelta(days=2),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test material request',
            'state': 'approved',
        })

        cls.mr_line = cls.env['test_app.material.request.line'].create({
            'material_request_id': cls.material_request.id,
            'product_id': cls.product.id,
            'description': cls.product.name,
            'quantity': 5.0,
            'uom_id': cls.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

    def _create_purchase_request(self):
        """Helper to create purchase request"""
        return self.env['test_app.purchase.request'].create({
            'vendor_id': self.vendor.id,
            'date_requested': fields.Date.today(),
        })

    def test_create_purchase_request(self):
        """Test purchase request creation and sequence generation"""
        pr = self._create_purchase_request()

        # Verify sequence is generated
        self.assertTrue(pr.name)
        self.assertNotEqual(pr.name, 'New')
        self.assertTrue(pr.name.startswith('PR/'))

        # Verify defaults
        self.assertEqual(pr.state, 'draft')
        self.assertTrue(pr.company_id)
        self.assertTrue(pr.currency_id)

    def test_date_required_computed(self):
        """Test that date_required is computed from linked material requests"""
        pr = self._create_purchase_request()

        # Link material request
        self.material_request.purchase_request_id = pr.id

        # Date required should be computed from MR
        pr._compute_date_required()
        self.assertEqual(pr.date_required, self.material_request.date_required)

    def test_approve_workflow(self):
        """Test draft → approved workflow"""
        pr = self._create_purchase_request()

        # Add lines
        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Approve
        pr.with_user(self.manager).action_approve()

        self.assertEqual(pr.state, 'approved')
        self.assertEqual(pr.approved_by, self.manager)
        self.assertTrue(pr.approved_date)

    def test_cannot_approve_without_lines(self):
        """Test that approval fails without lines"""
        pr = self._create_purchase_request()

        with self.assertRaises(UserError) as cm:
            pr.action_approve()

        self.assertIn('without any line items', str(cm.exception))

    def test_convert_to_po(self):
        """Test conversion to purchase order"""
        pr = self._create_purchase_request()

        # Add lines
        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Approve
        pr.with_user(self.manager).action_approve()

        # Convert to PO
        result = pr.action_convert_to_po()

        # Should create PO and update state
        self.assertEqual(pr.state, 'converted')
        self.assertTrue(pr.purchase_order_id)

        # Verify PO was created
        po = pr.purchase_order_id
        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(po.origin, pr.name)
        self.assertTrue(po.order_line)

    def test_cancel_purchase_request(self):
        """Test cancelling purchase request"""
        pr = self._create_purchase_request()

        # Link material request
        self.material_request.purchase_request_id = pr.id

        # Cancel PR
        pr.action_cancel()

        self.assertEqual(pr.state, 'cancelled')
        # Material request should be unlinked
        self.assertFalse(self.material_request.purchase_request_id)

    def test_cannot_cancel_converted(self):
        """Test that converted PR cannot be cancelled"""
        pr = self._create_purchase_request()

        # Add lines and convert
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

        # Try to cancel
        with self.assertRaises(UserError) as cm:
            pr.action_cancel()

        self.assertIn('converted', str(cm.exception).lower())

    def test_material_request_count(self):
        """Test material request count computation"""
        pr = self._create_purchase_request()

        # Initially should be 0
        self.assertEqual(pr.material_request_count, 0)

        # Link material request
        self.material_request.purchase_request_id = pr.id

        # Should now be 1
        pr._compute_material_request_count()
        self.assertEqual(pr.material_request_count, 1)

    def test_total_estimated_cost(self):
        """Test total estimated cost computation"""
        pr = self._create_purchase_request()

        # Add multiple lines
        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': 'Product 1',
            'quantity': 2.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': 'Product 2',
            'quantity': 3.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 50.00,
        })

        # Total should be (2 * 100) + (3 * 50) = 350
        self.assertEqual(pr.total_estimated_cost, 350.0)

    def test_set_to_draft_from_cancelled(self):
        """Test resetting cancelled PR to draft"""
        pr = self._create_purchase_request()

        # Cancel
        pr.action_cancel()
        self.assertEqual(pr.state, 'cancelled')

        # Reset to draft
        pr.with_user(self.manager).action_set_to_draft()

        self.assertEqual(pr.state, 'draft')
        self.assertFalse(pr.approved_by)
        self.assertFalse(pr.approved_date)

    def test_cannot_delete_approved_request(self):
        """Test that approved PR cannot be deleted"""
        pr = self._create_purchase_request()

        # Add lines and approve
        self.env['test_app.purchase.request.line'].create({
            'purchase_request_id': pr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 5.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        pr.with_user(self.manager).action_approve()

        # Try to delete
        with self.assertRaises(UserError) as cm:
            pr.unlink()

        self.assertIn('cannot delete', str(cm.exception))
