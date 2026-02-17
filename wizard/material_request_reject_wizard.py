# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MaterialRequestRejectWizard(models.TransientModel):
    _name = 'test_app.material.request.reject.wizard'
    _description = 'Material Request Rejection Wizard'

    material_request_id = fields.Many2one(
        'test_app.material.request',
        string='Material Request',
        required=True,
    )

    rejected_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Please provide a reason for rejecting this material request',
    )

    def action_reject(self):
        """Reject the material request with the provided reason"""
        self.ensure_one()
        if not self.rejected_reason:
            raise UserError(_('Please provide a reason for rejection.'))

        # Call the reject method on material request
        self.material_request_id.action_reject(self.rejected_reason)

        return {'type': 'ir.actions.act_window_close'}
