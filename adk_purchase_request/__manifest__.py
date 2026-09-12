{
    'name': 'ADK Demande d\'Achat',
    'version': '18.0.1.2',
    'category': 'Inventory/Purchase',
    'summary': 'Gestion complète des demandes d\'achat ADK avec traçabilité, tableau de bord et rapports intégrés',

    'description': """
ADK Demande d'Achat
====================

Module natif Odoo 18 pour la gestion des demandes d'achat internes.

Fonctionnalités principales :
* Tableau de bord avec indicateurs clés
* Vues d'analyse graphique et pivot
* Génération de bons de commande fournisseur
* Rapport PDF imprimable
* Traçabilité complète avec chatter et activités
""",

    'author': 'Kambeu Henang Ange Duval',
    'company': 'ADK',
    'support': 'duvalkambeu61@gmail.com',

    'images': [
        'static/description/banner.png',
    ],

    'depends': [
        'purchase',
        'purchase_stock',
        'stock',
        'hr',
        'mail',
        'uom',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'report/purchase_request_report.xml',
        'report/purchase_request_report_templates.xml',
        'views/purchase_request_analysis_views.xml',
        'views/purchase_request_dashboard_views.xml',
        'views/purchase_request_views.xml',
        'views/purchase_request_article_dashboard_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_request_menus.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
