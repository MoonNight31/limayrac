{
    'name': 'Limayrac Contact',
    'version': '0.1',
    'summary': 'Module to manage Limayrac contacts and related information.',
    'description': """
        A detailed description of the module.
    """,
    'author': 'Limayrac',
    'website': 'http://www.limayrac.com',
    'category': 'Uncategorized',
    'depends': ['base', 'contacts', 'crm', 'mail'],
    'data': [
        #SECURITY
        'security/ir.model.access.csv',
        # #DATA
        'data/default_res_partner_naf.xml',
        'data/default_res_partner_type.xml',
        'data/cron_load_demo.xml',
        'data/mail_template_rdv_sre.xml',
        'data/limayrac_contract_sequence.xml',
        'data/cron_limayrac_contract.xml',
        # 'data/res_groups.xml',
        # #VIEWS
        'views/res_partner_views.xml',
        'views/res_partner_department_views.xml',
        'views/res_partner_naf_views.xml',
        'views/limayrac_formation_views.xml',
        'views/crm_lead_views.xml',
        'views/limayrac_contract_views.xml',
        # #REPORT
        # 'report/report_estate_property.xml',
        # # WIZARD
        'wizard/res_partner_blacklist_wizard_views.xml',
        # #MENU
        # 'views/menu.xml',
    ],
    'demo': [
        'demo/title_rncp_demo.xml',
        'demo/limayrac_formations_demo.xml',
        'demo/res_partner_demo.xml',
        'demo/res_partner_department_demo.xml',
        'demo/res_partner_cursus_demo.xml',
        'demo/crm_lead_demo.xml',
        'demo/crm_opportunity_demo.xml',
    ],
}