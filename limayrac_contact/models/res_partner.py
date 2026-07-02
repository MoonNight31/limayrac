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
    partner_type_ids = fields.Many2many('res.partner.type', string='Type de partenaire', compute='_compute_partner_type_ids')
    headquarters_id = fields.Many2one('res.partner', string='Siège social', domain="[('is_company', '=', True), ('id', '!=', id)]")
    childs_company_ids = fields.One2many('res.partner', 'headquarters_id', string='Filiales')
    res_partner_cursus_ids = fields.One2many('res.partner.cursus', 'res_partner_id', string='Cursus du contact')
    limayrac_formations_ids = fields.Many2many('limayrac.formations', 'res_partner_limayrac_formations_rel', 'res_partner_id', 'limayrac_formations_id', string='Formations Limayrac')
    limayrac_formations_resp_ids = fields.Many2many('limayrac.formations', 'res_partner_limayrac_formations_resp_rel', 'res_partner_id', 'limayrac_formations_id', string='Responsable de sections Limayrac')

    @api.depends('limayrac_formations_ids', 'limayrac_formations_resp_ids', 'res_partner_cursus_ids', 'user_id', 'is_company')
    def _compute_partner_type_ids(self):
        type_001 = self.env.ref('limayrac_contact.type_001')
        type_002 = self.env.ref('limayrac_contact.type_002')
        type_003 = self.env.ref('limayrac_contact.type_003')
        type_004 = self.env.ref('limayrac_contact.type_004')
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
            record.partner_type_ids = types