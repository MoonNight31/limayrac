{
    'name': 'Limayrac Contact',
    'version': '0.1',
    'summary': 'A brief summary of the module',
    'description': """
        A detailed description of the module.
    """,
    'author': 'Limayrac',
    'website': 'http://www.limayrac.com',
    'category': 'Uncategorized',
    'depends': ['base', 'contacts'],
    'data': [
        #SECURITY
        'security/ir.model.access.csv',
        # #DATA
        'data/default_res_partner_naf.xml',
        # 'data/res_groups.xml',
        # #VIEWS
        'views/res_partner_views.xml',
        'views/res_partner_department_views.xml',
        'views/res_partner_naf_views.xml',
        'views/limayrac_formation_views.xml'
        # #REPORT
        # 'report/report_estate_property.xml',
        # # WIZARD
        'wizard/res_partner_blacklist_wizard_views.xml',
        # #MENU
        # 'views/menu.xml',
    ],
}