# -*- coding: utf-8 -*-
# Part of test_app. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MaterialRequest(models.Model):
    _name = 'test_app.material.request'
    _description = 'Material Request'
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

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        index=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
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
        required=True,
        default=lambda self: fields.Date.context_today(self),
        tracking=True,
    )

    # Status and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    # Additional Information
    reason = fields.Text(
        string='Reason for Request',
        tracking=True,
    )

    rejected_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        tracking=True,
    )

    # Approval Information
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

    rejected_by = fields.Many2one(
        'res.users',
        string='Rejected By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    rejected_date = fields.Datetime(
        string='Rejection Date',
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
    purchase_request_id = fields.Many2one(
        'test_app.purchase.request',
        string='Purchase Request',
        readonly=True,
        copy=False,
        tracking=True,
    )

    # Lines
    line_ids = fields.One2many(
        'test_app.material.request.line',
        'material_request_id',
        string='Request Lines',
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

    line_count = fields.Integer(
        string='Number of Lines',
        compute='_compute_line_count',
    )

    @api.depends('line_ids.estimated_total_cost')
    def _compute_total_estimated_cost(self):
        """Compute total estimated cost from all lines"""
        for request in self:
            request.total_estimated_cost = sum(request.line_ids.mapped('estimated_total_cost'))

    @api.depends('line_ids')
    def _compute_line_count(self):
        """Count number of request lines"""
        for request in self:
            request.line_count = len(request.line_ids)

    @api.constrains('line_ids')
    def _check_lines(self):
        """Ensure at least one line exists before submission"""
        for request in self:
            if request.state != 'draft' and not request.line_ids:
                raise ValidationError(_('Material request must have at least one line item.'))

    @api.constrains('date_required', 'date_requested')
    def _check_date_required(self):
        """Ensure required date is not before request date"""
        for request in self:
            if request.date_required and request.date_requested:
                if request.date_required < request.date_requested:
                    raise ValidationError(_('Required date cannot be before request date.'))

    # Override create to generate sequence
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('test_app.material.request') or _('New')
        return super().create(vals_list)

    def unlink(self):
        """Prevent deletion of submitted/approved/done material requests"""
        for request in self:
            if request.state not in ('draft', 'rejected'):
                raise UserError(_('You cannot delete a material request in %s state.') % request.state)
        return super().unlink()

    # Workflow Action Methods

    def action_submit(self):
        """Submit material request for approval"""
        for request in self:
            if not request.line_ids:
                raise UserError(_('Cannot submit material request without any line items.'))
            request.write({'state': 'submitted'})
            request._notify_managers('submitted')
            request.message_post(
                body=_('Material request %s has been submitted for approval.') % request.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_approve(self):
        """Approve material request"""
        for request in self:
            if request.state != 'submitted':
                raise UserError(_('Only submitted material requests can be approved.'))
            request.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            request.message_post(
                body=_('Material request %s has been approved by %s.') % (request.name, self.env.user.name),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            # Notify employee
            if request.employee_id.user_id:
                request.message_notify(
                    partner_ids=request.employee_id.user_id.partner_id.ids,
                    body=_('Your material request %s has been approved.') % request.name,
                )
        return True

    def action_reject(self, rejected_reason=None):
        """Reject material request with reason"""
        for request in self:
            if request.state not in ('submitted', 'approved'):
                raise UserError(_('Only submitted or approved material requests can be rejected.'))
            if not rejected_reason:
                raise UserError(_('Rejection reason is required.'))
            request.write({
                'state': 'rejected',
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'rejected_reason': rejected_reason,
            })
            request.message_post(
                body=_('Material request %s has been rejected by %s. Reason: %s') % (
                    request.name, self.env.user.name, rejected_reason
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            # Notify employee
            if request.employee_id.user_id:
                request.message_notify(
                    partner_ids=request.employee_id.user_id.partner_id.ids,
                    body=_('Your material request %s has been rejected. Reason: %s') % (
                        request.name, rejected_reason
                    ),
                )
        return True

    def action_set_to_draft(self):
        """Reset material request to draft"""
        for request in self:
            if request.state == 'done':
                raise UserError(_('Cannot reset a completed material request to draft.'))
            if request.purchase_request_id:
                raise UserError(_(
                    'Cannot reset material request to draft because it is linked to purchase request %s.'
                ) % request.purchase_request_id.name)
            request.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
                'rejected_by': False,
                'rejected_date': False,
                'rejected_reason': False,
            })
        return True

    def action_mark_done(self):
        """Mark material request as done"""
        for request in self:
            if request.state != 'approved':
                raise UserError(_('Only approved material requests can be marked as done.'))
            request.write({'state': 'done'})
            request.message_post(
                body=_('Material request %s has been marked as done.') % request.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def _notify_managers(self, event):
        """Notify department managers of material request events"""
        for request in self:
            if not request.department_id or not request.department_id.manager_id:
                continue

            manager = request.department_id.manager_id
            if not manager.user_id:
                continue

            if event == 'submitted':
                body = _(
                    'Material request %s has been submitted by %s and requires your approval.'
                ) % (request.name, request.employee_id.name)
            else:
                body = _('Material request %s: %s') % (request.name, event)

            request.message_notify(
                partner_ids=manager.user_id.partner_id.ids,
                body=body,
            )

    def action_view_purchase_request(self):
        """Open the linked purchase request"""
        self.ensure_one()
        if not self.purchase_request_id:
            return {}
        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'test_app.purchase.request',
            'view_mode': 'form',
            'res_id': self.purchase_request_id.id,
        }


class MaterialRequestLine(models.Model):
    _name = 'test_app.material.request.line'
    _description = 'Material Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)

    material_request_id = fields.Many2one(
        'test_app.material.request',
        string='Material Request',
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

    # Related fields from material request
    currency_id = fields.Many2one(
        related='material_request_id.currency_id',
        store=True,
        string='Currency',
    )

    state = fields.Selection(
        related='material_request_id.state',
        string='Status',
        store=True,
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
            # Set estimated cost from standard price or recent PO
            self.estimated_unit_cost = self.product_id.standard_price

    @api.constrains('quantity')
    def _check_quantity(self):
        """Ensure quantity is greater than zero"""
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    @api.constrains('estimated_unit_cost')
    def _check_estimated_cost(self):
        """Ensure estimated cost is not negative"""
        for line in self:
            if line.estimated_unit_cost < 0:
                raise ValidationError(_('Estimated cost cannot be negative.'))
