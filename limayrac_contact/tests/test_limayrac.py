from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'limayrac')
class LimayracCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        filiere = cls.env['limayrac.formations.filiere'].create({'name': 'Test Filière'})
        cls.group = cls.env['limayrac.formations.group'].create({'name': 'Test BTS', 'filiere_id': filiere.id})
        cls.classe = cls.env['limayrac.formations'].create({'name': 'Test 1BTS', 'group_id': cls.group.id})
        cls.company = cls.env['res.partner'].create({'name': 'Test Entreprise', 'is_company': True})
        cls.tutor = cls.env['res.partner'].create({'name': 'Test Tuteur', 'parent_id': cls.company.id})
        cls.department = cls.env['res.partner.department'].create({
            'name': 'Test Service', 'res_partner_id': cls.company.id})
        cls.school_tutor = cls.env['res.partner'].create({'name': 'Test Formateur'})
        cls.classe.res_partner_ids = cls.school_tutor
        cls.student = cls.env['res.partner'].create({'name': 'Test Étudiant'})
        cls.cursus = cls.env['res.partner.cursus'].create({
            'res_partner_id': cls.student.id,
            'limayrac_formations_id': cls.classe.id,
            'start_date': cls.today - relativedelta(months=1),
            'end_date': cls.today + relativedelta(years=1),
        })

    def _lead(self, **vals):
        return self.env['crm.lead'].create(dict({
            'name': 'Test besoin',
            'type': 'opportunity',
            'partner_id': self.company.id,
            'type_contract': '2',
        }, **vals))

    def _contract_vals(self, **vals):
        return dict({
            'contract_type': '2',
            'student_id': self.student.id,
            'company_partner_id': self.company.id,
            'cursus_id': self.cursus.id,
            'department_id': self.department.id,
            'company_tutor_id': self.tutor.id,
            'school_tutor_id': self.school_tutor.id,
            'start_date': self.today + relativedelta(days=10),
            'end_date': self.today + relativedelta(months=6),
        }, **vals)


@tagged('post_install', '-at_install', 'limayrac')
class TestStageSync(LimayracCase):

    def test_stage_follows_student_and_contract(self):
        lead = self._lead()
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead1'))

        lead.write({'res_partner_ids': [(4, self.student.id)], 'res_partner_id': self.student.id})
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead2'))

        contract = self.env['limayrac.contract'].create(self._contract_vals(crm_lead_id=lead.id))
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead3'))

        contract.action_company_sign()
        contract.action_cfa_sign()
        contract.action_validate()
        self.assertEqual(contract.state, 'validated')
        self.assertEqual(contract.date_integration, contract.start_date + relativedelta(months=3))
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead4'))

        contract.action_cancel()
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead2'))

    def test_manual_stage_change_refused(self):
        lead = self._lead()
        with self.assertRaises(UserError):
            lead.stage_id = self.env.ref('crm.stage_lead3')

    def test_lost_lead_cancels_contract(self):
        lead = self._lead(res_partner_ids=[(4, self.student.id)], res_partner_id=self.student.id)
        contract = self.env['limayrac.contract'].create(self._contract_vals(crm_lead_id=lead.id))
        lead.action_archive()
        self.assertEqual(contract.state, 'cancel')

    def test_chosen_student_must_be_candidate(self):
        with self.assertRaises(ValidationError):
            self._lead(res_partner_id=self.student.id)


@tagged('post_install', '-at_install', 'limayrac')
class TestContract(LimayracCase):

    def test_reference_from_sequence(self):
        contract = self.env['limayrac.contract'].create(self._contract_vals())
        self.assertTrue(contract.name.startswith('CTR/'))
        self.assertEqual(contract.limayrac_formation_id, self.classe)
        self.assertEqual(contract.formation_id, self.group)

    def test_contract_from_formation_without_class(self):
        student = self.env['res.partner'].create({'name': 'Test Sans Classe'})
        cursus = self.env['res.partner.cursus'].create({
            'res_partner_id': student.id,
            'formation_id': self.group.id,
            'start_date': self.today - relativedelta(months=1),
        })
        self.assertFalse(cursus.limayrac_formations_id)
        contract = self.env['limayrac.contract'].create(self._contract_vals(
            student_id=student.id, cursus_id=False, formation_id=self.group.id))
        self.assertEqual(contract.cursus_id, cursus)
        self.assertFalse(contract.limayrac_formation_id)

    def test_contract_formation_without_cursus_refused(self):
        other = self.env['limayrac.formations.group'].create({
            'name': 'Test Autre', 'filiere_id': self.group.filiere_id.id})
        with self.assertRaises(ValidationError):
            self.env['limayrac.contract'].create(self._contract_vals(
                cursus_id=False, formation_id=other.id))

    def test_opco_frozen_at_signature(self):
        atlas = self.env.ref('limayrac_contact.opco_atlas')
        akto = self.env.ref('limayrac_contact.opco_akto')
        sante = self.env.ref('limayrac_contact.opco_sante')
        self.company.res_partner_opco_id = atlas
        contract = self.env['limayrac.contract'].create(self._contract_vals())
        self.assertEqual(contract.opco_id, atlas)
        # En attente de signature : suit l'entreprise.
        self.company.res_partner_opco_id = akto
        self.assertEqual(contract.opco_id, akto)
        # Signé : ne bouge plus.
        contract.action_company_sign()
        self.company.res_partner_opco_id = sante
        self.env.flush_all()
        contract.invalidate_recordset()
        self.assertEqual(contract.opco_id, akto)

    def test_opco_given_at_creation_is_kept(self):
        self.company.res_partner_opco_id = self.env.ref('limayrac_contact.opco_atlas')
        akto = self.env.ref('limayrac_contact.opco_akto')
        contract = self.env['limayrac.contract'].create(self._contract_vals(
            opco_id=akto.id))
        self.assertEqual(contract.opco_id, akto)

    def test_cannot_sign_incomplete(self):
        contract = self.env['limayrac.contract'].create(self._contract_vals(
            department_id=False, company_tutor_id=False))
        with self.assertRaises(ValidationError):
            contract.action_company_sign()

    def test_wrong_step_refused(self):
        contract = self.env['limayrac.contract'].create(self._contract_vals())
        with self.assertRaises(UserError):
            contract.action_validate()

    def test_student_overlap_refused(self):
        self.env['limayrac.contract'].create(self._contract_vals())
        with self.assertRaises(ValidationError):
            self.env['limayrac.contract'].create(self._contract_vals(
                start_date=self.today + relativedelta(months=2)))

    def test_blacklisted_department_refused(self):
        self.department.write({'is_blacklisted': True, 'reason_blacklist': 'Test'})
        with self.assertRaises(ValidationError):
            self.env['limayrac.contract'].create(self._contract_vals())

    def test_dates_drive_running_and_done(self):
        contract = self.env['limayrac.contract'].create(self._contract_vals(
            start_date=self.today - relativedelta(days=5)))
        contract.action_company_sign()
        contract.action_cfa_sign()
        contract.action_validate()
        self.assertEqual(contract.state, 'running')
        contract.end_date = self.today - relativedelta(days=1)
        self.env['limayrac.contract']._cron_update_states()
        self.assertEqual(contract.state, 'done')

    def test_cron_realigns_opportunity_stage(self):
        # Opportunité restée en décalage avec son contrat en cours (données
        # antérieures aux règles d'étape) : le cron la remet en Won.
        lead = self._lead(res_partner_ids=[(6, 0, self.student.ids)], res_partner_id=self.student.id)
        contract = self.env['limayrac.contract'].create(self._contract_vals(
            crm_lead_id=lead.id, start_date=self.today - relativedelta(days=5)))
        contract.action_company_sign()
        contract.action_cfa_sign()
        contract.action_validate()
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead4'))
        lead.with_context(limayrac_stage_sync=True).stage_id = self.env.ref('crm.stage_lead2')
        self.env['limayrac.contract']._cron_update_states()
        self.assertEqual(lead.stage_id, self.env.ref('crm.stage_lead4'))


@tagged('post_install', '-at_install', 'limayrac')
class TestPartnerTypes(LimayracCase):

    def _types(self, partner):
        return set(partner.partner_type_ids.mapped('code'))

    def test_types(self):
        self.assertIn('type_002', self._types(self.student))
        self.assertIn('type_001', self._types(self.school_tutor))
        self.assertIn('type_004', self._types(self.company))
        self.assertIn('type_004', self._types(self.tutor))

    def test_cursus_without_end_date_is_current(self):
        partner = self.env['res.partner'].create({'name': 'Test Sans Fin'})
        self.env['res.partner.cursus'].create({
            'res_partner_id': partner.id,
            'limayrac_formations_id': self.classe.id,
            'start_date': self.today,
        })
        self.assertIn('type_002', self._types(partner))

    def test_ended_cursus_makes_former_student(self):
        partner = self.env['res.partner'].create({'name': 'Test Ancien'})
        self.env['res.partner.cursus'].create({
            'res_partner_id': partner.id,
            'limayrac_formations_id': self.classe.id,
            'start_date': date(2020, 9, 1),
            'end_date': date(2021, 6, 30),
        })
        self.assertEqual(self._types(partner), {'type_005'})

    def test_cron_recomputes_types(self):
        # Simule une valeur stockée devenue périmée (le cursus a pris fin
        # depuis le dernier calcul) : le cron doit la corriger.
        self.cursus.end_date = self.today - relativedelta(days=1)
        self.student.partner_type_ids = self.env.ref('limayrac_contact.type_002')
        self.env['res.partner']._cron_update_partner_types()
        self.assertEqual(self._types(self.student), {'type_005'})

    def test_cursus_formation_from_class(self):
        self.assertEqual(self.cursus.formation_id, self.group)

    def test_cursus_needs_formation(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner.cursus'].create({
                'res_partner_id': self.env['res.partner'].create({'name': 'Test Vide'}).id,
                'start_date': self.today,
            })

    def test_cursus_class_must_match_formation(self):
        other = self.env['limayrac.formations.group'].create({
            'name': 'Test Autre', 'filiere_id': self.group.filiere_id.id})
        with self.assertRaises(ValidationError):
            self.cursus.write({'formation_id': other.id, 'limayrac_formations_id': self.classe.id})

    def test_cursus_overlap_refused(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner.cursus'].create({
                'res_partner_id': self.student.id,
                'limayrac_formations_id': self.classe.id,
                'start_date': self.today,
            })


@tagged('post_install', '-at_install', 'limayrac')
class TestTitleRncp(LimayracCase):

    def test_validity_follows_today(self):
        Title = self.env['title.rncp']
        expired = Title.create({'name': 'Test expiré', 'end_date': self.today - relativedelta(days=1)})
        current = Title.create({'name': 'Test valide', 'end_date': self.today})
        open_ended = Title.create({'name': 'Test sans fin'})
        self.assertFalse(expired.is_valid)
        self.assertTrue(current.is_valid)
        self.assertTrue(open_ended.is_valid)
        mine = expired | current | open_ended
        self.assertEqual(Title.search([('id', 'in', mine.ids), ('is_valid', '=', True)]), current | open_ended)
        self.assertEqual(Title.search([('id', 'in', mine.ids), ('is_valid', '=', False)]), expired)
        self.assertEqual(Title.search([('id', 'in', mine.ids), ('is_valid', '!=', True)]), expired)
