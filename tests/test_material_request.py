# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from odoo import fields


class TestMaterialRequest(TransactionCase):
    """Test Material Request model functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Get test employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

        # Get test products
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Test Product 1',
            'type': 'product',
            'purchase_ok': True,
            'standard_price': 100.00,
        })

        cls.product_2 = cls.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'product',
            'purchase_ok': True,
            'standard_price': 50.00,
        })

        cls.manager = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_manager',
            'groups_id': [(6, 0, [cls.env.ref('test_app.group_material_request_manager').id])],
        })

    def _create_material_request(self, state='draft'):
        """Helper to create a material request"""
        return self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test request',
            'state': state,
        })

    def _add_request_line(self, material_request, product, quantity=1.0, unit_cost=100.0):
        """Helper to add a line to material request"""
        return self.env['test_app.material.request.line'].create({
            'material_request_id': material_request.id,
            'product_id': product.id,
            'description': product.name,
            'quantity': quantity,
            'uom_id': product.uom_id.id,
            'estimated_unit_cost': unit_cost,
        })

    def test_create_material_request(self):
        """Test material request creation and sequence generation"""
        mr = self._create_material_request()

        # Verify sequence is generated
        self.assertTrue(mr.name)
        self.assertNotEqual(mr.name, 'New')
        self.assertTrue(mr.name.startswith('MR/'))

        # Verify defaults
        self.assertEqual(mr.state, 'draft')
        self.assertEqual(mr.employee_id, self.employee)
        self.assertTrue(mr.company_id)
        self.assertTrue(mr.currency_id)

    def test_submit_without_lines_fails(self):
        """Test that submitting without lines raises an error"""
        mr = self._create_material_request()

        with self.assertRaises(UserError) as cm:
            mr.action_submit()

        self.assertIn('without any line items', str(cm.exception))

    def test_submit_with_lines_succeeds(self):
        """Test successful submission with lines"""
        mr = self._create_material_request()
        self._add_request_line(mr, self.product_1)

        # Submit should succeed
        mr.action_submit()

        self.assertEqual(mr.state, 'submitted')

    def test_approve_workflow(self):
        """Test submit → approve workflow"""
        mr = self._create_material_request()
        self._add_request_line(mr, self.product_1)

        # Submit
        mr.action_submit()
        self.assertEqual(mr.state, 'submitted')

        # Approve
        mr.with_user(self.manager).action_approve()
        self.assertEqual(mr.state, 'approved')
        self.assertEqual(mr.approved_by, self.manager)
        self.assertTrue(mr.approved_date)

    def test_reject_workflow(self):
        """Test submit → reject workflow"""
        mr = self._create_material_request()
        self._add_request_line(mr, self.product_1)

        # Submit
        mr.action_submit()

        # Reject
        rejection_reason = 'Budget exceeded'
        mr.with_user(self.manager).action_reject(rejection_reason)

        self.assertEqual(mr.state, 'rejected')
        self.assertEqual(mr.rejected_by, self.manager)
        self.assertEqual(mr.rejected_reason, rejection_reason)
        self.assertTrue(mr.rejected_date)

    def test_compute_total_cost(self):
        """Test total estimated cost computation"""
        mr = self._create_material_request()

        # Add multiple lines
        self._add_request_line(mr, self.product_1, quantity=2.0, unit_cost=100.0)
        self._add_request_line(mr, self.product_2, quantity=3.0, unit_cost=50.0)

        # Total should be (2 * 100) + (3 * 50) = 350
        self.assertEqual(mr.total_estimated_cost, 350.0)

    def test_date_required_before_requested_fails(self):
        """Test that required date cannot be before request date"""
        with self.assertRaises(ValidationError) as cm:
            self.env['test_app.material.request'].create({
                'employee_id': self.employee.id,
                'date_requested': fields.Date.today(),
                'date_required': fields.Date.today() - timedelta(days=1),
                'reason': 'Test',
            })

        self.assertIn('cannot be before request date', str(cm.exception))

    def test_negative_quantity_fails(self):
        """Test that negative quantity is not allowed"""
        mr = self._create_material_request()

        with self.assertRaises(ValidationError) as cm:
            self._add_request_line(mr, self.product_1, quantity=-1.0)

        self.assertIn('must be greater than zero', str(cm.exception))

    def test_negative_cost_fails(self):
        """Test that negative cost is not allowed"""
        mr = self._create_material_request()

        with self.assertRaises(ValidationError) as cm:
            self._add_request_line(mr, self.product_1, unit_cost=-10.0)

        self.assertIn('cannot be negative', str(cm.exception))

    def test_cannot_delete_submitted_request(self):
        """Test that submitted requests cannot be deleted"""
        mr = self._create_material_request()
        self._add_request_line(mr, self.product_1)
        mr.action_submit()

        with self.assertRaises(UserError) as cm:
            mr.unlink()

        self.assertIn('cannot delete', str(cm.exception))

    def test_set_to_draft_from_rejected(self):
        """Test resetting rejected request to draft"""
        mr = self._create_material_request()
        self._add_request_line(mr, self.product_1)

        # Submit and reject
        mr.action_submit()
        mr.with_user(self.manager).action_reject('Test rejection')

        # Reset to draft
        mr.with_user(self.manager).action_set_to_draft()

        self.assertEqual(mr.state, 'draft')
        self.assertFalse(mr.rejected_by)
        self.assertFalse(mr.rejected_date)
        self.assertFalse(mr.rejected_reason)

    def test_line_onchange_product(self):
        """Test that line fields are auto-filled on product selection"""
        mr = self._create_material_request()

        line = self.env['test_app.material.request.line'].new({
            'material_request_id': mr.id,
            'product_id': self.product_1.id,
        })

        line._onchange_product_id()

        # UOM should be set
        self.assertEqual(line.uom_id, self.product_1.uom_po_id or self.product_1.uom_id)
        # Estimated cost should be set from standard price
        self.assertEqual(line.estimated_unit_cost, self.product_1.standard_price)

    def test_mark_done(self):
        """Test marking approved request as done"""
        mr = self._create_material_request()
        self._add_request_line(mr, self.product_1)

        # Submit and approve
        mr.action_submit()
        mr.with_user(self.manager).action_approve()

        # Mark as done
        mr.action_mark_done()

        self.assertEqual(mr.state, 'done')
