from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartnerCursus(models.Model):
    _name = 'res.partner.cursus'
    _description = 'Cursus d\'un contact'

    start_date = fields.Date(string='Date de début', required=True)
    end_date = fields.Date(string='Date de fin')
    res_partner_id = fields.Many2one('res.partner', string='Contact', required=True)
    # La formation est l'information de référence ; la classe est facultative.
    # Quand une classe est choisie, la formation est reprise de la classe.
    formation_id = fields.Many2one(
        'limayrac.formations.group', string='Formation', index=True,
        compute='_compute_formation_id', store=True, readonly=False)
    limayrac_formations_id = fields.Many2one(
        'limayrac.formations', string='Classe',
        domain="[('group_id', '=', formation_id)] if formation_id else []")
    is_diploma_obtained = fields.Boolean(string='Diplôme obtenu')

    @api.depends('limayrac_formations_id.group_id')
    def _compute_formation_id(self):
        for record in self:
            if record.limayrac_formations_id.group_id:
                record.formation_id = record.limayrac_formations_id.group_id
            else:
                record.formation_id = record.formation_id

    @api.onchange('formation_id')
    def _onchange_formation_id(self):
        group = self.limayrac_formations_id.group_id
        if group and group != self.formation_id:
            self.limayrac_formations_id = False

    @api.depends('formation_id', 'limayrac_formations_id', 'start_date', 'end_date')
    def _compute_display_name(self):
        for record in self:
            label = record.formation_id.name or record.limayrac_formations_id.name or ''
            if record.limayrac_formations_id and record.formation_id:
                label = '%s (%s)' % (label, record.limayrac_formations_id.name)
            if record.start_date:
                label = '%s, depuis le %s' % (label, record.start_date.strftime('%d/%m/%Y'))
            record.display_name = label

    @api.constrains('formation_id', 'limayrac_formations_id')
    def _check_formation(self):
        for record in self:
            if not record.formation_id and not record.limayrac_formations_id:
                raise ValidationError("Renseignez la formation du cursus.")
            group = record.limayrac_formations_id.group_id
            if group and record.formation_id and group != record.formation_id:
                raise ValidationError(
                    "La classe « %s » n'appartient pas à la formation « %s »." % (
                        record.limayrac_formations_id.name, record.formation_id.name))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.end_date < record.start_date:
                raise ValidationError(
                    "La date de fin ne peut pas être antérieure à la date de début.")

    @api.constrains('start_date', 'end_date', 'res_partner_id')
    def _check_no_overlapping_cursus(self):
        for record in self:
            others = self.search([
                ('id', '!=', record.id),
                ('res_partner_id', '=', record.res_partner_id.id),
            ])
            for other in others:
                # Two cursus overlap when each one starts on or before the other
                # ends. A missing end_date means the cursus is still in progress.
                starts_before_other_ends = not other.end_date or record.start_date <= other.end_date
                other_starts_before_ends = not record.end_date or other.start_date <= record.end_date
                if starts_before_other_ends and other_starts_before_ends:
                    raise ValidationError(
                        "Ce contact a déjà un cursus en cours sur cette période. "
                        "Deux cursus ne peuvent pas se chevaucher.")
