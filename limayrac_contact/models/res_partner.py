from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    birthday_date = fields.Date(string='Date de naissance')
    civilite = fields.Selection([
        ('mr', 'Monsieur'),
        ('mrs', 'Madame'),
    ], string='Civilité')
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
    res_partner_opco_id = fields.Many2one(
        'res.partner.opco',
        string='OPCO',
        index=True)
    partner_type_ids = fields.Many2many('res.partner.type', string='Type de partenaire', compute='_compute_partner_type_ids', store=True)
    headquarters_id = fields.Many2one('res.partner', string='Siège social', domain="[('is_company', '=', True), ('id', '!=', id)]")
    childs_company_ids = fields.One2many('res.partner', 'headquarters_id', string='Filiales')
    company_contract_ids = fields.One2many('limayrac.contract', 'company_partner_id', string='Contrats')
    res_partner_cursus_ids = fields.One2many('res.partner.cursus', 'res_partner_id', string='Cursus du contact')
    cursus_formations_ids = fields.Many2many(
        'limayrac.formations',
        string='Classes du cursus',
        compute='_compute_cursus_formations_ids',
        store=True)
    cursus_formation_group_ids = fields.Many2many(
        'limayrac.formations.group',
        'res_partner_cursus_formation_group_rel', 'res_partner_id', 'formation_id',
        string='Formations suivies',
        compute='_compute_cursus_formations_ids',
        store=True)
    limayrac_formations_ids = fields.Many2many('limayrac.formations', 'res_partner_limayrac_formations_rel', 'res_partner_id', 'limayrac_formations_id', string='Formations Limayrac')
    limayrac_formations_resp_ids = fields.Many2many('limayrac.formations', 'res_partner_limayrac_formations_resp_rel', 'res_partner_id', 'limayrac_formations_id', string='Responsable de sections Limayrac')
    formation_group_ids = fields.Many2many(
        'limayrac.formations.group', 'res_partner_limayrac_formations_group_rel', 'res_partner_id', 'group_id',
        string='Formations (formateur)')
    formation_group_resp_ids = fields.Many2many(
        'limayrac.formations.group', 'res_partner_limayrac_formations_group_resp_rel', 'res_partner_id', 'group_id',
        string='Formations (responsable pédagogique)')

    @api.depends('res_partner_cursus_ids.limayrac_formations_id', 'res_partner_cursus_ids.formation_id')
    def _compute_cursus_formations_ids(self):
        for record in self:
            record.cursus_formations_ids = record.res_partner_cursus_ids.limayrac_formations_id
            record.cursus_formation_group_ids = record.res_partner_cursus_ids.formation_id

    @api.depends('limayrac_formations_ids', 'limayrac_formations_resp_ids',
                 'formation_group_ids', 'formation_group_resp_ids',
                 'res_partner_cursus_ids', 'res_partner_cursus_ids.end_date',
                 'res_partner_cursus_ids.limayrac_formations_id',
                 'user_ids', 'is_company', 'parent_id')
    def _compute_partner_type_ids(self):
        empty = self.env['res.partner.type']
        # raise_if_not_found=False : ce compute peut se déclencher pendant
        # l'installation (init_models), avant que les types de démo/données
        # ne soient chargés en base. On tolère alors leur absence.
        #FORMATEUR
        type_001 = self.env.ref('limayrac_contact.type_001', raise_if_not_found=False) or empty
        #ETUDIANTS
        type_002 = self.env.ref('limayrac_contact.type_002', raise_if_not_found=False) or empty
        #ADMINISTRATIF
        type_003 = self.env.ref('limayrac_contact.type_003', raise_if_not_found=False) or empty
        #ENTREPRISE
        type_004 = self.env.ref('limayrac_contact.type_004', raise_if_not_found=False) or empty
        #ANCIEN ELEVE
        type_005 = self.env.ref('limayrac_contact.type_005', raise_if_not_found=False) or empty
        today = fields.Date.today()
        for record in self:
            types = self.env['res.partner.type']
            # Un cursus sans date de fin est en cours.
            current_formations = record.res_partner_cursus_ids.filtered(
                lambda c: not c.end_date or c.end_date >= today)
            if record.limayrac_formations_ids or record.limayrac_formations_resp_ids \
                    or record.formation_group_ids or record.formation_group_resp_ids:
                types |= type_001
            if record.res_partner_cursus_ids and current_formations:
                types |= type_002
            if record.user_ids:
                types |= type_003
            if record.is_company or record.parent_id and record.parent_id.id != self.env.company.id:
                types |= type_004
            if record.res_partner_cursus_ids and not current_formations:
                types |= type_005
            record.partner_type_ids = types

    @api.model
    def _cron_update_partner_types(self):
        """Recalcule les types des contacts ayant un cursus.

        Le type Étudiant / Ancien étudiant dépend de la date du jour : la
        valeur stockée ne change pas d'elle-même quand un cursus se termine.
        """
        partners = self.with_context(active_test=False).search([('res_partner_cursus_ids', '!=', False)])
        partners.modified(['res_partner_cursus_ids'])
        partners.flush_recordset(['partner_type_ids'])
        return len(partners)