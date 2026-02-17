# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseRequestConvertWizard(models.TransientModel):
    _name = 'test_app.purchase.request.convert.wizard'
    _description = 'Purchase Request Convert to PO Wizard'

    purchase_request_id = fields.Many2one(
        'test_app.purchase.request',
        string='Purchase Request',
        required=True,
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('supplier_rank', '>', 0)],
        help='Select the vendor for this purchase order',
    )

    def action_convert(self):
        """Convert purchase request to purchase order with selected vendor"""
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_('Please select a vendor.'))

        # Set vendor on purchase request
        self.purchase_request_id.write({'vendor_id': self.vendor_id.id})

        # Call convert method
        return self.purchase_request_id.action_convert_to_po()
