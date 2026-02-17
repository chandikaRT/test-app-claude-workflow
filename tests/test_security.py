# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from datetime import timedelta
from odoo import fields


class TestSecurity(TransactionCase):
    """Test security and access rights"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'purchase_ok': True,
            'standard_price': 100.00,
        })

        # Create test users with different groups
        cls.basic_user = cls.env['res.users'].create({
            'name': 'Basic User',
            'login': 'basic_user',
            'email': 'basic@test.com',
            'groups_id': [(6, 0, [cls.env.ref('test_app.group_material_request_user').id])],
        })

        cls.manager_user = cls.env['res.users'].create({
            'name': 'Manager User',
            'login': 'manager_user',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [cls.env.ref('test_app.group_material_request_manager').id])],
        })

        cls.procurement_officer = cls.env['res.users'].create({
            'name': 'Procurement Officer',
            'login': 'procurement_officer',
            'email': 'officer@test.com',
            'groups_id': [(6, 0, [cls.env.ref('test_app.group_procurement_officer').id])],
        })

        # Link basic user to employee
        cls.employee.user_id = cls.basic_user.id

    def test_user_can_create_own_mr(self):
        """Test that basic user can create material request"""
        mr = self.env['test_app.material.request'].with_user(self.basic_user).create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test request',
        })

        self.assertTrue(mr)
        self.assertEqual(mr.employee_id, self.employee)

    def test_user_cannot_approve(self):
        """Test that basic user cannot approve material requests"""
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test request',
            'state': 'submitted',
        })

        # Basic user should not be able to approve
        with self.assertRaises(AccessError):
            mr.with_user(self.basic_user).action_approve()

    def test_manager_can_approve(self):
        """Test that manager can approve material requests"""
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test request',
        })

        # Add line
        self.env['test_app.material.request.line'].create({
            'material_request_id': mr.id,
            'product_id': self.product.id,
            'description': self.product.name,
            'quantity': 1.0,
            'uom_id': self.product.uom_id.id,
            'estimated_unit_cost': 100.00,
        })

        # Submit
        mr.action_submit()

        # Manager should be able to approve
        mr.with_user(self.manager_user).action_approve()
        self.assertEqual(mr.state, 'approved')

    def test_user_sees_only_own_and_approved(self):
        """Test that basic user sees only their own requests and approved/rejected/done from others"""

        # Create another employee and user
        other_employee = self.env['hr.employee'].create({
            'name': 'Other Employee',
        })

        other_user = self.env['res.users'].create({
            'name': 'Other User',
            'login': 'other_user',
            'email': 'other@test.com',
            'groups_id': [(6, 0, [self.env.ref('test_app.group_material_request_user').id])],
        })

        other_employee.user_id = other_user.id

        # Create MR for basic user (draft)
        mr_own = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Own request',
            'state': 'draft',
        })

        # Create MR for other user (draft)
        mr_other_draft = self.env['test_app.material.request'].create({
            'employee_id': other_employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Other draft request',
            'state': 'draft',
        })

        # Create MR for other user (approved)
        mr_other_approved = self.env['test_app.material.request'].create({
            'employee_id': other_employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Other approved request',
            'state': 'approved',
        })

        # Basic user should see:
        # - their own draft MR
        # - other user's approved MR
        # - NOT other user's draft MR
        mrs_visible = self.env['test_app.material.request'].with_user(self.basic_user).search([])

        self.assertIn(mr_own, mrs_visible)
        self.assertIn(mr_other_approved, mrs_visible)
        self.assertNotIn(mr_other_draft, mrs_visible)

    def test_manager_sees_all(self):
        """Test that manager sees all material requests"""

        # Create another employee
        other_employee = self.env['hr.employee'].create({
            'name': 'Other Employee',
        })

        # Create MRs in different states
        mr_draft = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Draft request',
            'state': 'draft',
        })

        mr_submitted = self.env['test_app.material.request'].create({
            'employee_id': other_employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Submitted request',
            'state': 'submitted',
        })

        # Manager should see all MRs
        mrs_visible = self.env['test_app.material.request'].with_user(self.manager_user).search([])

        self.assertIn(mr_draft, mrs_visible)
        self.assertIn(mr_submitted, mrs_visible)

    def test_officer_can_create_pr(self):
        """Test that procurement officer can create purchase requests"""
        pr = self.env['test_app.purchase.request'].with_user(self.procurement_officer).create({
            'date_requested': fields.Date.today(),
        })

        self.assertTrue(pr)
        self.assertEqual(pr.created_by, self.procurement_officer)

    def test_user_cannot_create_pr(self):
        """Test that basic user cannot create purchase requests"""
        with self.assertRaises(AccessError):
            self.env['test_app.purchase.request'].with_user(self.basic_user).create({
                'date_requested': fields.Date.today(),
            })

    def test_user_cannot_delete_mr(self):
        """Test that basic user cannot delete material requests"""
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test request',
        })

        # Basic user should not be able to delete
        with self.assertRaises(AccessError):
            mr.with_user(self.basic_user).unlink()

    def test_manager_can_delete_draft_mr(self):
        """Test that manager can delete draft material requests"""
        mr = self.env['test_app.material.request'].create({
            'employee_id': self.employee.id,
            'date_requested': fields.Date.today(),
            'date_required': fields.Date.today() + timedelta(days=7),
            'reason': 'Test request',
            'state': 'draft',
        })

        # Manager should be able to delete draft
        mr.with_user(self.manager_user).unlink()

        # Verify deleted
        self.assertFalse(mr.exists())
