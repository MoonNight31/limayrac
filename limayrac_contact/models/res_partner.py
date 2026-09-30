from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    birthday_date = fields.Date(string='Date de naissance')
    res_partner_department_ids = fields.One2many(
        'res.partner.department',
        'res_partner_id',
        string='Services')
    is_partenaire = fields.Boolean(default=False)
    is_prospect = fields.Boolean(default=False)
    is_blacklist = fields.Boolean(default=False)
    res_partner_naf_id = fields.Many2one(
        'res.partner.naf',
        string='Code NAF')
    partner_type_ids = fields.Many2many('res.partner.type', string='Type de partenaire', compute='_compute_partner_type_ids', store=True)
    headquarters_id = fields.Many2one('res.partner', string='Siège social', domain="[('is_company', '=', True), ('id', '!=', id)]")
    childs_company_ids = fields.One2many('res.partner', 'headquarters_id', string='Filiales')
    company_contract_ids = fields.One2many('limayrac.contract', 'company_partner_id', string='Contrats')
    res_partner_cursus_ids = fields.One2many('res.partner.cursus', 'res_partner_id', string='Cursus du contact')
    cursus_formations_ids = fields.Many2many(
        'limayrac.formations',
        string='Formations du cursus',
        compute='_compute_cursus_formations_ids',
        store=True)
    limayrac_formations_ids = fields.Many2many('limayrac.formations', 'res_partner_limayrac_formations_rel', 'res_partner_id', 'limayrac_formations_id', string='Formations Limayrac')
    limayrac_formations_resp_ids = fields.Many2many('limayrac.formations', 'res_partner_limayrac_formations_resp_rel', 'res_partner_id', 'limayrac_formations_id', string='Responsable de sections Limayrac')

    @api.depends('res_partner_cursus_ids.limayrac_formations_id')
    def _compute_cursus_formations_ids(self):
        for record in self:
            record.cursus_formations_ids = record.res_partner_cursus_ids.limayrac_formations_id

    @api.depends('limayrac_formations_ids', 'limayrac_formations_resp_ids', 'res_partner_cursus_ids', 'user_id', 'is_company')
    def _compute_partner_type_ids(self):
        empty = self.env['res.partner.type']
        # raise_if_not_found=False : ce compute peut se déclencher pendant
        # l'installation (init_models), avant que les types de démo/données
        # ne soient chargés en base. On tolère alors leur absence.
        type_001 = self.env.ref('limayrac_contact.type_001', raise_if_not_found=False) or empty
        type_002 = self.env.ref('limayrac_contact.type_002', raise_if_not_found=False) or empty
        type_003 = self.env.ref('limayrac_contact.type_003', raise_if_not_found=False) or empty
        type_004 = self.env.ref('limayrac_contact.type_004', raise_if_not_found=False) or empty
        type_005 = self.env.ref('limayrac_contact.type_005', raise_if_not_found=False) or empty
        for record in self:
            types = self.env['res.partner.type']
            if record.limayrac_formations_ids or record.limayrac_formations_resp_ids:
                types |= type_001
            if record.res_partner_cursus_ids:
                types |= type_002
            if record.user_ids:
                types |= type_003
            if record.is_company or record.parent_id and record.parent_id.id != self.env.company.id:
                types |= type_004
            current_formations = record.res_partner_cursus_ids.filtered(lambda c: not c.end_date or c.end_date < fields.Date.today())
            if record.res_partner_cursus_ids and not current_formations:
                types |= type_005
            record.partner_type_ids = types