from odoo import models, fields, api

class TitleRncp(models.Model):
    _name = 'title.rncp'
    _description = 'Intitulé RNCP'

    name = fields.Char(string="Intitulé")
    code_rncp = fields.Char(string="Code RNCP")
    start_date = fields.Date(string="Date de début validitée")
    end_date = fields.Date(string="Date de fin de validitée")
    # Non stocké : la validité dépend de la date du jour, une valeur stockée
    # resterait figée après l'expiration du titre.
    is_valid = fields.Boolean(string="Valide", compute='_compute_is_valid', search='_search_is_valid')

    @api.depends('end_date')
    def _compute_is_valid(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_valid = not record.end_date or record.end_date >= today

    def _search_is_valid(self, operator, value):
        # Odoo 19 normalise les domaines booléens en 'in' / 'not in' ;
        # 'not in' est déduit par négation de 'in'.
        if operator != 'in':
            return NotImplemented
        valid = ['|', ('end_date', '=', False), ('end_date', '>=', fields.Date.context_today(self))]
        values = set(value)
        if True in values and False in values:
            return [(1, '=', 1)]
        if True in values:
            return valid
        if False in values:
            return ['!'] + valid
        return [(0, '=', 1)]
