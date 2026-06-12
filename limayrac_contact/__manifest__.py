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
        # 'data/res_groups.xml',
        # #VIEWS
        'views/res_partner_views.xml',
        'views/res_partner_department_views.xml',
        # #REPORT
        # 'report/report_estate_property.xml',
        # # WIZARD
        # 'wizard/mon_super_wizard_views.xml',
        # #MENU
        # 'views/menu.xml',
    ],
}