{
    'name': 'ADK Demande d\'Achat',
    'version': '18.0.1.2',
    'category': 'Inventory/Purchase',
    'summary': 'Gestion complète des demandes d\'achat ADK avec traçabilité, tableau de bord et rapports intégrés',
    'description': """
ADK Demande d'Achat
====================
Module 100% natif Odoo 18 (purchase, mail, uom) pour la gestion des
demandes d'achat internes, avec génération de bons de commande
fournisseur, enrichi par ADK avec :

* Un tableau de bord (kanban) avec indicateurs clés
* Des vues d'analyse graphique et pivot
* Un rapport PDF imprimable de la demande d'achat
* Une traçabilité complète (chatter, activités, suivi des champs)
""",
    'author': 'KAMBEU HENANG ANGE DUVAL <duvalkambeu61@gmail.com>',
    'company': 'ADK',
    'images': ['static/description/banner.png'],
    'depends': ['purchase', 'purchase_stock', 'stock', 'hr', 'mail', 'uom'],
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
        # CORRECTION 4 : liaison avec le module Achats natif (smart button, colonne,
        # filtre, menu) + accès direct aux demandes d'achat depuis Achats.
        'views/purchase_order_views.xml',
        'views/purchase_request_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
