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

    crm_lead_id = fields.Many2one('crm.lead', string='Opportunité', ondelete='set null')

    # --- Les acteurs du contrat ---
    student_id = fields.Many2one(
        'res.partner', string='Étudiant', required=True, tracking=True,
        domain="[('is_company', '=', False), ('partner_type_ids.code', '=', 'type_002')]")
    company_partner_id = fields.Many2one(
        'res.partner', string='Entreprise', required=True, tracking=True,
        domain="[('is_company', '=', True)]")
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
    limayrac_formation_id = fields.Many2one(
        'limayrac.formations', string='Formation', required=True,
        compute='_compute_limayrac_formation_id',
        inverse='_inverse_limayrac_formation_id',
        store=True, readonly=False,
        domain="[('res_partner_cursus_ids.res_partner_id', '=', student_id)]")
    title_rncp_id = fields.Many2one(
        'title.rncp', string='Titre RNCP',
        related='limayrac_formation_id.title_rncp_id', readonly=True)

    @api.depends('cursus_id')
    def _compute_limayrac_formation_id(self):
        for record in self:
            if record.cursus_id:
                record.limayrac_formation_id = record.cursus_id.limayrac_formations_id
            elif not record.limayrac_formation_id:
                record.limayrac_formation_id = False

    @api.model
    def _find_cursus(self, student, formation):
        """Cursus de l'étudiant correspondant à la formation choisie."""
        cursus = student.res_partner_cursus_ids.filtered(
            lambda c: c.limayrac_formations_id == formation)
        if not cursus:
            raise ValidationError(
                "%s n'a aucun cursus pour la formation « %s »." % (
                    student.name, formation.name))
        # Plusieurs cursus pour la même formation (redoublement, reprise) :
        # on retient le plus récent.
        return cursus.sorted('start_date', reverse=True)[0]

    def _inverse_limayrac_formation_id(self):
        for record in self:
            if not record.limayrac_formation_id or not record.student_id:
                continue
            if record.cursus_id.limayrac_formations_id == record.limayrac_formation_id:
                continue
            record.cursus_id = self._find_cursus(record.student_id, record.limayrac_formation_id)

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
            self.limayrac_formation_id = False
        if self.student_id and not self.cursus_id:
            cursus = self.student_id.res_partner_cursus_ids.filtered(
                lambda c: not c.end_date or c.end_date >= fields.Date.today())
            if len(cursus) == 1:
                self.cursus_id = cursus

    @api.onchange('limayrac_formation_id')
    def _onchange_limayrac_formation_id(self):
        # Résout le cursus dès la saisie, pour que l'erreur remonte avant
        # l'enregistrement plutôt qu'au moment du create.
        if self.limayrac_formation_id and self.student_id:
            if self.cursus_id.limayrac_formations_id != self.limayrac_formation_id:
                self.cursus_id = self._find_cursus(self.student_id, self.limayrac_formation_id)

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
            if not vals.get('cursus_id') and vals.get('limayrac_formation_id') and vals.get('student_id'):
                vals['cursus_id'] = self._find_cursus(
                    self.env['res.partner'].browse(vals['student_id']),
                    self.env['limayrac.formations'].browse(vals['limayrac_formation_id']),
                ).id
            elif vals.get('cursus_id') and not vals.get('limayrac_formation_id'):
                cursus = self.env['res.partner.cursus'].browse(vals['cursus_id'])
                vals['limayrac_formation_id'] = cursus.limayrac_formations_id.id
            elif not vals.get('cursus_id'):
                raise ValidationError("La formation est obligatoire sur un contrat.")
        return super().create(vals_list)

    def _sync_lead_won(self):
        """L'opportunité est gagnée dès qu'un de ses contrats est validé."""
        for record in self:
            lead = record.crm_lead_id
            if not lead:
                continue
            has_validated = any(
                contract.state in ('validated', 'running', 'done')
                for contract in lead.contract_ids
            )
            if has_validated and lead.won_status != 'won':
                lead.action_set_won()
            elif not has_validated and lead.won_status == 'won':
                lead.stage_id = lead._stage_for_partner(bool(lead.res_partner_id))

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
        self._sync_lead_won()
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
        self._sync_lead_won()

    def action_draft(self):
        self.write({'state': 'draft'})
        self._sync_lead_won()
