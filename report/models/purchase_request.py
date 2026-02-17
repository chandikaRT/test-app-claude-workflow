# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = 'test_app.purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_requested desc, id desc'

    # Basic Information
    name = fields.Char(
        string='Request Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain=[('supplier_rank', '>', 0)],
        tracking=True,
        index=True,
    )

    # Dates
    date_requested = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    date_required = fields.Date(
        string='Required Date',
        compute='_compute_date_required',
        store=True,
        readonly=True,
    )

    # Status and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('converted', 'Converted to PO'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    # Additional Information
    notes = fields.Text(
        string='Notes',
    )

    # Approval Information
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
        tracking=True,
    )

    # Company and Currency
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    # Integration Fields
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        readonly=True,
        copy=False,
        tracking=True,
    )

    material_request_ids = fields.One2many(
        'test_app.material.request',
        'purchase_request_id',
        string='Material Requests',
    )

    # Lines
    line_ids = fields.One2many(
        'test_app.purchase.request.line',
        'purchase_request_id',
        string='Purchase Request Lines',
        copy=True,
    )

    # Computed Fields
    total_estimated_cost = fields.Monetary(
        string='Total Estimated Cost',
        compute='_compute_total_estimated_cost',
        store=True,
        currency_field='currency_id',
        tracking=True,
    )

    material_request_count = fields.Integer(
        string='Number of Material Requests',
        compute='_compute_material_request_count',
    )

    line_count = fields.Integer(
        string='Number of Lines',
        compute='_compute_line_count',
    )

    @api.depends('material_request_ids.date_required')
    def _compute_date_required(self):
        """Compute earliest required date from linked material requests"""
        for request in self:
            if request.material_request_ids:
                dates = request.material_request_ids.mapped('date_required')
                request.date_required = min(dates) if dates else False
            else:
                request.date_required = False

    @api.depends('line_ids.estimated_total_cost')
    def _compute_total_estimated_cost(self):
        """Compute total estimated cost from all lines"""
        for request in self:
            request.total_estimated_cost = sum(request.line_ids.mapped('estimated_total_cost'))

    @api.depends('material_request_ids')
    def _compute_material_request_count(self):
        """Count number of linked material requests"""
        for request in self:
            request.material_request_count = len(request.material_request_ids)

    @api.depends('line_ids')
    def _compute_line_count(self):
        """Count number of purchase request lines"""
        for request in self:
            request.line_count = len(request.line_ids)

    # Override create to generate sequence
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('test_app.purchase.request') or _('New')
        return super().create(vals_list)

    def unlink(self):
        """Prevent deletion of approved/converted purchase requests"""
        for request in self:
            if request.state not in ('draft', 'cancelled'):
                raise UserError(_('You cannot delete a purchase request in %s state.') % request.state)
        return super().unlink()

    # View Action Methods

    def action_view_material_requests(self):
        """Open linked material requests"""
        self.ensure_one()
        return {
            'name': _('Material Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'test_app.material.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.material_request_ids.ids)],
            'context': {'default_purchase_request_id': self.id},
        }

    def action_view_purchase_order(self):
        """Open linked purchase order"""
        self.ensure_one()
        if not self.purchase_order_id:
            return {}
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
        }

    # Workflow Action Methods

    def action_approve(self):
        """Approve purchase request"""
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft purchase requests can be approved.'))
            if not request.line_ids:
                raise UserError(_('Cannot approve purchase request without any line items.'))
            request.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            request.message_post(
                body=_('Purchase request %s has been approved by %s.') % (request.name, self.env.user.name),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_cancel(self):
        """Cancel purchase request"""
        for request in self:
            if request.state == 'converted':
                raise UserError(_('Cannot cancel a purchase request that has been converted to a purchase order.'))
            # Unlink material requests to free them for other purchase requests
            request.material_request_ids.write({'purchase_request_id': False})
            request.write({'state': 'cancelled'})
            request.message_post(
                body=_('Purchase request %s has been cancelled.') % request.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_set_to_draft(self):
        """Reset purchase request to draft"""
        for request in self:
            if request.state == 'converted':
                raise UserError(_('Cannot reset a converted purchase request to draft.'))
            request.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
            })
        return True

    def action_convert_to_po(self):
        """Convert purchase request to purchase order"""
        self.ensure_one()

        if self.state != 'approved':
            raise UserError(_('Only approved purchase requests can be converted to purchase orders.'))

        if not self.vendor_id:
            # Open wizard to select vendor
            return {
                'name': _('Select Vendor'),
                'type': 'ir.actions.act_window',
                'res_model': 'test_app.purchase.request.convert.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_purchase_request_id': self.id},
            }

        # Create purchase order
        po_vals = self._prepare_purchase_order_values()
        purchase_order = self.env['purchase.order'].create(po_vals)

        # Create purchase order lines from purchase request lines
        for line in self.line_ids:
            po_line_vals = line._prepare_purchase_order_line_values(purchase_order.id)
            po_line = self.env['purchase.order.line'].create(po_line_vals)
            # Link PO line back to PR line for traceability
            line.write({'purchase_order_line_id': po_line.id})

        # Update purchase request state and link to PO
        self.write({
            'state': 'converted',
            'purchase_order_id': purchase_order.id,
        })

        # Post message
        self.message_post(
            body=_('Purchase request %s has been converted to purchase order %s.') % (
                self.name, purchase_order.name
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Return action to open the created PO
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': purchase_order.id,
        }

    def _prepare_purchase_order_values(self):
        """Prepare values for creating purchase order from this purchase request"""
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_('Please select a vendor before converting to purchase order.'))

        # Get fiscal position based on vendor
        fiscal_position = self.env['account.fiscal.position']._get_fiscal_position(self.vendor_id)

        return {
            'partner_id': self.vendor_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.vendor_id.property_purchase_currency_id.id or self.currency_id.id,
            'fiscal_position_id': fiscal_position.id if fiscal_position else False,
            'payment_term_id': self.vendor_id.property_supplier_payment_term_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.name,
            'material_request_ids': [(6, 0, self.material_request_ids.ids)],
        }


class PurchaseRequestLine(models.Model):
    _name = 'test_app.purchase.request.line'
    _description = 'Purchase Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)

    purchase_request_id = fields.Many2one(
        'test_app.purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='cascade',
        index=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('purchase_ok', '=', True)],
    )

    description = fields.Text(
        string='Description',
    )

    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )

    # Estimated Costs
    estimated_unit_cost = fields.Monetary(
        string='Estimated Unit Cost',
        currency_field='currency_id',
        default=0.0,
    )

    estimated_total_cost = fields.Monetary(
        string='Estimated Total Cost',
        compute='_compute_estimated_total_cost',
        store=True,
        currency_field='currency_id',
    )

    # Related fields
    currency_id = fields.Many2one(
        related='purchase_request_id.currency_id',
        store=True,
        string='Currency',
    )

    state = fields.Selection(
        related='purchase_request_id.state',
        string='Status',
        store=True,
    )

    # Traceability - Link to source material request lines
    material_request_line_ids = fields.Many2many(
        'test_app.material.request.line',
        relation='test_app_mr_line_pr_line_rel',
        column1='purchase_request_line_id',
        column2='material_request_line_id',
        string='Material Request Lines',
        help='Source material request lines for this purchase request line',
    )

    # Integration - Link to created purchase order line
    purchase_order_line_id = fields.Many2one(
        'purchase.order.line',
        string='Purchase Order Line',
        readonly=True,
        copy=False,
    )

    @api.depends('quantity', 'estimated_unit_cost')
    def _compute_estimated_total_cost(self):
        """Compute estimated total cost from quantity and unit cost"""
        for line in self:
            line.estimated_total_cost = line.quantity * line.estimated_unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill UOM and description when product is selected"""
        if self.product_id:
            self.uom_id = self.product_id.uom_po_id or self.product_id.uom_id
            if self.product_id.description_purchase:
                self.description = self.product_id.description_purchase
            elif not self.description:
                self.description = self.product_id.display_name
            # Set estimated cost from standard price
            self.estimated_unit_cost = self.product_id.standard_price

    @api.constrains('quantity')
    def _check_quantity(self):
        """Ensure quantity is greater than zero"""
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    def _prepare_purchase_order_line_values(self, purchase_order_id):
        """Prepare values for creating purchase order line"""
        self.ensure_one()

        # Get price from product supplier info if available
        product_supplier = self.product_id.seller_ids.filtered(
            lambda s: s.partner_id == self.purchase_request_id.vendor_id
        )[:1]

        price_unit = product_supplier.price if product_supplier else self.estimated_unit_cost

        return {
            'order_id': purchase_order_id,
            'product_id': self.product_id.id,
            'name': self.description or self.product_id.display_name,
            'product_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'price_unit': price_unit,
            'date_planned': self.purchase_request_id.date_required or fields.Datetime.now(),
        }
