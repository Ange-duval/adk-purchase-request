from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdkPurchaseRequestOrder(models.Model):
    _name = 'adk.purchase.request.order'
    _description = "Demande d'Achat ADK"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="Référence de la demande", required=True, readonly=True, default='Nouveau', copy=False, tracking=True)

    # --- Colonne gauche ---
    demandeur_id = fields.Many2one('res.users', string="Demandeur", default=lambda self: self.env.user, required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string="Département", tracking=True)
    assigned_id = fields.Many2one('res.users', string="Approbateur", tracking=True)
    request_date = fields.Date(string="Date de création", default=fields.Date.context_today, required=True, tracking=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string="Site de livraison",
        domain="[('company_id', '=', company_id), ('code', '=', 'incoming')]",
        tracking=True,
    )
    company_id = fields.Many2one('res.company', string="Société", default=lambda self: self.env.company, required=True, tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Unité opérationnelle", domain="[('company_id', '=', company_id)]", tracking=True)
    currency_id = fields.Many2one('res.currency', string="Devise", default=lambda self: self.env.company.currency_id, required=True, tracking=True)

    # --- Colonne droite ---
    origin = fields.Char(string="Document source")
    description = fields.Text(string="Description")
    procurement_group_id = fields.Many2one('procurement.group', string="Groupe d'approvisionnement")
    reparation_ref = fields.Char(string="Réparation", default='/')

    expected_date = fields.Date(string="Date souhaitée", tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('to_approve', 'A approuver'),
        ('approved', 'Approuvé'),
        ('refused', 'Refusé'),
        ('done', 'Terminé'),
    ], string="État", default='draft', tracking=True, copy=False)

    line_ids = fields.One2many('adk.purchase.request.line', 'order_id', string="Articles", copy=True)
    purchase_order_ids = fields.One2many('purchase.order', 'adk_request_id', string="Bons de commande")
    picking_ids = fields.Many2many(
        'stock.picking',
        compute='_compute_picking_ids',
        string="Transferts",
        readonly=True,
    )
    # CORRECTION : accès direct aux lignes de commande fournisseur générées,
    # comme dans les modules natifs Odoo (Achats > Demande de prix > Ligne de commande).
    purchase_order_line_ids = fields.Many2many(
        'purchase.order.line',
        compute='_compute_purchase_order_line_ids',
        string="Lignes de commande",
        readonly=True,
    )

    line_count = fields.Integer(compute='_compute_counts', string="Nb. lignes", compute_sudo=True, store=True)
    purchase_count = fields.Integer(compute='_compute_counts', string="Bons de commande", compute_sudo=True)
    picking_count = fields.Integer(compute='_compute_counts', string="Transferts", compute_sudo=True)
    purchase_order_line_count = fields.Integer(compute='_compute_counts', string="Nb. lignes de commande", compute_sudo=True)

    total_qty_requested = fields.Float(compute='_compute_line_stats', string="Qté totale demandée", compute_sudo=True, store=True)
    total_estimated_cost = fields.Monetary(compute='_compute_line_stats', string="Coût estimé total", currency_field='currency_id', compute_sudo=True, store=True)
    is_late = fields.Boolean(compute='_compute_is_late', string="En retard", compute_sudo=True, store=True)
    pending_rfq_lines = fields.Integer(
        compute='_compute_pending_rfq_lines', string="Articles non encore soumis à une demande de prix",
        compute_sudo=True, store=True,
    )

    @api.depends('purchase_order_ids', 'line_ids', 'line_ids.purchase_order_line_ids')
    def _compute_counts(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.purchase_count = len(record.purchase_order_ids)
            record.picking_count = len(record._get_pickings())
            record.purchase_order_line_count = len(record.line_ids.purchase_order_line_ids)

    @api.depends('line_ids.purchase_order_line_ids')
    def _compute_purchase_order_line_ids(self):
        for record in self:
            record.purchase_order_line_ids = [(6, 0, record.line_ids.purchase_order_line_ids.ids)]

    def _get_pickings(self):
        """Récupère les transferts liés aux bons de commande générés, de façon défensive
        (le nom exact du champ natif peut varier selon la configuration purchase_stock)."""
        self.ensure_one()
        pickings = self.env['stock.picking']
        for po in self.purchase_order_ids:
            if 'picking_ids' in po._fields:
                pickings |= po.picking_ids
        if not pickings and 'stock.picking' in self.env and 'purchase_id' in self.env['stock.picking']._fields:
            pickings = self.env['stock.picking'].search([('purchase_id', 'in', self.purchase_order_ids.ids)])
        return pickings

    def _compute_picking_ids(self):
        for record in self:
            record.picking_ids = record._get_pickings()

    @api.depends('line_ids.qty', 'line_ids.estimated_subtotal')
    def _compute_line_stats(self):
        for record in self:
            record.total_qty_requested = sum(record.line_ids.mapped('qty'))
            record.total_estimated_cost = sum(record.line_ids.mapped('estimated_subtotal'))

    @api.depends('line_ids.line_status')
    def _compute_pending_rfq_lines(self):
        for record in self:
            record.pending_rfq_lines = len(record.line_ids.filtered(lambda line: line.line_status == 'to_order'))

    @api.depends('expected_date', 'state')
    def _compute_is_late(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_late = bool(
                record.expected_date and record.expected_date < today and record.state not in ('done', 'refused')
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('adk.purchase.request.order') or 'Nouveau'
        return super().create(vals_list)

    # --- Lignes modifiables hors brouillon (nécessaires au flux demande de prix) ---
    _RFQ_EDIT_SAFE_LINE_FIELDS = {'include_in_rfq', 'supplier_id'}

    def _line_commands_are_benign(self, commands):
        """Vrai si les commandes ligne ne modifient QUE la sélection demande de prix
        (include_in_rfq / supplier_id) sans toucher au contenu de la demande."""
        if not commands:
            return True
        for command in commands:
            if not isinstance(command, (list, tuple)) or len(command) < 2:
                continue
            op = command[0]
            if op == 1 and len(command) >= 3 and isinstance(command[2], dict):
                line = self.env['adk.purchase.request.line'].browse(command[1])
                benign = True
                for field, value in command[2].items():
                    if field in self._RFQ_EDIT_SAFE_LINE_FIELDS:
                        continue
                    if line._fields[field].type in ('one2many', 'many2many'):
                        benign = False
                        break
                    cached = line._fields[field].convert_to_cache(value, line)
                    current = line._fields[field].convert_to_cache(line[field], line)
                    if cached != current:
                        benign = False
                        break
                if benign:
                    continue
            return False
        return True

    def write(self, vals):
        protected = {
            'demandeur_id', 'department_id', 'assigned_id', 'request_date',
            'picking_type_id', 'company_id', 'warehouse_id', 'currency_id',
            'origin', 'description', 'procurement_group_id', 'reparation_ref',
            'expected_date', 'line_ids',
        }
        for record in self:
            if record.state != 'draft':
                changed = set()
                for field in protected:
                    if field not in vals:
                        continue
                    if record._fields[field].type == 'one2many':
                        if vals[field] and not self._line_commands_are_benign(vals[field]):
                            changed.add(field)
                    else:
                        new_cache = record._fields[field].convert_to_cache(vals[field], record)
                        current_cache = record._fields[field].convert_to_cache(record[field], record)
                        if new_cache != current_cache:
                            changed.add(field)
                if changed:
                    raise UserError(_("Une demande qui n'est plus en brouillon est verrouillée. Réinitialisez-la avant de modifier ses données."))
        return super().write(vals)

    def unlink(self):
        """Anti-fraude : interdit de supprimer une demande d'achat qui a déjà généré
        des demandes de prix, des commandes fournisseur ou des réceptions."""
        for record in self:
            orders = record.purchase_order_ids
            po_lines = record.line_ids.purchase_order_line_ids
            pickings = record._get_pickings()
            if orders or po_lines or pickings:
                raise UserError(_(
                    "Impossible de supprimer cette demande d'achat : elle possède déjà "
                    "des demandes de prix / commandes fournisseur (%s) ou des réceptions (%s)."
                ) % (
                    ", ".join(orders.mapped('name')) or '-',
                    len(pickings),
                ))
        return super().unlink()

    # --- Workflow ---

    def action_request_approval(self):
        """Bouton 'Demander l'autorisation' : Brouillon -> A approuver."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Seule une demande en brouillon peut être soumise à approbation."))
            if not record.line_ids:
                raise UserError(_("Veuillez ajouter au moins une ligne avant de demander l'autorisation."))
            if not record.assigned_id:
                raise UserError(_("Renseignez l'approbateur avant de demander l'autorisation."))
            invalid_lines = record.line_ids.filtered(lambda line: line.qty <= 0 or not line.product_id)
            if invalid_lines:
                raise UserError(_("Chaque ligne doit contenir un article et une quantité strictement positive."))
        self.write({'state': 'to_approve'})

    def action_approve(self):
        """Manager uniquement : A approuver -> Approuvé"""
        if not self.env.user.has_group('adk_purchase_request.group_adk_purchase_request_manager'):
            raise UserError(_("Seul un Manager Demande d'Achat peut approuver cette demande."))
        for record in self:
            if record.state != 'to_approve':
                raise UserError(_("Seules les demandes à approuver peuvent être approuvées."))
        self.write({'state': 'approved'})

    def action_refuse(self):
        """Manager uniquement : A approuver -> Refusé"""
        if not self.env.user.has_group('adk_purchase_request.group_adk_purchase_request_manager'):
            raise UserError(_("Seul un Manager Demande d'Achat peut refuser cette demande."))
        for record in self:
            if record.state != 'to_approve':
                raise UserError(_("Seules les demandes à approuver peuvent être refusées."))
        self.write({'state': 'refused'})

    def action_reset_to_draft(self):
        """Bouton 'Réinitialiser' : A approuver / Refusé / Approuvé -> Brouillon.
        Une demande approuvée ne peut être réinitialisée que par un Manager
        Demande d'Achat (ou l'admin) afin de corriger des données."""
        for record in self:
            if record.state == 'approved' and not self.env.user.has_group(
                'adk_purchase_request.group_adk_purchase_request_manager'
            ):
                raise UserError(_(
                    "Seul un Manager Demande d'Achat peut réinitialiser une demande approuvée."
                ))
            if record.state not in ('to_approve', 'refused', 'approved'):
                raise UserError(_("Cette demande ne peut pas être réinitialisée depuis son état actuel."))
        self.write({'state': 'draft'})

    def action_done(self):
        """Bouton 'Terminé' : marque une demande approuvée comme traitée."""
        if not self.env.user.has_group('adk_purchase_request.group_adk_purchase_request_manager'):
            raise UserError(_("Seul un Manager Demande d'Achat peut terminer une demande."))
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Seules les demandes approuvées peuvent être terminées."))
        self.write({'state': 'done'})

    def action_create_purchase_orders(self):
        """Bouton 'Créer une demande de prix' : génère une demande de prix (couche de
        commande fournisseur) par fournisseur, pour les seuls articles cochés.
        Chaque clic crée une nouvelle demande de prix numérotée nativement ; les
        articles non cochés restent en attente pour une prochaine demande."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("La demande doit être approuvée avant de créer une demande de prix."))
        pending = self.line_ids.filtered(lambda line: line.line_status == 'to_order')
        selected = pending.filtered('include_in_rfq')
        if not selected:
            raise UserError(_(
                "Cochez au moins un article (colonne « Inclure dans la demande de prix ») "
                "avant de créer la demande de prix."
            ))
        missing = selected.filtered(lambda line: not line.supplier_id)
        if missing:
            raise UserError(_(
                "Renseignez un fournisseur pour chaque article sélectionné (article(s) : %s)."
            ) % ", ".join(missing.mapped('product_id.display_name')))

        purchase_orders = self.env['purchase.order']
        for supplier in selected.mapped('supplier_id'):
            supplier_lines = selected.filtered(lambda line: line.supplier_id == supplier)
            order_line_vals = []
            for line in supplier_lines:
                order_line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.display_name,
                    'product_qty': line.qty,
                    'product_uom': line.product_uom_id.id,
                    'price_unit': line.estimated_unit_cost,
                    'date_planned': fields.Datetime.to_datetime(line.date_required or self.expected_date or fields.Date.context_today(self)),
                    'adk_request_line_id': line.id,
                }))
            purchase_order = self.env['purchase.order'].create({
                'partner_id': supplier.id,
                'origin': self.name,
                'currency_id': self.currency_id.id,
                'adk_request_id': self.id,
                **({'picking_type_id': self.picking_type_id.id} if self.picking_type_id and 'picking_type_id' in self.env['purchase.order']._fields else {}),
                **({'group_id': self.procurement_group_id.id} if self.procurement_group_id and 'group_id' in self.env['purchase.order']._fields else {}),
                'order_line': order_line_vals,
            })
            purchase_orders |= purchase_order

        selected.include_in_rfq = False
        self.write({'state': 'approved'})
        return {
            'name': _('Demandes de prix'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', purchase_orders.ids)],
        }

    def action_view_purchase_orders(self):
        return {
            'name': _('Bons de commande'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('adk_request_id', '=', self.id)],
            'context': {'default_adk_request_id': self.id},
        }

    def action_view_pickings(self):
        return {
            'name': _('Transferts'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self._get_pickings().ids)],
        }

    def action_view_purchase_order_lines(self):
        """Accès direct aux lignes de commande fournisseur (tous bons de commande confondus),
        comme dans les modules Achats natifs d'Odoo."""
        return {
            'name': _('Lignes de commande'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'list',
            'domain': [('id', 'in', self.line_ids.purchase_order_line_ids.ids)],
        }


class AdkPurchaseRequestLine(models.Model):
    _name = 'adk.purchase.request.line'
    _description = "Ligne de demande d'achat"

    order_id = fields.Many2one('adk.purchase.request.order', ondelete='cascade')
    company_id = fields.Many2one(related='order_id.company_id', store=True, readonly=True, string="Société")
    currency_id = fields.Many2one(related='order_id.currency_id', string="Devise", readonly=True)
    request_date = fields.Date(related='order_id.request_date', store=True, string="Date de la demande")
    state = fields.Selection(related='order_id.state', store=True, string="État de la demande")

    product_id = fields.Many2one('product.product', string="Article", required=True)
    description = fields.Char(string="Description")
    destination_location_id = fields.Many2one('stock.location', string="Destinations")
    qty = fields.Float(string="Quantité", default=1.0, required=True)
    product_uom_id = fields.Many2one('uom.uom', string="UoM", compute='_compute_product_uom_id', store=True, readonly=True)
    date_required = fields.Date(string="Date de la demande")
    estimated_unit_cost = fields.Monetary(string="Coût unitaire estimé", currency_field='currency_id')
    estimated_subtotal = fields.Monetary(compute='_compute_estimated_subtotal', string="Coût estimé", currency_field='currency_id', store=True)
    supplier_id = fields.Many2one('res.partner', string="Fournisseur suggéré", domain=[('supplier_rank', '>', 0)])
    include_in_rfq = fields.Boolean(string="Inclure dans la demande de prix", default=False, copy=False)

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'adk_request_line_id', string="Lignes de commande")
    rfq_po_qty = fields.Float(compute='_compute_po_stats', compute_sudo=True, store=True, string="Qté commandée")
    qty_received = fields.Float(compute='_compute_po_stats', compute_sudo=True, store=True, string="Quantité reçue")
    ordered_subtotal = fields.Monetary(compute='_compute_po_amounts', compute_sudo=True, store=True, string="Montant commandé", currency_field='currency_id')
    received_subtotal = fields.Monetary(compute='_compute_po_amounts', compute_sudo=True, store=True, string="Montant reçu", currency_field='currency_id')
    po_refs = fields.Char(compute='_compute_po_refs', compute_sudo=True, store=True, string="N° commandes acheteurs")
    line_status = fields.Selection([
        ('to_order', 'A commander'),
        ('ordered', 'Commandé'),
        ('received', 'Reçu'),
    ], compute='_compute_po_stats', compute_sudo=True, store=True, string="Statut de l'offre")

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_po_id or line.product_id.uom_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['adk.purchase.request.order'].browse(vals.get('order_id'))
            if order and order.state != 'draft':
                raise UserError(_("Les lignes ne peuvent être ajoutées que sur une demande en brouillon."))
        return super().create(vals_list)

    def write(self, vals):
        protected = {
            'product_id', 'description', 'destination_location_id', 'qty',
            'date_required', 'estimated_unit_cost', 'order_id',
        }
        for line in self:
            if line.order_id.state != 'draft' and protected.intersection(vals):
                raise UserError(_("Les données d'une ligne sont verrouillées après soumission de la demande."))
            if line.order_id.state != 'approved' and {'include_in_rfq', 'supplier_id'}.intersection(vals):
                raise UserError(_("La sélection fournisseur n'est disponible que pour une demande approuvée."))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda line: line.order_id.state != 'draft'):
            raise UserError(_("Une ligne ne peut être supprimée qu'en brouillon."))
        return super().unlink()

    @api.depends('qty', 'estimated_unit_cost')
    def _compute_estimated_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.qty * line.estimated_unit_cost

    @api.depends('purchase_order_line_ids.product_qty', 'purchase_order_line_ids.qty_received', 'purchase_order_line_ids.order_id.state')
    def _compute_po_stats(self):
        for line in self:
            po_lines = line.purchase_order_line_ids.filtered(lambda pol: pol.order_id.state != 'cancel')
            line.rfq_po_qty = sum(po_lines.mapped('product_qty'))
            line.qty_received = sum(po_lines.mapped('qty_received'))
            if not po_lines:
                line.line_status = 'to_order'
            elif line.qty_received >= line.qty and line.qty > 0:
                line.line_status = 'received'
            else:
                line.line_status = 'ordered'

    @api.depends(
        'purchase_order_line_ids.price_subtotal',
        'purchase_order_line_ids.qty_received',
        'purchase_order_line_ids.price_unit',
        'purchase_order_line_ids.order_id.state',
    )
    def _compute_po_amounts(self):
        for line in self:
            po_lines = line.purchase_order_line_ids.filtered(lambda pol: pol.order_id.state != 'cancel')
            line.ordered_subtotal = sum(po_lines.mapped('price_subtotal'))
            line.received_subtotal = sum(
                po_line.qty_received * po_line.price_unit for po_line in po_lines
            )

    @api.depends('purchase_order_line_ids.order_id.name', 'purchase_order_line_ids.order_id.state')
    def _compute_po_refs(self):
        for line in self:
            line.po_refs = ', '.join(line.purchase_order_line_ids.filtered(lambda pol: pol.order_id.state != 'cancel').order_id.mapped('name'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.description = line.product_id.display_name
                line.estimated_unit_cost = line.product_id.standard_price
                if line.product_id.seller_ids:
                    line.supplier_id = line.product_id.seller_ids[0].partner_id


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    adk_request_id = fields.Many2one('adk.purchase.request.order', string="Demande d'achat source", ondelete='set null', tracking=True)

    def action_view_adk_request(self):
        """Retour direct vers la demande d'achat ADK à l'origine de ce bon de commande."""
        self.ensure_one()
        return {
            'name': _("Demande d'achat"),
            'type': 'ir.actions.act_window',
            'res_model': 'adk.purchase.request.order',
            'view_mode': 'form',
            'res_id': self.adk_request_id.id,
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    adk_request_line_id = fields.Many2one('adk.purchase.request.line', string="Ligne de demande source", ondelete='set null')
