from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

# Étapes du pipeline, déduites de l'état de l'opportunité :
#   New         : besoin reçu, aucun étudiant choisi
#   Qualified   : étudiant choisi parmi les candidatures
#   Proposition : contrat en cours de signature
#   Won         : contrat validé (ou en cours / terminé)
STAGE_NEW = 'crm.stage_lead1'
STAGE_QUALIFIED = 'crm.stage_lead2'
STAGE_PROPOSITION = 'crm.stage_lead3'
STAGE_WON = 'crm.stage_lead4'

CONTRACT_WON_STATES = ('validated', 'running', 'done')


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    res_partner_id = fields.Many2one('res.partner', string='Etudiant choisi', domain="[('id', 'in', res_partner_ids)]")
    res_partner_ids = fields.Many2many('res.partner', 'crm_lead_res_partner_rel', 'crm_lead_id', 'res_partner_id', string='Candidatures', domain="[('is_company', '=', False), ('partner_type_ids.code', '=', 'type_002')]")
    type_contract = fields.Selection([('1', 'Stage'), ('2', 'Alternance'), ('3', 'Stage/Alternance')], string='Type de contrat')
    formation_id = fields.Many2one('limayrac.formations.group', string='Formation', index=True)
    contract_ids = fields.One2many('limayrac.contract', 'crm_lead_id', string='Contrats')
    contract_count = fields.Integer(compute='_compute_contract_count')
    has_active_contract = fields.Boolean(compute='_compute_contract_count')

    @api.depends('contract_ids', 'contract_ids.state')
    def _compute_contract_count(self):
        for record in self:
            record.contract_count = len(record.contract_ids)
            record.has_active_contract = bool(record._get_active_contract())

    def _get_active_contract(self):
        """Le contrat de l'opportunité : une opportunité donne au plus un contrat non annulé."""
        self.ensure_one()
        return self.contract_ids.filtered(lambda c: c.state != 'cancel')[:1]

    # ------------------------------------------------------------------
    # Contrôles
    # ------------------------------------------------------------------

    @api.constrains('partner_id', 'type')
    def _check_partner_is_company(self):
        # Le pipeline représente les besoins des entreprises.
        for record in self:
            if record.type == 'opportunity' and record.partner_id \
                    and not record.partner_id.commercial_partner_id.is_company:
                raise ValidationError(
                    "Le client de l'opportunité « %s » doit être une entreprise." % record.name)

    @api.constrains('res_partner_id', 'res_partner_ids', 'partner_id')
    def _check_chosen_student(self):
        for record in self:
            if not record.res_partner_id:
                continue
            if not record.partner_id:
                raise ValidationError(
                    "Renseignez l'entreprise de l'opportunité « %s » avant de choisir un étudiant." % record.name)
            if record.res_partner_id not in record.res_partner_ids:
                raise ValidationError(
                    "%s doit faire partie des candidatures de l'opportunité « %s »." % (
                        record.res_partner_id.name, record.name))

    @api.constrains('partner_id', 'res_partner_id', 'type_contract', 'formation_id')
    def _check_contract_consistency(self):
        # Une fois le contrat créé, l'opportunité ne doit plus le contredire.
        self.contract_ids._check_lead_consistency()

    # ------------------------------------------------------------------
    # Étapes
    # ------------------------------------------------------------------

    def _get_expected_stage(self):
        self.ensure_one()
        contract = self._get_active_contract()
        if contract.state in CONTRACT_WON_STATES:
            xmlid = STAGE_WON
        elif contract:
            xmlid = STAGE_PROPOSITION
        elif self.res_partner_id:
            xmlid = STAGE_QUALIFIED
        else:
            xmlid = STAGE_NEW
        return self.env.ref(xmlid)

    def _sync_stage(self):
        """Aligne l'étape sur l'état de l'opportunité et de son contrat."""
        for record in self.with_context(limayrac_stage_sync=True):
            stage = record._get_expected_stage()
            if record.stage_id == stage:
                continue
            was_won = record.stage_id.is_won
            record.write({'stage_id': stage.id})
            if was_won:
                # Sortie de l'étape gagnée : la probabilité reste sinon à 100 %.
                record._compute_probabilities()
                record.probability = record.automated_probability

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_stage()
        return records

    def write(self, vals):
        if 'stage_id' in vals and not self.env.context.get('limayrac_stage_sync'):
            # L'étape suit le contrat : pas de déplacement manuel.
            for record in self:
                if record.stage_id.id != vals['stage_id']:
                    raise UserError(
                        "L'étape d'une opportunité est mise à jour automatiquement "
                        "(étudiant choisi, contrat en signature, contrat validé) : "
                        "elle ne peut pas être modifiée à la main.")
        if 'active' in vals and not vals['active']:
            for record in self:
                if record._get_active_contract().state in CONTRACT_WON_STATES:
                    raise UserError(
                        "L'opportunité « %s » a un contrat validé : elle ne peut pas être perdue." % record.name)
        res = super().write(vals)
        if 'active' in vals and not vals['active']:
            # Opportunité perdue : ses contrats non validés sont annulés.
            self.contract_ids.filtered(lambda c: c.state != 'cancel').action_cancel()
        if {'res_partner_id', 'active'} & set(vals):
            self._sync_stage()
        return res

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_create_contract(self):
        """Ouvre un formulaire de contrat pré-rempli avec ce que l'opportunité sait déjà."""
        self.ensure_one()
        if not self.active:
            raise UserError("Impossible de créer un contrat sur une opportunité perdue.")
        if self._get_active_contract():
            raise UserError("Cette opportunité a déjà un contrat.")
        student = self.res_partner_id
        cursus = student.res_partner_cursus_ids.filtered(
            lambda c: not c.end_date or c.end_date >= fields.Date.today())
        if self.formation_id:
            cursus = cursus.filtered(
                lambda c: c.formation_id == self.formation_id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouveau contrat',
            'res_model': 'limayrac.contract',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_crm_lead_id': self.id,
                'default_student_id': student.id,
                'default_company_partner_id': self.partner_id.commercial_partner_id.id,
                # type_contract vaut '3' (Stage/Alternance) sur l'opportunité :
                # il faut trancher au moment du contrat, on ne pré-remplit pas.
                'default_contract_type': self.type_contract if self.type_contract in ('1', '2') else False,
                'default_cursus_id': cursus.id if len(cursus) == 1 else False,
                'default_formation_id': cursus.formation_id.id if len(cursus) == 1 else self.formation_id.id,
            },
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrats',
            'res_model': 'limayrac.contract',
            'view_mode': 'list,form',
            'domain': [('crm_lead_id', '=', self.id)],
            'context': {'default_crm_lead_id': self.id},
        }
