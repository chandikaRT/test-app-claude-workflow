# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    material_request_ids = fields.Many2many(
        'test_app.material.request',
        string='Material Requests',
        help='Material requests that triggered this purchase order',
        copy=False,
    )

    material_request_count = fields.Integer(
        string='Number of Material Requests',
        compute='_compute_material_request_count',
    )

    @api.depends('material_request_ids')
    def _compute_material_request_count(self):
        """Count number of linked material requests"""
        for order in self:
            order.material_request_count = len(order.material_request_ids)

    def action_view_material_requests(self):
        """Open linked material requests"""
        self.ensure_one()
        return {
            'name': _('Material Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'test_app.material.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.material_request_ids.ids)],
            'context': {'create': False},
        }


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Override to mark material requests as done when PO is received"""
        result = super().button_validate()

        # Mark linked material requests as done when goods are received
        for picking in self:
            if picking.purchase_id and picking.purchase_id.material_request_ids:
                # Filter for approved material requests only
                approved_mrs = picking.purchase_id.material_request_ids.filtered(
                    lambda mr: mr.state == 'approved'
                )
                if approved_mrs:
                    approved_mrs.action_mark_done()

        return result
