from odoo import models, fields, api

class LimayracFormations(models.Model):
    _name = 'limayrac.formations'
    _description = 'Formations Limayrac'

    name = fields.Char(string="Nom commercial", required=True)
    question_one = fields.Char(string="Question 1")
    question_two = fields.Char(string="Question 2")
    question_three = fields.Char(string="Question 3")
    question_four = fields.Char(string="Question 4")
    question_five = fields.Char(string="Question 5")
    title_rncp_id = fields.Many2one('title.rncp', string="Titre RNCP", domain="[('is_valid', '=', True)]")
    old_rncp_ids = fields.Many2many('title.rncp', string="Ancien Titre RNCP", readonly=True)
    res_partner_ids = fields.Many2many('res.partner', string='Responsables formation')

    def write(self, vals):
        for record in self:
            if 'title_rncp_id' in vals:
                if record.title_rncp_id.id not in record.old_rncp_ids.ids:
                    record.old_rncp_ids = [(4, record.title_rncp_id.id)]
                if vals['title_rncp_id'] in record.old_rncp_ids.ids:
                    record.old_rncp_ids = [(3, vals['title_rncp_id'])]
        return super(LimayracFormations, self).write(vals)
