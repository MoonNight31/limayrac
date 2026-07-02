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
    res_partner_resp_ids = fields.Many2many('res.partner', 'res_partner_limayrac_formations_resp_rel', 'limayrac_formations_id', 'res_partner_id', string='Responsables de sections')
    res_partner_ids = fields.Many2many('res.partner', 'res_partner_limayrac_formations_rel', 'limayrac_formations_id', 'res_partner_id', string='Formateurs')
    res_partner_cursus_ids = fields.One2many('res.partner.cursus', 'limayrac_formations_id', string='Cursus des contacts')

    def write(self, vals):
        partners_before = self.res_partner_ids | self.res_partner_resp_ids
        for record in self:
            if 'title_rncp_id' in vals:
                if record.title_rncp_id.id not in record.old_rncp_ids.ids:
                    record.old_rncp_ids = [(4, record.title_rncp_id.id)]
                if vals['title_rncp_id'] in record.old_rncp_ids.ids:
                    record.old_rncp_ids = [(3, vals['title_rncp_id'])]
        res = super(LimayracFormations, self).write(vals)
        if 'res_partner_ids' in vals or 'res_partner_resp_ids' in vals:
            partners_after = self.res_partner_ids | self.res_partner_resp_ids
            (partners_before | partners_after).modified(['limayrac_formations_ids', 'limayrac_formations_resp_ids'])
        return res

    def unlink(self):
        partners = self.res_partner_ids | self.res_partner_resp_ids
        res = super(LimayracFormations, self).unlink()
        partners.modified(['limayrac_formations_ids', 'limayrac_formations_resp_ids'])
        return res

