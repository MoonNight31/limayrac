from odoo import models, fields, api

class LimayracFormationsFiliere(models.Model):
    _name = 'limayrac.formations.filiere'
    _description = 'Filière Limayrac'
    _order = 'name'

    name = fields.Char(string="Nom de la filière", required=True)
    active = fields.Boolean(default=True)
    group_ids = fields.One2many('limayrac.formations.group', 'filiere_id', string="Formations")
    group_count = fields.Integer(string="Nombre de formations", compute='_compute_group_count')

    _name_uniq = models.Constraint('UNIQUE(name)', "Cette filière existe déjà.")

    @api.depends('group_ids')
    def _compute_group_count(self):
        for record in self:
            record.group_count = len(record.group_ids)
