from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class LimayracContract(models.Model):
    _name = 'limayrac.contract'
    _description = 'Contrat alternance / stage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False,
                       default=lambda self: 'Nouveau', readonly=True)
    contract_type = fields.Selection(
        [('1', 'Stage'), ('2', 'Alternance')],
        string='Type de contrat', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'En attente signature'),
        ('company_signed', "Signé par l'entreprise"),
        ('cfa_signed', 'Signé par le CFA'),
        ('validated', 'Validé'),
        ('running', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    date_integration = fields.Date(string='Date intégration', tracking=True)

    crm_lead_id = fields.Many2one('crm.lead', string='Opportunité', ondelete='set null', index=True)
    company_currency = fields.Many2one(
        'res.currency', string='Devise', related='crm_lead_id.company_currency')
    expected_revenue = fields.Monetary(
        string='Revenu espéré', related='crm_lead_id.expected_revenue',
        currency_field='company_currency', readonly=True)
    revenue = fields.Monetary(string='Revenu réel', currency_field='company_currency', tracking=True)

    # --- Les acteurs du contrat ---
    student_id = fields.Many2one(
        'res.partner', string='Étudiant', required=True, tracking=True,
        domain="[('is_company', '=', False), ('partner_type_ids.code', '=', 'type_002')]")
    company_partner_id = fields.Many2one(
        'res.partner', string='Entreprise', required=True, tracking=True,
        domain="[('is_company', '=', True)]")
    # OPCO figé à la signature : tant que le contrat est en attente de
    # signature il suit celui de l'entreprise, ensuite il ne bouge plus même
    # si l'entreprise change d'OPCO.
    opco_id = fields.Many2one(
        'res.partner.opco', string='OPCO', tracking=True,
        compute='_compute_opco_id', store=True, readonly=False)
    department_id = fields.Many2one(
        'res.partner.department', string='Service',
        domain="[('res_partner_id', '=', company_partner_id), ('is_blacklisted', '=', False)]")
    company_tutor_id = fields.Many2one(
        'res.partner', string='Tuteur entreprise 1', tracking=True,
        domain="[('is_company', '=', False), ('parent_id', '=', company_partner_id)]")
    company_tutor2_id = fields.Many2one(
        'res.partner', string='Tuteur entreprise 2', tracking=True,
        domain="[('is_company', '=', False), ('parent_id', '=', company_partner_id), ('id', '!=', company_tutor_id)]")

    school_tutor_id = fields.Many2one(
        'res.partner', string='Tuteur école', tracking=True,
        domain="[('is_company', '=', False), ('partner_type_ids.code', 'in', ['type_001', 'type_003'])]")

    # --- Formation suivie ---
    # L'utilisateur choisit la formation ; le cursus correspondant de l'étudiant
    # est retrouvé automatiquement et reste la source de vérité en base.
    cursus_id = fields.Many2one(
        'res.partner.cursus', string='Cursus', required=True,
        domain="[('res_partner_id', '=', student_id)]")
    formation_id = fields.Many2one(
        'limayrac.formations.group', string='Formation', index=True,
        compute='_compute_formation_id',
        inverse='_inverse_formation_id',
        store=True, readonly=False,
        domain="[('id', 'in', student_formation_ids)]")
    student_formation_ids = fields.Many2many(
        'limayrac.formations.group', compute='_compute_student_formation_ids')
    # Classe : facultative, reprise du cursus.
    limayrac_formation_id = fields.Many2one(
        'limayrac.formations', string='Classe',
        related='cursus_id.limayrac_formations_id', store=True, readonly=True)
    title_rncp_id = fields.Many2one(
        'title.rncp', string='Titre RNCP',
        related='limayrac_formation_id.title_rncp_id', readonly=True)

    @api.depends('cursus_id.formation_id')
    def _compute_formation_id(self):
        for record in self:
            if record.cursus_id:
                record.formation_id = record.cursus_id.formation_id
            elif not record.formation_id:
                record.formation_id = False

    @api.depends('student_id.res_partner_cursus_ids.formation_id')
    def _compute_student_formation_ids(self):
        for record in self:
            record.student_formation_ids = record.student_id.res_partner_cursus_ids.formation_id

    @api.depends('company_partner_id.res_partner_opco_id')
    def _compute_opco_id(self):
        for record in self:
            # Un contrat déjà signé garde son OPCO ; on ne complète que s'il
            # n'en a pas (ex. contrat importé sans OPCO).
            if record.state == 'draft' or not record.opco_id:
                record.opco_id = record.company_partner_id.res_partner_opco_id
            else:
                record.opco_id = record.opco_id

    @api.model
    def _find_cursus(self, student, formation):
        """Cursus de l'étudiant correspondant à la formation choisie."""
        cursus = student.res_partner_cursus_ids.filtered(
            lambda c: c.formation_id == formation)
        if not cursus:
            raise ValidationError(
                "%s n'a aucun cursus pour la formation « %s »." % (
                    student.name, formation.name))
        # Plusieurs cursus pour la même formation (redoublement, reprise) :
        # on retient le plus récent.
        return cursus.sorted('start_date', reverse=True)[0]

    def _inverse_formation_id(self):
        for record in self:
            if not record.formation_id or not record.student_id:
                continue
            if record.cursus_id.formation_id == record.formation_id:
                continue
            record.cursus_id = self._find_cursus(record.student_id, record.formation_id)

    start_date = fields.Date(string='Date de début', required=True)
    end_date = fields.Date(string='Date de fin', required=True)
    note = fields.Text(string='Notes')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date < record.start_date:
                raise ValidationError(
                    "La date de fin ne peut pas être antérieure à la date de début.")

    @api.constrains('cursus_id', 'student_id')
    def _check_cursus_student(self):
        for record in self:
            if record.cursus_id.res_partner_id != record.student_id:
                raise ValidationError(
                    "Le cursus sélectionné n'appartient pas à l'étudiant du contrat.")

    @api.constrains('crm_lead_id', 'state', 'student_id', 'company_partner_id',
                    'contract_type', 'formation_id')
    def _check_lead_consistency(self):
        """Le contrat doit correspondre à l'opportunité dont il est issu."""
        for record in self:
            lead = record.crm_lead_id
            if not lead or record.state == 'cancel':
                continue
            others = lead.contract_ids.filtered(lambda c: c.state != 'cancel') - record
            if others:
                raise ValidationError(
                    "L'opportunité « %s » a déjà un contrat (%s)." % (lead.name, others[0].name))
            if not lead.active:
                raise ValidationError(
                    "L'opportunité « %s » est perdue : elle ne peut pas avoir de contrat actif." % lead.name)
            if record.company_partner_id != lead.partner_id.commercial_partner_id:
                raise ValidationError(
                    "L'entreprise du contrat %s (%s) n'est pas celle de l'opportunité « %s »." % (
                        record.name, record.company_partner_id.name, lead.name))
            if record.student_id != lead.res_partner_id:
                raise ValidationError(
                    "L'étudiant du contrat %s doit être l'étudiant choisi sur l'opportunité « %s »." % (
                        record.name, lead.name))
            if lead.type_contract in ('1', '2') and record.contract_type != lead.type_contract:
                raise ValidationError(
                    "Le type du contrat %s ne correspond pas à celui de l'opportunité « %s »." % (
                        record.name, lead.name))
            if lead.formation_id and record.formation_id != lead.formation_id:
                raise ValidationError(
                    "La formation du contrat %s n'est pas la formation « %s » de l'opportunité." % (
                        record.name, lead.formation_id.name))

    @api.constrains('student_id', 'start_date', 'end_date', 'state')
    def _check_student_overlap(self):
        # Un étudiant ne peut pas être engagé dans deux contrats sur la même période.
        for record in self:
            if record.state == 'cancel':
                continue
            overlap = self.search([
                ('id', '!=', record.id),
                ('student_id', '=', record.student_id.id),
                ('state', '!=', 'cancel'),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    "%s a déjà le contrat %s du %s au %s, qui chevauche cette période." % (
                        record.student_id.name, overlap.name,
                        overlap.start_date.strftime('%d/%m/%Y'), overlap.end_date.strftime('%d/%m/%Y')))

    @api.constrains('company_tutor_id', 'company_tutor2_id', 'department_id', 'company_partner_id')
    def _check_company_consistency(self):
        # Les domaines des champs ne sont qu'une aide à la saisie : un write
        # direct (import, ORM, API) les contourne. On revérifie ici.
        for record in self:
            tutors = record.company_tutor_id | record.company_tutor2_id
            if tutors.filtered(lambda t: t.parent_id != record.company_partner_id):
                raise ValidationError(
                    "Les tuteurs entreprise doivent être des contacts de l'entreprise du contrat.")
            if record.company_tutor2_id and not record.company_tutor_id:
                raise ValidationError(
                    "Renseignez le tuteur entreprise 1 avant le tuteur entreprise 2.")
            if record.company_tutor2_id and record.company_tutor2_id == record.company_tutor_id:
                raise ValidationError(
                    "Les deux tuteurs entreprise doivent être des personnes différentes.")
            if record.department_id and record.department_id.res_partner_id != record.company_partner_id:
                raise ValidationError(
                    "Le service sélectionné n'appartient pas à l'entreprise du contrat.")
            if record.department_id.is_blacklisted:
                raise ValidationError(
                    "Ce service est blacklisté : %s" % (record.department_id.reason_blacklist or 'sans motif renseigné'))


    @api.onchange('student_id')
    def _onchange_student_id(self):
        # Un seul cursus pour l'étudiant : on le propose d'office.
        if self.cursus_id.res_partner_id != self.student_id:
            self.cursus_id = False
            self.formation_id = False
        if self.student_id and not self.cursus_id:
            cursus = self.student_id.res_partner_cursus_ids.filtered(
                lambda c: not c.end_date or c.end_date >= fields.Date.today())
            if len(cursus) == 1:
                self.cursus_id = cursus

    @api.onchange('formation_id')
    def _onchange_formation_id(self):
        # Résout le cursus dès la saisie, pour que l'erreur remonte avant
        # l'enregistrement plutôt qu'au moment du create.
        if self.formation_id and self.student_id:
            if self.cursus_id.formation_id != self.formation_id:
                self.cursus_id = self._find_cursus(self.student_id, self.formation_id)

    @api.onchange('company_partner_id')
    def _onchange_company_partner_id(self):
        if self.department_id.res_partner_id != self.company_partner_id:
            self.department_id = False
        if self.company_tutor_id.parent_id != self.company_partner_id:
            self.company_tutor_id = False
        if self.company_tutor2_id.parent_id != self.company_partner_id:
            self.company_tutor2_id = False


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('limayrac.contract') or 'Nouveau'
            # Les deux champs sont requis en base, et compute/inverse ne
            # s'exécutent qu'après l'INSERT : on les aligne dès maintenant.
            # La classe est reprise du cursus : jamais écrite directement.
            vals.pop('limayrac_formation_id', None)
            if not vals.get('cursus_id') and vals.get('formation_id') and vals.get('student_id'):
                vals['cursus_id'] = self._find_cursus(
                    self.env['res.partner'].browse(vals['student_id']),
                    self.env['limayrac.formations.group'].browse(vals['formation_id']),
                ).id
            elif vals.get('cursus_id') and not vals.get('formation_id'):
                cursus = self.env['res.partner.cursus'].browse(vals['cursus_id'])
                vals['formation_id'] = cursus.formation_id.id
            elif not vals.get('cursus_id'):
                raise ValidationError("La formation est obligatoire sur un contrat.")
        records = super().create(vals_list)
        records.crm_lead_id._sync_stage()
        return records

    def write(self, vals):
        # L'étape de l'opportunité suit le contrat : on resynchronise
        # l'ancienne et la nouvelle opportunité.
        leads = self.crm_lead_id
        res = super().write(vals)
        if {'state', 'crm_lead_id'} & set(vals):
            (leads | self.crm_lead_id)._sync_stage()
        return res

    def unlink(self):
        leads = self.crm_lead_id
        res = super().unlink()
        leads.exists()._sync_stage()
        return res

    def _check_ready_to_sign(self):
        """Un brouillon peut rester incomplet, pas un contrat signé."""
        for record in self:
            missing = []
            if not record.department_id:
                missing.append('le service')
            if not record.school_tutor_id:
                missing.append('le tuteur école')
            if not record.company_tutor_id:
                missing.append('au moins un tuteur entreprise')
            if missing:
                raise ValidationError(
                    "Impossible de signer le contrat %s : renseignez %s." % (
                        record.name, ', '.join(missing)))

    def _check_state(self, expected_state, action_label):
        # Les boutons sont masqués hors de leur étape, mais un appel direct
        # (RPC, double-clic sur un formulaire périmé) les contourne.
        wrong = self.filtered(lambda c: c.state != expected_state)
        if wrong:
            raise UserError("Action « %s » impossible sur le contrat %s à l'étape « %s »." % (
                action_label, wrong[0].name,
                dict(self._fields['state'].selection)[wrong[0].state]))

    def action_company_sign(self):
        self._check_state('draft', "Signature entreprise")
        self._check_ready_to_sign()
        self.write({'state': 'company_signed'})

    def action_cfa_sign(self):
        self._check_state('company_signed', "Signature CFA")
        self.write({'state': 'cfa_signed'})

    def action_validate(self):
        self._check_state('cfa_signed', "Valider")
        self.write({'state': 'validated'})
        for record in self:
            record.date_integration = record.start_date + relativedelta(months=3)
        # Un contrat validé alors que sa période a déjà commencé ne doit pas
        # attendre le passage du cron le lendemain.
        self._update_state_from_dates()

    def _update_state_from_dates(self):
        """Fait avancer le contrat selon ses dates, sans action manuelle.

        validated -> running à la date de début, puis running -> done au
        lendemain de la date de fin. Les étapes de signature et cancel ne
        bougent pas : un contrat non validé ou annulé ne démarre jamais tout seul.
        """
        today = fields.Date.today()
        to_run = self.filtered(
            lambda c: c.state == 'validated' and c.start_date <= today < c.end_date)
        to_done = self.filtered(
            lambda c: c.state in ('validated', 'running') and c.end_date < today)
        if to_run:
            to_run.write({'state': 'running'})
        if to_done:
            to_done.write({'state': 'done'})
        return to_run | to_done

    @api.model
    def _cron_update_states(self):
        """Balaie quotidiennement les contrats dont la période a évolué."""
        today = fields.Date.today()
        contracts = self.search([
            ('state', 'in', ('validated', 'running')),
            '|', ('start_date', '<=', today), ('end_date', '<', today),
        ])
        updated = contracts._update_state_from_dates()
        return len(updated)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})
