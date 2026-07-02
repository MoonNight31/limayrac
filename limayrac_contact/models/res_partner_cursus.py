from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartnerCursus(models.Model):
    _name = 'res.partner.cursus'
    _description = 'Cursus d\'un contact'

    start_date = fields.Date(string='Date de début', required=True)
    end_date = fields.Date(string='Date de fin')
    res_partner_id = fields.Many2one('res.partner', string='Contact', required=True)
    limayrac_formations_id = fields.Many2one('limayrac.formations', string='Formation', required=True)
    is_diploma_obtained = fields.Boolean(string='Diplôme obtenu')

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

